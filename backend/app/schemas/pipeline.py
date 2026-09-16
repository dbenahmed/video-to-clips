from pydantic import BaseModel, Field
from typing import List, Optional

class SegmentationOptions(BaseModel):
    """Configuration options for the AI video segmentation algorithm."""
    similarity_drop_threshold: float = Field(
        default=0.2, 
        description="The sensitivity of topic cuts. Lower (e.g. 0.1) creates fewer, longer cuts. Higher (e.g. 0.4) creates many short cuts."
    )
    min_clip_duration_seconds: float = Field(
        default=30.0, 
        description="The minimum acceptable duration for a clip. Anything shorter is classified as dead air or a tangent and discarded."
    )
    max_clip_duration_seconds: float = Field(
        default=60.0, 
        description="The maximum acceptable duration. Rambling topics longer than this will be truncated to capture just the hook."
    )
    whisper_model_size: str = Field(
        default="base", 
        description="The size of the Whisper AI transcription model (e.g., 'tiny', 'base', 'small', 'medium', 'large')."
    )

class TrackingOptions(BaseModel):
    """Configuration options for the subject tracking algorithm."""
    target_frames_per_second: int = Field(
        default=1, 
        description="How many frames per second to process. 1 FPS is extremely fast but blocky. 15 FPS is smooth but 15x slower."
    )
    pixel_movement_threshold: int = Field(
        default=50, 
        description="The amount of pixels the subject must move before the compressor locks in a new time block."
    )

class PipelineProcessRequest(BaseModel):
    """The request payload expected from the frontend to trigger a full processing job."""
    saved_filename: str = Field(
        ..., 
        description="The exact 'saved_filename' returned by the /upload or /download-youtube endpoint."
    )
    skip_segmentation: bool = Field(
        default=False,
        description="If true, bypasses the Whisper transcription entirely and only returns tracking data."
    )
    segmentation_options: SegmentationOptions = Field(
        default_factory=SegmentationOptions,
        description="User-defined tweaks for how the AI segments the video."
    )
    tracking_options: TrackingOptions = Field(
        default_factory=TrackingOptions,
        description="User-defined tweaks for how the AI tracks faces."
    )

class ClipResponse(BaseModel):
    """A single extracted short-form clip."""
    clip_id: str
    start_time_seconds: float
    end_time_seconds: float
    duration_seconds: float
    text_transcript: str
    extraction_reasoning: str

class TrackingBlockResponse(BaseModel):
    """A compressed block of time where the subject remains relatively still."""
    start_time_seconds: float
    end_time_seconds: float
    center_x_coordinate: int = Field(description="The exact center pixel X coordinate of the face.")
    center_y_coordinate: int = Field(description="The exact center pixel Y coordinate of the face.")
    crop_x: int = Field(default=0, description="The pre-calculated top-left X coordinate for FFmpeg's 9:16 crop filter. It is clamped to prevent video boundary overflow.")
    crop_y: int = Field(default=0, description="The pre-calculated top-left Y coordinate for FFmpeg's 9:16 crop filter.")

# Alias for backwards compatibility
TrackingBlock = TrackingBlockResponse

class PipelineProcessResponse(BaseModel):
    """The final 'Recipe' returned to the frontend when processing completes."""
    video_id: str
    status: str
    global_tracking: List[TrackingBlockResponse]
    extracted_clips: List[ClipResponse]
