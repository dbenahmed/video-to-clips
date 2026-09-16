"""
VIDEO INGESTION ROUTER
======================

OVERVIEW & ARCHITECTURE:
This module handles all external media entering the system (Milestone 2). Following the Single 
Responsibility Principle, it isolates the HTTP layer from the actual downloading and file I/O logic. 
The heavy lifting is delegated to `upload_service.py` (chunked disk writing) and `youtube_service.py` 
(yt-dlp subprocessing).

DETAILED SEQUENCE OF EVENTS:
1. Direct Uploads (`POST /api/upload`):
   a. Client sends a multipart binary file.
   b. Router triggers `save_uploaded_video` in `upload_service.py`.
   c. The file is assigned a collision-resistant UUID (e.g. `1234-5678_original.mp4`).
   d. The file is streamed to `storage/uploads/` in chunks to prevent RAM exhaustion.
   e. The frontend receives the generated UUID to use in all future AI endpoints.

2. YouTube Ingestion (`POST /api/download-youtube`):
   a. Client sends a YouTube URL string.
   b. Router triggers `download_from_youtube` in `youtube_service.py`.
   c. A python subprocess runs `yt-dlp` to fetch the highest quality stream.
   d. The stream is packaged into an MP4 and saved to `storage/uploads/`.
   e. The frontend receives the UUID.

3. Session Recovery (`GET /api/video/{uuid}`):
   a. If a user refreshes their browser, the React UI pings this endpoint.
   b. The router checks if the file still exists in the local filesystem.
   c. If true, the session is recovered.

SWAGGER USE CASES:
- Use `/upload` for raw .mp4, .mov, .webm files from disk.
- Use `/download-youtube` for scraping public web video content.
- Use `/video/{uuid}` to reconstruct frontend UI state without re-uploading.
"""

from fastapi import APIRouter, UploadFile, File, status
from app.schemas.video import (
    YouTubeDownloadRequest,
    VideoUploadResponse,
    YouTubeDownloadResponse,
    ErrorResponse,
)
from app.services.upload_service import save_uploaded_video
from app.services.youtube_service import download_from_youtube
from app.core.config import UPLOADS_DIR
from fastapi import HTTPException
from app.services.upload_service import save_uploaded_video
from app.services.youtube_service import download_from_youtube

router = APIRouter(
    prefix="/api",
    tags=["Video Ingestion"],
)


@router.post(
    "/upload",
    response_model=VideoUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a local video file (Direct Ingestion)",
    description="""
### 📥 Direct Video Upload Endpoint

Accepts a multipart video file and performs the following pipeline steps:
1. **Format Validation**: Ensures the uploaded file extension matches one of the supported video types (`.mp4`, `.mov`, `.avi`, `.mkv`, `.webm`).
2. **UUID Generation**: Generates a collision-resistant UUID to prevent accidental file overwrites.
3. **Chunk-based Streaming**: Streams the binary file to disk in manageable buffer chunks to ensure zero memory exhaustion on large video files.
4. **Storage Persistence**: Saves the file safely into `backend/storage/uploads/`.
5. **Static Streaming URL**: Generates a public relative stream URL accessible by HTML5 video players.
""",
    responses={
        201: {
            "description": "Video uploaded successfully and ready for analysis.",
            "model": VideoUploadResponse,
        },
        400: {
            "description": "Unsupported file format or invalid request.",
            "model": ErrorResponse,
        },
        500: {
            "description": "Internal server error occurred while writing file to disk.",
            "model": ErrorResponse,
        },
    },
)
async def upload_endpoint(file: UploadFile = File(..., description="The binary video file to upload (.mp4, .mov, .avi, .mkv, .webm)")):
    return save_uploaded_video(file)


@router.post(
    "/download-youtube",
    response_model=YouTubeDownloadResponse,
    status_code=status.HTTP_200_OK,
    summary="Download video from YouTube (URL Ingestion)",
    description="""
### 🎥 YouTube URL Ingestion Endpoint

Fetches and downloads a public YouTube video to the server's local storage:
1. **URL Validation**: Verifies that a valid YouTube URL string is provided.
2. **Stream Selection**: Configures `yt-dlp` to select the highest quality video and audio streams.
3. **Format Packaging**: Merges video and audio streams cleanly into a universally compatible MP4 container.
4. **Metadata Extraction**: Extracts the official video title, duration in seconds, and generated file path.
5. **Static Streaming URL**: Exposes the downloaded file under `/storage/uploads/` for immediate browser playback.
""",
    responses={
        200: {
            "description": "YouTube video downloaded successfully.",
            "model": YouTubeDownloadResponse,
        },
        400: {
            "description": "Empty URL or invalid YouTube link.",
            "model": ErrorResponse,
        },
        500: {
            "description": "yt-dlp download failed or video unavailable.",
            "model": ErrorResponse,
        },
    },
)
def youtube_download_endpoint(payload: YouTubeDownloadRequest):
    return download_from_youtube(payload.url)


@router.get(
    "/video/{saved_filename}",
    response_model=VideoUploadResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Video Metadata (Refresh Recovery)",
    description="""
### 🔄 Session Recovery Endpoint
When a user refreshes the page, the frontend pings this endpoint with the video's UUID to verify if the file still safely exists in the backend storage. 
Returns the original filename and stream URL so the UI can instantly recover its state without re-uploading.
""",
)
def get_video_status_endpoint(saved_filename: str):
    """Verifies if a video file exists in storage and returns its metadata for the frontend to render."""
    video_path = UPLOADS_DIR / saved_filename
    if not video_path.exists():
        raise HTTPException(status_code=404, detail="Video not found in storage")
        
    # Extract original name (e.g. "uuid_original.mp4" -> "original.mp4")
    parts = saved_filename.split("_", 1)
    video_id = parts[0] if len(parts) > 1 else "unknown-id"
    original_name = parts[1] if len(parts) > 1 else saved_filename
    size_bytes = video_path.stat().st_size
    
    return {
        "status": "success",
        "id": video_id,
        "original_name": original_name,
        "saved_filename": saved_filename,
        "url": f"/storage/uploads/{saved_filename}",
        "size_bytes": size_bytes
    }
