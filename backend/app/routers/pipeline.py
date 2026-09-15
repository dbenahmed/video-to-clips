from fastapi import APIRouter, HTTPException, BackgroundTasks
from pathlib import Path
import os
import uuid

from app.schemas.pipeline import PipelineProcessRequest, PipelineProcessResponse
from app.services.segmentation import run_segmentation
from app.services.tracking import run_tracking

router = APIRouter(
    prefix="/api/v1/pipeline",
    tags=["Pipeline"],
    responses={404: {"description": "Not found"}},
)

# For a production application, you would use Celery or RQ to handle this in the background
# and provide a WebSockets or Polling endpoint to check status. 
# For this MVP, we process synchronously so the frontend can just await the HTTP response.
@router.post("/process", response_model=PipelineProcessResponse)
def process_video_pipeline(request: PipelineProcessRequest):
    """
    Executes the full AI pipeline (Tracking + Segmentation) on an uploaded video.
    
    This is a long-running synchronous request. The frontend should display a loading spinner 
    while waiting for this endpoint to return.
    """
    
    # In a real app, you would retrieve the file from AWS S3 or a local /storage volume
    storage_dir = Path("backend/storage/uploads")
    video_path = storage_dir / request.saved_filename
    
    if not video_path.exists():
        raise HTTPException(status_code=404, detail=f"Video file '{request.saved_filename}' not found in storage.")
        
    try:
        print(f"Starting pipeline for {request.saved_filename}...")
        
        # 1. Run Subject Tracking
        print("--> Running Hybrid Tracking...")
        tracking_data = run_tracking(video_path, request.tracking_options)
        
        # 2. Run Semantic Segmentation
        print("--> Running Semantic Segmentation...")
        extracted_clips = run_segmentation(video_path, request.segmentation_options)
        
        # 3. Compile and Return the "Recipe"
        return PipelineProcessResponse(
            video_id=request.saved_filename,
            status="completed",
            global_tracking=tracking_data,
            extracted_clips=extracted_clips
        )
        
    except ValueError as e:
        # Catch our custom corruption errors
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Catch unexpected AI pipeline crashes
        raise HTTPException(status_code=500, detail=f"Pipeline processing failed: {str(e)}")
