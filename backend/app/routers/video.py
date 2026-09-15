"""
Video Ingestion Router
======================
Exposes API endpoints for receiving source videos either directly from user file uploads
or by fetching and converting streams from YouTube via yt-dlp.
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
