"""
EXPORT SCHEMAS
==============
Defines the request and response models for the FFmpeg export pipeline.
"""
from pydantic import BaseModel, Field
from typing import List
from app.schemas.pipeline import TrackingBlockResponse

# Alias for compatibility with colab_showcase and external services
TrackingBlock = TrackingBlockResponse

class ExportClipRequest(BaseModel):
    """Payload sent by the frontend to trigger a video export."""
    saved_filename: str = Field(..., description="The UUID of the original source video on disk.")
    start_time: float = Field(..., description="The start time of the clip in seconds.")
    end_time: float = Field(..., description="The end time of the clip in seconds.")
    tracking_data: List[TrackingBlockResponse] = Field(
        ..., 
        description="The raw tracking data blocks. Sent by the client so the backend remains stateless."
    )
