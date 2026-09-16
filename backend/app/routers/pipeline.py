"""
PIPELINE ROUTER
===============

OVERVIEW & ARCHITECTURE:
This module is the core API controller for the AI Pipeline. Following SOLID principles (specifically the 
Single Responsibility Principle), this file does NOT contain any heavy machine learning math, OpenCV operations, 
or AI logic. Its solely responsible for:
1. HTTP Request/Response validation and routing.
2. Managing FastAPI BackgroundTasks (thread spawning).
3. Maintaining the `pipeline_jobs_cache` global state dictionary for live polling.
4. Catching and standardizing HTTP Exceptions.

DETAILED SEQUENCE OF EVENTS (The "Pipeline"):
1. The client sends a `POST /api/v1/pipeline/process` request with a video UUID and configuration options.
2. The router validates that the video actually exists on disk in `storage/uploads/`.
3. The router checks `pipeline_jobs_cache`. If a task is already running for this UUID, it rejects the duplicate 
   request to prevent CPU melting (Edge Case Handled).
4. A new FastAPI `BackgroundTask` is spawned (`execute_pipeline_task`). The HTTP POST instantly returns `200 OK`.
5. In the background thread:
   a. The `update_progress` callback is instantiated. It checks for a `cancelled` flag on every tick.
   b. `run_tracking()` (MediaPipe) is called. It calculates 9:16 bounding boxes.
   c. `run_segmentation()` (Whisper) is called. It extracts subtitles and topic blocks.
   d. The final "Recipe" is saved to `pipeline_jobs_cache[uuid]["result"]`.
6. Meanwhile, the client sends `GET /api/v1/pipeline/progress/{uuid}` every 5 seconds to poll the live state.

SWAGGER USE CASES:
- Use `/process` to trigger asynchronous AI jobs.
- Use `/progress` to build real-time loading bars in the UI.
- Use `/cancel` to gracefully abort heavy threads.
"""
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

# ==============================================================================
#  STATE WARNING: IN-MEMORY CACHE
# ==============================================================================
# Currently, all AI jobs and final results (Tracking Recipe & Segmentation Data) 
# are stored in this volatile RAM dictionary (`pipeline_jobs_cache`). 
# 
# LIMITATION: If the FastAPI server (Uvicorn) restarts or crashes, this dictionary 
# is wiped clean. Any user refreshing the page after a restart will lose their AI results.
# 
# FUTURE UPGRADE PATH: 
# To make finished videos survive server restarts "for eternity", this should be upgraded 
# to save the final `response_model.model_dump()` to a physical `.json` file in 
# `backend/storage/recipes/` (or into a Postgres/Mongo database) upon completion.
# ==============================================================================
pipeline_jobs_cache: Dict[str, Any] = {}

@router.get(
    "/progress/{saved_filename}",
    summary="Get AI Pipeline Progress",
    description="Poll this endpoint every few seconds to retrieve the live status of the background AI processing job (tracking & segmentation).",
)
def get_pipeline_progress(saved_filename: str):
    job = pipeline_jobs_cache.get(saved_filename)
    if job:
        return job
        
    # Recovery mechanism: If the server restarted, check if it's already finished on disk!
    import json
    recipe_path = UPLOADS_DIR / f"{saved_filename}_recipe.json"
    if recipe_path.exists():
        try:
            with open(recipe_path, "r") as f:
                result = json.load(f)
            return {"step": "completed", "progress": 100.0, "result": result}
        except Exception:
            pass
            
    return {"step": "waiting", "progress": 0.0}

def execute_pipeline_task(request: PipelineProcessRequest, video_path: Path):
    """Background worker function that runs the heavy AI computations safely."""
    try:
        def update_progress(step: str, progress: float, hardware: str | None = None) -> bool:
            if request.saved_filename in pipeline_jobs_cache:
                # If the task was flagged as cancelled by the user, tell the worker to abort!
                if pipeline_jobs_cache[request.saved_filename].get("step") == "cancelled":
                    return False
                    
                pipeline_jobs_cache[request.saved_filename].update({"step": step, "progress": round(progress, 1)})
                if hardware:
                    pipeline_jobs_cache[request.saved_filename]["hardware"] = hardware
            return True
            
        update_progress("initializing", 0.0)
        
        # 1. Run Subject Tracking
        tracking_data = run_tracking(video_path, request.tracking_options, lambda p, h=None: update_progress("tracking", p, h))
        
        # 2. Run Semantic Segmentation
        extracted_clips = []
        if not request.skip_segmentation and pipeline_jobs_cache[request.saved_filename].get("step") != "cancelled":
            extracted_clips = run_segmentation(video_path, request.segmentation_options, lambda p: update_progress("segmentation", p))
            
        if pipeline_jobs_cache[request.saved_filename].get("step") == "cancelled":
            print(f"Task for {request.saved_filename} aborted gracefully.")
            return
            
        update_progress("completed", 100.0)
        
        import json
        
        # 3. Compile and Store the "Recipe" directly in memory for the frontend to fetch
        response_model = PipelineProcessResponse(
            video_id=request.saved_filename,
            status="completed",
            global_tracking=tracking_data,
            extracted_clips=extracted_clips
        )
        
        result_dict = response_model.model_dump()
        pipeline_jobs_cache[request.saved_filename]["result"] = result_dict
        
        # Save to disk to persist across server restarts
        recipe_path = UPLOADS_DIR / f"{request.saved_filename}_recipe.json"
        with open(recipe_path, "w") as f:
            json.dump(result_dict, f)

        
    except Exception as e:
        print(f"Pipeline Error: {e}")
        pipeline_jobs_cache[request.saved_filename] = {"step": "error", "progress": 0.0, "error_detail": str(e)}

@router.post(
    "/process",
    summary="Start AI Pipeline (Background Task)",
    description="""
### 🚀 Trigger AI Processing
Kicks off the heavy machine learning pipeline in a non-blocking background task.
- Validates the video exists.
- Triggers Semantic Segmentation (Whisper) and Subject Tracking (MediaPipe/OpenCV).
- Immediately returns a success status so the client can begin polling `/progress/{video_id}`.
- If a task is already running for this video, it rejects duplicate requests to save CPU.
""",
)
def process_video_pipeline(request: PipelineProcessRequest, background_tasks: BackgroundTasks):
    """
    Triggers the full AI pipeline in the background and immediately returns to prevent timeouts.
    """
    
    # In a real app, you would retrieve the file from AWS S3 or a local /storage volume
    video_path = UPLOADS_DIR / request.saved_filename
    
    if not video_path.exists():
        raise HTTPException(status_code=404, detail=f"Video file '{request.saved_filename}' not found in storage.")
        
    try:
        # Check the temporary in-memory cache to prevent ghost tasks
        existing_job = pipeline_jobs_cache.get(request.saved_filename)
        if existing_job and existing_job.get("step") not in ["waiting", "completed", "error"]:
            # Task is currently running! Do not spawn a new one.
            return {"status": "already_running", "video_id": request.saved_filename}

        # Register the background task and return immediately
        pipeline_jobs_cache[request.saved_filename] = {"step": "queued", "progress": 0.0}
        background_tasks.add_task(execute_pipeline_task, request, video_path)
        
        return {"status": "processing_started", "video_id": request.saved_filename}
    except Exception as e:
        # Catch unexpected AI pipeline crashes
        raise HTTPException(status_code=500, detail=f"Pipeline processing failed: {str(e)}")
@router.post(
    "/cancel/{saved_filename}",
    summary="Cancel Running AI Job",
    description="Sends a graceful kill signal to the active AI background task, causing it to safely abort without freezing the server.",
)
def cancel_pipeline(saved_filename: str):
    if saved_filename in pipeline_jobs_cache:
        current_step = pipeline_jobs_cache[saved_filename].get("step")
        if current_step not in ["completed", "error", "waiting"]:
            pipeline_jobs_cache[saved_filename]["step"] = "cancelled"
            return {"status": "cancelled", "message": "Kill signal sent to AI worker."}
        else:
            return {"status": "ignored", "message": "Job is not actively running."}
    raise HTTPException(status_code=404, detail="No active job found for this video.")

import json

@router.get(
    "/recipe/{saved_filename}",
    summary="Get Final AI Recipe",
    description="Fetches the persisted AI tracking and segmentation data for a video.",
)
def get_pipeline_recipe(saved_filename: str):
    recipe_path = UPLOADS_DIR / f"{saved_filename}_recipe.json"
    
    # Check if we have it on disk
    if recipe_path.exists():
        try:
            with open(recipe_path, "r") as f:
                return json.load(f)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to read recipe file: {e}")
            
    # Check memory cache as fallback
    job = pipeline_jobs_cache.get(saved_filename)
    if job and "result" in job:
        return job["result"]
        
    raise HTTPException(status_code=404, detail="Recipe not found. The AI pipeline has not processed this video yet.")
