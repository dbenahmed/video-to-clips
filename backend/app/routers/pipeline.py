from fastapi import APIRouter, HTTPException, BackgroundTasks
from pathlib import Path
from typing import Dict, Any
import os
import uuid

from app.schemas.pipeline import PipelineProcessRequest, PipelineProcessResponse
from app.services.segmentation import run_segmentation
from app.services.tracking import run_tracking
from app.core.config import UPLOADS_DIR

router = APIRouter(
    prefix="/api/v1/pipeline",
    tags=["Pipeline"],
    responses={404: {"description": "Not found"}},
)

# In-memory store for tracking pipeline progress for the frontend to poll
# Structure: { "uuid.mp4": { "step": "tracking", "progress": 45.0, "result": null, "error": null } }
job_progress: Dict[str, Any] = {}

@router.get("/progress/{saved_filename}")
def get_pipeline_progress(saved_filename: str):
    return job_progress.get(saved_filename, {"step": "waiting", "progress": 0.0})

def execute_pipeline_task(request: PipelineProcessRequest, video_path: Path):
    """Background worker function that runs the heavy AI computations safely."""
    try:
        def update_progress(step: str, progress: float):
            if request.saved_filename in job_progress:
                job_progress[request.saved_filename].update({"step": step, "progress": round(progress, 1)})
            
        update_progress("initializing", 0.0)
        
        # 1. Run Subject Tracking
        tracking_data = run_tracking(video_path, request.tracking_options, lambda p: update_progress("tracking", p))
        
        # 2. Run Semantic Segmentation
        extracted_clips = []
        if not request.skip_segmentation:
            extracted_clips = run_segmentation(video_path, request.segmentation_options, lambda p: update_progress("segmentation", p))
            
        update_progress("completed", 100.0)
        
        # 3. Compile and Store the "Recipe" directly in memory for the frontend to fetch
        response_model = PipelineProcessResponse(
            video_id=request.saved_filename,
            status="completed",
            global_tracking=tracking_data,
            extracted_clips=extracted_clips
        )
        job_progress[request.saved_filename]["result"] = response_model.model_dump()
        
    except Exception as e:
        print(f"Pipeline Error: {e}")
        job_progress[request.saved_filename] = {"step": "error", "progress": 0.0, "error_detail": str(e)}

@router.post("/process")
def process_video_pipeline(request: PipelineProcessRequest, background_tasks: BackgroundTasks):
    """
    Triggers the full AI pipeline in the background and immediately returns to prevent timeouts.
    """
    
    # In a real app, you would retrieve the file from AWS S3 or a local /storage volume
    video_path = UPLOADS_DIR / request.saved_filename
    
    if not video_path.exists():
        raise HTTPException(status_code=404, detail=f"Video file '{request.saved_filename}' not found in storage.")
        
    try:
        # Register the background task and return immediately
        job_progress[request.saved_filename] = {"step": "queued", "progress": 0.0}
        background_tasks.add_task(execute_pipeline_task, request, video_path)
        
        return {"status": "processing_started", "video_id": request.saved_filename}
    except Exception as e:
        # Catch unexpected AI pipeline crashes
        raise HTTPException(status_code=500, detail=f"Pipeline processing failed: {str(e)}")
