"""
Schemas Module (Data Transfer Objects & API Contracts)
======================================================
Defines typed request and response models with detailed Swagger UI examples,
field-level descriptions, and JSON schema metadata for API consumers and clients.
"""

from pydantic import BaseModel, Field


class YouTubeDownloadRequest(BaseModel):
    """Payload schema required to download a video from YouTube."""
    url: str = Field(
        ...,
        description="Public URL of the YouTube video to be ingested by the pipeline.",
        examples=["https://www.youtube.com/watch?v=dQw4w9WgXcQ"]
    )

    class Config:
        json_schema_extra = {
            "example": {
                "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
            }
        }


class VideoUploadResponse(BaseModel):
    """Response returned upon successful direct video file upload."""
    status: str = Field("success", description="Status code or state indicator of the operation", examples=["success"])
    id: str = Field(..., description="Unique UUID assigned to this video session", examples=["9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d"])
    original_name: str = Field(..., description="Original name of the uploaded file", examples=["podcast_interview.mp4"])
    saved_filename: str = Field(..., description="Collision-proof filename stored in backend/storage/uploads/", examples=["9b1deb4d_podcast_interview.mp4"])
    url: str = Field(..., description="Relative HTTP URL used by the frontend to stream or preview the video", examples=["/storage/uploads/9b1deb4d_podcast_interview.mp4"])
    size_bytes: int = Field(..., description="Exact file size on disk measured in bytes", examples=[15728640])

    class Config:
        json_schema_extra = {
            "example": {
                "status": "success",
                "id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
                "original_name": "podcast_interview.mp4",
                "saved_filename": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d_podcast_interview.mp4",
                "url": "/storage/uploads/9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d_podcast_interview.mp4",
                "size_bytes": 15728640
            }
        }


class YouTubeDownloadResponse(BaseModel):
    """Response returned upon successful download and ingestion of a YouTube video."""
    status: str = Field("success", description="Status indicator of the operation", examples=["success"])
    id: str = Field(..., description="Unique UUID assigned to this ingested video", examples=["3fa85f64-5717-4562-b3fc-2c963f66afa6"])
    title: str = Field(..., description="Video title fetched from YouTube metadata", examples=["How AI is Changing Content Creation"])
    duration_seconds: int = Field(..., description="Total length of the video in seconds", examples=[240])
    saved_filename: str = Field(..., description="Generated MP4 filename in backend/storage/uploads/", examples=["3fa85f64-5717-4562-b3fc-2c963f66afa6.mp4"])
    url: str = Field(..., description="Relative HTTP URL used by the frontend to stream or preview the video", examples=["/storage/uploads/3fa85f64-5717-4562-b3fc-2c963f66afa6.mp4"])

    class Config:
        json_schema_extra = {
            "example": {
                "status": "success",
                "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                "title": "How AI is Changing Content Creation",
                "duration_seconds": 240,
                "saved_filename": "3fa85f64-5717-4562-b3fc-2c963f66afa6.mp4",
                "url": "/storage/uploads/3fa85f64-5717-4562-b3fc-2c963f66afa6.mp4"
            }
        }


class ErrorResponse(BaseModel):
    """Standardized error structure returned when a request fails."""
    detail: str = Field(..., description="Detailed explanation of why the operation failed", examples=["Unsupported file format '.exe'. Allowed formats: .avi, .mkv, .mov, .mp4, .webm"])
