import cv2
import urllib.request
from pathlib import Path
from typing import List, Optional, Tuple, Any

try:
    import mediapipe as mp
    from mediapipe.tasks import python as mp_python
    from mediapipe.tasks.python import vision as mp_vision
except ImportError:
    print("CRITICAL: Missing MediaPipe dependency. Please run pip install mediapipe")

from app.schemas.pipeline import TrackingOptions

class VideoMetadata:
    def __init__(self, capture: cv2.VideoCapture):
        self.total_frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
        self.frames_per_second = capture.get(cv2.CAP_PROP_FPS)
        self.video_width_pixels = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.video_height_pixels = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        if self.frames_per_second > 0:
            self.duration_seconds = self.total_frames / self.frames_per_second
        else:
            self.duration_seconds = 0.0

class TrackingDataCompressor:
    def __init__(self, pixel_movement_threshold: int):
        self.pixel_movement_threshold = pixel_movement_threshold
        self.compressed_tracking_map = []
        self.active_time_range = None

    def add_data_point(self, current_time_seconds: float, center_x: int, center_y: int) -> None:
        if self.active_time_range is None:
            self.active_time_range = {
                "start_time_seconds": current_time_seconds,
                "end_time_seconds": current_time_seconds,
                "center_x_coordinate": center_x,
                "center_y_coordinate": center_y
            }
            return

        movement_distance = abs(center_x - self.active_time_range["center_x_coordinate"])

        if movement_distance > self.pixel_movement_threshold:
            self.compressed_tracking_map.append(self.active_time_range)
            self.active_time_range = {
                "start_time_seconds": current_time_seconds,
                "end_time_seconds": current_time_seconds,
                "center_x_coordinate": center_x,
                "center_y_coordinate": center_y
            }
        else:
            self.active_time_range["end_time_seconds"] = current_time_seconds

    def get_final_map(self) -> List[dict]:
        if self.active_time_range is not None:
            self.compressed_tracking_map.append(self.active_time_range)
            self.active_time_range = None
        return self.compressed_tracking_map


class HybridVideoTracker:
    def __init__(self, video_metadata: VideoMetadata):
        self.video_metadata = video_metadata
        
        # Download mediapipe model if not exists
        model_path = Path(__file__).parent / "blaze_face_short_range.tflite"
        if not model_path.exists():
            model_url = "https://storage.googleapis.com/mediapipe-models/face_detector/blaze_face_short_range/float16/1/blaze_face_short_range.tflite"
            urllib.request.urlretrieve(model_url, str(model_path))

        base_options = mp_python.BaseOptions(model_asset_path=str(model_path))
        options = mp_vision.FaceDetectorOptions(base_options=base_options, min_detection_confidence=0.65)
        self.mediapipe_face_detector = mp_vision.FaceDetector.create_from_options(options)
        
        self.opencv_csrt_tracker = None
        self.last_known_face_bounding_box = None

    def process_frame(self, frame_bgr: Any) -> Tuple[int, int]:
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)
        mediapipe_results = self.mediapipe_face_detector.detect(mp_image)
        
        if mediapipe_results.detections:
            primary_face = mediapipe_results.detections[0]
            bbox = primary_face.bounding_box
            self.last_known_face_bounding_box = (bbox.origin_x, bbox.origin_y, bbox.width, bbox.height)
            self.opencv_csrt_tracker = None 
            
            center_x = bbox.origin_x + (bbox.width // 2)
            center_y = bbox.origin_y + (bbox.height // 2)
            return center_x, center_y

        elif self.last_known_face_bounding_box is not None:
            if self.opencv_csrt_tracker is None:
                self.opencv_csrt_tracker = cv2.TrackerCSRT_create()  # type: ignore
                self.opencv_csrt_tracker.init(frame_bgr, self.last_known_face_bounding_box)
                
            tracking_success, new_bounding_box = self.opencv_csrt_tracker.update(frame_bgr)
            
            if tracking_success:
                fallback_x, fallback_y, fallback_w, fallback_h = [int(v) for v in new_bounding_box]
                return fallback_x + (fallback_w // 2), fallback_y + (fallback_h // 2)
            else:
                self.opencv_csrt_tracker = None
                self.last_known_face_bounding_box = None

        # Ultimate fallback
        return self.video_metadata.video_width_pixels // 2, self.video_metadata.video_height_pixels // 2


def run_tracking(video_path: Path, options: TrackingOptions, progress_callback=None) -> List[dict]:
    """Runs the hybrid tracking algorithm on the video."""
    capture = cv2.VideoCapture(str(video_path))
    
    if not capture.isOpened() or int(capture.get(cv2.CAP_PROP_FRAME_COUNT)) <= 0:
        capture.release()
        raise ValueError("Corrupted or invalid video file.")
        
    metadata = VideoMetadata(capture)
    
    frame_skip_interval = max(1, int(metadata.frames_per_second / options.target_frames_per_second))
    
    tracker = HybridVideoTracker(video_metadata=metadata)
    compressor = TrackingDataCompressor(pixel_movement_threshold=options.pixel_movement_threshold)
    
    current_frame_index = 0
    
    while True:
        read_success, frame_bgr = capture.read()
        if not read_success:
            break
            
        if current_frame_index % frame_skip_interval == 0:
            current_time = current_frame_index / metadata.frames_per_second
            cx, cy = tracker.process_frame(frame_bgr)
            compressor.add_data_point(current_time, cx, cy)
            
        if current_frame_index % 10 == 0 and progress_callback:
            progress = min(99.0, (current_frame_index / metadata.total_frames) * 100.0)
            progress_callback(progress)
            
        current_frame_index += 1
        
    capture.release()
    return compressor.get_final_map()
