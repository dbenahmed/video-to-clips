"""
================================================================================
PIPELINE PLAYGROUND: Milestone 3 (The Brain)
================================================================================
Purpose:
    This is an isolated sandbox to test the video segmentation and global tracking 
    algorithms on a local 'sample.mp4' file before integrating them into the 
    live FastAPI endpoints.

Workflow Implemented:
    1. Read 'sample.mp4' using OpenCV.
    2. Run Hybrid Global Tracking (MediaPipe for faces, OpenCV CSRT for fallback).
    3. Compress the tracking data into Time Ranges (to save JSON size).
    4. Export the resulting "Recipe" JSON into a timestamped output folder.
================================================================================
"""

import os
import json
import math
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Optional, Tuple, Dict, Any

import cv2
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision as mp_vision
import urllib.request

# ============================================================================
# DATA TRANSFER OBJECTS (DTOs)
# ============================================================================

@dataclass
class TimeRangeTrackingData:
    """Represents a compressed block of time where the subject sits still."""
    start_time_seconds: float
    end_time_seconds: float
    center_x_coordinate: int
    center_y_coordinate: int
    crop_x: int = 0
    crop_y: int = 0


@dataclass
class VideoMetadata:
    """Stores essential technical details about the source video."""
    total_frames: int
    frames_per_second: float
    video_width_pixels: int
    video_height_pixels: int
    duration_seconds: float


# ============================================================================
# ALGORITHM MODULES (SOLID Principles)
# ============================================================================

class TrackingDataCompressor:
    """
    Responsibility: Takes raw frame-by-frame coordinates (which would create massive JSON files)
    and compresses them into logical "Time Ranges" by detecting if the subject is sitting still.
    
    Example of Compression:
        Imagine processing 3 frames at 1 frame per second:
        - Second 1.0: Subject is at X=500. We start a new block: {start: 1.0, end: 1.0, x: 500}
        - Second 2.0: Subject is at X=502. They haven't moved much (less than 10 pixels). 
                      Instead of a new block, we EXTEND the current block: {start: 1.0, end: 2.0, x: 500}
        - Second 3.0: Subject walks to X=800. They moved significantly! 
                      We save the old block, and start a new one: {start: 3.0, end: 3.0, x: 800}
                      
    This turns 36,000 frames into maybe 50 logical blocks, saving massive amounts of data!
    """
    # TODO: RESTORE - Revert pixel_movement_threshold to 10 for accurate production tracking
    def __init__(self, pixel_movement_threshold: int = 50):
        # The maximum number of pixels the subject can move left or right before we 
        # decide they have "moved" and a brand new time block needs to be created.
        self.pixel_movement_threshold: int = pixel_movement_threshold
        
        # The final array of compressed time blocks that will be returned as JSON.
        self.compressed_tracking_map: List[TimeRangeTrackingData] = []
        
        # The current time block we are actively building and extending.
        self.active_time_range: Optional[TimeRangeTrackingData] = None

    def add_data_point(self, current_time_seconds: float, center_x: int, center_y: int) -> None:
        """
        Evaluates a single new X/Y coordinate from the video tracker.
        Decides whether to extend the `active_time_range` or start a new one.
        """
        
        # Scenario 1: The engine just started. We have no active block yet.
        if self.active_time_range is None:
            self.active_time_range = TimeRangeTrackingData(
                start_time_seconds=current_time_seconds,
                end_time_seconds=current_time_seconds,
                center_x_coordinate=center_x,
                center_y_coordinate=center_y
            )
            return

        # Calculate absolute pixel distance between the subject's current X position 
        # and the X position where they were when this time block originally started.
        movement_distance: float = abs(center_x - self.active_time_range.center_x_coordinate)

        # Scenario 2: The subject walked across the room (Movement > Threshold)
        if movement_distance > self.pixel_movement_threshold:
            # We must lock in the old block because the subject is in a completely new position.
            self.compressed_tracking_map.append(self.active_time_range)
            # Create a brand new block starting at this exact second with the new coordinates.
            self.active_time_range = TimeRangeTrackingData(
                start_time_seconds=current_time_seconds,
                end_time_seconds=current_time_seconds,
                center_x_coordinate=center_x,
                center_y_coordinate=center_y
            )
        
        # Scenario 3: The subject is sitting relatively still (Movement <= Threshold)
        else:
            # Do NOT create a new block. This is where the compression happens!
            # We simply stretch the end time of the existing block to include this second.
            self.active_time_range.end_time_seconds = current_time_seconds

    def get_final_map(self) -> List[TimeRangeTrackingData]:
        """
        Called when the video finishes processing. 
        Ensures the very last active block is safely pushed into the final array.
        """
        if self.active_time_range is not None:
            self.compressed_tracking_map.append(self.active_time_range)
            self.active_time_range = None
        return self.compressed_tracking_map


class HybridVideoTracker:
    """
    Responsibility: Uses MediaPipe as the primary face detector. If the face is lost 
    (e.g. subject turns their back), it seamlessly hands the last known coordinates 
    over to an OpenCV CSRT pixel tracker until the face returns.
    """
    def __init__(self, video_metadata: VideoMetadata):
        # We store the video metadata (like width/height) because MediaPipe returns 
        # relative percentages (e.g. 0.5) that we need to convert to absolute pixels (e.g. 500px).
        self.video_metadata: VideoMetadata = video_metadata
        
        # --------------------------------------------------------------------
        # MEDIAPIPE CONFIGURATION (MODERN TASKS API)
        # --------------------------------------------------------------------
        # `model_selection`: In the modern Tasks API, we don't pass an integer. 
        # Instead, we explicitly download and provide the exact model we want.
        # We download 'blaze_face_short_range.tflite' which is optimized for faces 
        # reasonably close to the camera (podcasts/interviews).
        model_path = Path(__file__).parent / "blaze_face_short_range.tflite"
        if not model_path.exists():
            print("Downloading MediaPipe face detection model...")
            model_url = "https://storage.googleapis.com/mediapipe-models/face_detector/blaze_face_short_range/float16/1/blaze_face_short_range.tflite"
            urllib.request.urlretrieve(model_url, str(model_path))

        # Attempt to use CUDA/GPU hardware acceleration
        try:
            base_options = mp_python.BaseOptions(model_asset_path=str(model_path), delegate=mp_python.BaseOptions.Delegate.GPU)
            options = mp_vision.FaceDetectorOptions(base_options=base_options, min_detection_confidence=0.65)
            self.mediapipe_face_detector = mp_vision.FaceDetector.create_from_options(options)
            print("\n🚀 [TRACKING] Hardware Acceleration ENABLED: Using NVIDIA CUDA/GPU for MediaPipe.")
        except Exception as e:
            print("\n⚠️ [TRACKING] Hardware Acceleration UNAVAILABLE: Using CPU fallback for MediaPipe.")
            base_options = mp_python.BaseOptions(model_asset_path=str(model_path), delegate=mp_python.BaseOptions.Delegate.CPU)
            options = mp_vision.FaceDetectorOptions(base_options=base_options, min_detection_confidence=0.65)
            self.mediapipe_face_detector = mp_vision.FaceDetector.create_from_options(options)
        
        # --------------------------------------------------------------------
        # OPENCV FALLBACK CONFIGURATION
        # --------------------------------------------------------------------
        # `opencv_csrt_tracker`: Holds the active instance of the CSRT tracking algorithm.
        # It is set to None by default, and only initialized when MediaPipe loses a face.
        self.opencv_csrt_tracker: Optional[cv2.Tracker] = None
        
        # `last_known_face_bounding_box`: A tuple of (X, Y, Width, Height) in absolute pixels.
        # We constantly update this when MediaPipe sees a face. If MediaPipe fails, 
        # we hand this exact box to OpenCV so it knows which pixels to start tracking.
        self.last_known_face_bounding_box: Optional[Tuple[int, int, int, int]] = None

    def process_frame(self, frame_bgr: Any) -> Tuple[int, int]:
        """
        Analyzes a single frame and returns the best known (X, Y) center coordinates.
        Returns the center of the screen if absolutely no subject can be found.
        """
        # OpenCV reads in BGR, but MediaPipe requires RGB color space
        frame_rgb: Any = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        
        # --------------------------------------------------------------------
        # STEP 1: Attempt Primary Detection (MediaPipe)
        # --------------------------------------------------------------------
        # The modern API requires wrapping the numpy array in an mp.Image object
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)
        mediapipe_results = self.mediapipe_face_detector.detect(mp_image)
        
        if mediapipe_results.detections:
            # We found a face! Get the highest confidence face (usually the first one)
            primary_face = mediapipe_results.detections[0]
            
            # MediaPipe Tasks API natively returns absolute pixel coordinates.
            # (The old legacy API used to return percentages 0.0-1.0 that we had to convert).
            bbox = primary_face.bounding_box
            box_x_pixel: int = bbox.origin_x
            box_y_pixel: int = bbox.origin_y
            box_width_pixel: int = bbox.width
            box_height_pixel: int = bbox.height
            
            # Update our fallback state
            self.last_known_face_bounding_box = (box_x_pixel, box_y_pixel, box_width_pixel, box_height_pixel)
            self.opencv_csrt_tracker = None # Reset OpenCV because we don't need it right now
            
            # Calculate mathematical center of the face
            center_x: int = box_x_pixel + (box_width_pixel // 2)
            center_y: int = box_y_pixel + (box_height_pixel // 2)
            return center_x, center_y

        # --------------------------------------------------------------------
        # STEP 2: Attempt Secondary Fallback (OpenCV CSRT Pixel Tracker)
        # --------------------------------------------------------------------
        elif self.last_known_face_bounding_box is not None:
            # MediaPipe failed (maybe they turned around). Let's use OpenCV if it's not started yet.
            if self.opencv_csrt_tracker is None:
                self.opencv_csrt_tracker = cv2.TrackerCSRT_create()  # type: ignore
                self.opencv_csrt_tracker.init(frame_bgr, self.last_known_face_bounding_box)
                
            # Ask OpenCV to find those same pixels in this new frame
            tracking_success, new_bounding_box = self.opencv_csrt_tracker.update(frame_bgr)
            
            if tracking_success:
                fallback_x, fallback_y, fallback_w, fallback_h = [int(v) for v in new_bounding_box]
                center_x = fallback_x + (fallback_w // 2)
                center_y = fallback_y + (fallback_h // 2)
                return center_x, center_y
            else:
                # OpenCV also lost the subject (e.g. they walked completely off screen)
                self.opencv_csrt_tracker = None
                self.last_known_face_bounding_box = None

        # --------------------------------------------------------------------
        # STEP 3: Ultimate Fallback (Center Screen)
        # --------------------------------------------------------------------
        # If we reach here, it's B-Roll footage or an empty room. Default to the exact center.
        default_center_x: int = self.video_metadata.video_width_pixels // 2
        default_center_y: int = self.video_metadata.video_height_pixels // 2
        return default_center_x, default_center_y


# ============================================================================
# MAIN PIPELINE EXECUTION
# ============================================================================

# TODO: RESTORE - Revert target_frames_per_second to 15 for smooth production tracking
def run_hybrid_tracking_pipeline(target_frames_per_second: int = 1) -> None:
    """
    The main orchestrator function. Reads the video, passes frames to the Hybrid Tracker,
    compresses the data, and outputs the final JSON recipe.
    """
    
    current_directory: Path = Path(__file__).parent
    sample_video_file_path: Path = current_directory / "sample.mp4"
    outputs_directory: Path = current_directory / "output"

    if not sample_video_file_path.exists():
        print(f"Error: Please place a video named 'sample.mp4' inside {current_directory}")
        return

    print("\n[1/4] Initializing Video Capture...")
    video_capture_instance = cv2.VideoCapture(str(sample_video_file_path))
    
    if not video_capture_instance.isOpened() or int(video_capture_instance.get(cv2.CAP_PROP_FRAME_COUNT)) <= 0:
        print(f"Error: OpenCV could not read '{sample_video_file_path.name}'.")
        print("The file appears to be corrupted, empty, or not a valid video format.")
        print("Solution: Please replace it with a real, working MP4 video file.")
        video_capture_instance.release()
        return
    
    # Extract metadata needed for calculations
    video_metadata = VideoMetadata(
        total_frames=int(video_capture_instance.get(cv2.CAP_PROP_FRAME_COUNT)),
        frames_per_second=video_capture_instance.get(cv2.CAP_PROP_FPS),
        video_width_pixels=int(video_capture_instance.get(cv2.CAP_PROP_FRAME_WIDTH)),
        video_height_pixels=int(video_capture_instance.get(cv2.CAP_PROP_FRAME_HEIGHT)),
        duration_seconds=0.0 # Will calculate below
    )
    video_metadata.duration_seconds = video_metadata.total_frames / video_metadata.frames_per_second
    
    # Optimization: Calculate how many frames to skip to achieve the target processing FPS
    # e.g., If video is 60fps and we want 2fps, we skip 30 frames at a time.
    frame_skip_interval: int = max(1, int(video_metadata.frames_per_second / target_frames_per_second))
    
    print(f"      Video Loaded: {video_metadata.duration_seconds:.1f} seconds, {video_metadata.frames_per_second} FPS.")
    print(f"      Processing at {target_frames_per_second} FPS (Scanning every {frame_skip_interval}th frame to save time).")

    # Initialize our SOLID worker classes
    hybrid_tracker = HybridVideoTracker(video_metadata=video_metadata)
    data_compressor = TrackingDataCompressor(pixel_movement_threshold=20)

    print("\n[2/4] Running Hybrid AI Tracking (MediaPipe + OpenCV)...")
    current_frame_index: int = 0
    
    while True:
        # Read the next frame from the hard drive
        read_success, frame_bgr = video_capture_instance.read()
        
        if not read_success:
            break # Reached the end of the video
            
        # Only process frames that match our target framerate to save CPU time
        if current_frame_index % frame_skip_interval == 0:
            current_time_in_seconds: float = current_frame_index / video_metadata.frames_per_second
            
            # Step A: Get the X/Y coordinates from our Hybrid Tracker
            subject_center_x, subject_center_y = hybrid_tracker.process_frame(frame_bgr=frame_bgr)
            
            # Step B: Pass those coordinates to the Compressor to build time ranges
            data_compressor.add_data_point(
                current_time_seconds=current_time_in_seconds,
                center_x=subject_center_x,
                center_y=subject_center_y
            )
            
            # Print a progress indicator every 10%
            if current_frame_index % (video_metadata.total_frames // 10 or 1) == 0:
                percent_done = (current_frame_index / video_metadata.total_frames) * 100
                print(f"      Progress: {percent_done:.0f}%")
                
        current_frame_index += 1

    # Cleanup memory
    video_capture_instance.release()
    
    print("\n[3/4] Compressing Tracking Data...")
    final_compressed_tracking_map = data_compressor.get_final_map()
    print(f"      Compression Result: {len(final_compressed_tracking_map)} total time blocks.")

    # -------------------------------------------------------------------------
    # NEW STEP: Calculate FFmpeg Crop Coordinates (The "Source of Truth")
    # -------------------------------------------------------------------------
    # We pre-calculate the exact top-left (X,Y) coordinates for FFmpeg's crop filter.
    # We enforce a strict 9:16 aspect ratio and clamp the values so the box never 
    # overflows the screen boundaries (which would cause FFmpeg errors/black bars).
    crop_height = video_metadata.video_height_pixels
    crop_width = int(crop_height * (9 / 16))
    
    for block in final_compressed_tracking_map:
        target_x = block.center_x_coordinate - (crop_width // 2)
        
        # Math.max(0, Math.min(max_x, target_x)) equivalent in Python
        clamped_x = max(0, min(video_metadata.video_width_pixels - crop_width, target_x))
        
        block.crop_x = clamped_x
        block.crop_y = 0  # Assuming vertical crop takes full height natively

    print("\n[4/4] Saving Final Recipe JSON...")
    # Create unique output folder
    timestamp_string: str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    run_output_directory: Path = outputs_directory / timestamp_string
    run_output_directory.mkdir(parents=True, exist_ok=True)
    
    recipe_output_file_path: Path = run_output_directory / "recipe.json"
    
    # Construct final JSON payload matching our agreed API schema
    final_json_payload: Dict[str, Any] = {
        "video_id": "playground_test_video",
        "status": "completed",
        "global_tracking": [asdict(block) for block in final_compressed_tracking_map],
        "clips": [
            # Mocking the segmentation boundaries for now
            {"clip_id": "clip_1", "start_time_sec": 15.0, "end_time_sec": 45.0},
            {"clip_id": "clip_2", "start_time_sec": 120.0, "end_time_sec": 150.0}
        ]
    }
    
    with open(recipe_output_file_path, "w") as json_file:
        json.dump(final_json_payload, json_file, indent=4)
        
    print(f"\n======================================================================")
    print(f"SUCCESS! Tracking complete.")
    print(f"Recipe saved to: {recipe_output_file_path}")
    print(f"======================================================================")


if __name__ == "__main__":
    # TODO: RESTORE - Revert target_frames_per_second to 15
    run_hybrid_tracking_pipeline(target_frames_per_second=1)
