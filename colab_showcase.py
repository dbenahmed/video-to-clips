import sys
import os
from pathlib import Path

# 1. Setup paths so Python can find our backend modules
sys.path.append(os.path.join(os.path.dirname(__file__), "backend"))

# 2. Import our core backend services
from app.services.youtube_service import download_youtube_video
from app.services.segmentation import run_segmentation, SegmentationOptions
from app.services.tracking import run_tracking, TrackingOptions
from app.services.export_service import run_export_pipeline
from app.schemas.export import ExportClipRequest, TrackingBlock
from app.core.config import UPLOADS_DIR

def run_colab_showcase():
    print("==================================================")
    print("🚀 STARTING COLAB GPU SHOWCASE PIPELINE 🚀")
    print("==================================================")
    
    # ---------------------------------------------------------
    # EDIT THIS URL TO YOUR SHOWCASE VIDEO!
    # (A podcast or talking-head video works best)
    youtube_url = "https://www.youtube.com/watch?v=F0J_P_7_8vU" 
    # ---------------------------------------------------------
    
    print(f"\n[1/4] Downloading Video: {youtube_url}")
    video_info = download_youtube_video(youtube_url)
    saved_filename = video_info.saved_filename if hasattr(video_info, "saved_filename") else video_info["saved_filename"]
    video_path = UPLOADS_DIR / saved_filename
    print(f"✅ Downloaded to {video_path}")
    
    print("\n[2/4] Running AI Segmentation (Whisper GPU)...")
    # Using 'small' model because the Colab GPU can handle it easily for high accuracy!
    seg_options = SegmentationOptions(
        similarity_drop_threshold=0.2,
        min_clip_duration_seconds=15.0,
        max_clip_duration_seconds=60.0,
        whisper_model_size="small" 
    )
    clips = run_segmentation(video_path, seg_options)
    
    if not clips:
        print("❌ No viral clips found in this video.")
        return
        
    best_clip = clips[0] # Take the first golden clip
    print(f"✅ Found best clip: {best_clip['duration_seconds']:.1f}s - {best_clip['extraction_reasoning']}")
    print(f"Transcript: {best_clip['text_transcript'][:100]}...")
    
    print("\n[3/4] Running Hybrid Tracking (MediaPipe + OpenCV)...")
    track_options = TrackingOptions(
        target_frames_per_second=2, # Smooth tracking since we have GPU power
        pixel_movement_threshold=40
    )
    tracking_data = run_tracking(video_path, track_options)
    print(f"✅ Generated {len(tracking_data)} tracking points.")
    
    print("\n[4/4] Exporting Final Vertical Video...")
    output_filename = f"SHOWCASE_RESULT_{saved_filename}"
    output_path = UPLOADS_DIR / output_filename
    
    # Format the tracking data to match our API schema
    export_tracking_blocks = [
        TrackingBlock(**block) for block in tracking_data
    ]
    
    export_req = ExportClipRequest(
        saved_filename=saved_filename,
        start_time=best_clip["start_time_seconds"],
        end_time=best_clip["end_time_seconds"],
        tracking_data=export_tracking_blocks
    )
    
    run_export_pipeline(export_req, video_path, output_path)
    
    print("\n==================================================")
    print(f"🎉 SHOWCASE COMPLETE! 🎉")
    print(f"Your vertical AI video is ready at: {output_path}")
    print("Download it from the Colab file explorer on the left!")
    print("==================================================")

if __name__ == "__main__":
    run_colab_showcase()
