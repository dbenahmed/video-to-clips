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

# Optional: Paste your raw YouTube Cookie string here if YouTube requires authentication on Colab
COLAB_YOUTUBE_COOKIE = os.environ.get("YOUTUBE_COOKIE", None)

def download_video_for_colab(youtube_url: str):
    """Independent Colab video downloader supporting custom Cookie headers."""
    import uuid
    import yt_dlp
    from app.core.config import UPLOADS_DIR, FFMPEG_PATH
    
    unique_id = str(uuid.uuid4())
    output_template = str(UPLOADS_DIR / f"{unique_id}.%(ext)s")
    
    opts = {
        "outtmpl": output_template,
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "merge_output_format": "mp4",
        "ffmpeg_location": FFMPEG_PATH,
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "extractor_args": {
            "youtube": {
                "player_client": ["android", "ios", "m3u8"]
            }
        }
    }
    
    if COLAB_YOUTUBE_COOKIE:
        opts["http_headers"] = {"Cookie": COLAB_YOUTUBE_COOKIE}
        
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(youtube_url, download=True)
        ext = info.get("ext") or "mp4"
        return f"{unique_id}.{ext}"

def run_colab_showcase():
    print("==================================================")
    print("🚀 STARTING COLAB GPU SHOWCASE PIPELINE 🚀")
    print("==================================================")
    
    # ---------------------------------------------------------
    # EDIT THIS URL TO YOUR SHOWCASE VIDEO!
    # (A podcast or talking-head video works best)
    youtube_url = "https://youtu.be/_g4l7YkDQwA?si=iW2DPHcNhb47QWbX" 
    # ---------------------------------------------------------
    
    print(f"\n[1/4] Downloading Video: {youtube_url}")
    try:
        saved_filename = download_video_for_colab(youtube_url)
        video_path = UPLOADS_DIR / saved_filename
        print(f"✅ Downloaded YouTube Video to {video_path}")
    except Exception as e:
        print(f"⚠️ YouTube blocked direct download on Colab IP: {e}")
        print("🔄 Using direct fallback sample MP4 video to run the AI showcase pipeline...")
        import urllib.request
        fallback_url = "https://github.com/intel-iot-devkit/sample-videos/raw/master/head-pose-face-detection-female-and-male.mp4"
        saved_filename = "colab_fallback_sample.mp4"
        video_path = UPLOADS_DIR / saved_filename
        if not video_path.exists():
            urllib.request.urlretrieve(fallback_url, video_path)
        print(f"✅ Fallback sample video ready at {video_path}")
    
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
