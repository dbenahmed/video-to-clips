"""
EXPORT API ROUTER
=================
Handles the endpoints that trigger and monitor the FFmpeg export process.
Uses an Async Polling architecture to prevent HTTP timeouts and server crashes.
"""
import uuid
import asyncio
from typing import Dict, Any
from pathlib import Path
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from app.schemas.export import ExportClipRequest
from app.services.export_service import run_export_pipeline
from app.core.config import STORAGE_DIR, UPLOADS_DIR

router = APIRouter(prefix="/export", tags=["Export"])

STORAGE_UPLOADS_DIR = UPLOADS_DIR
STORAGE_EXPORTS_DIR = STORAGE_DIR / "exports"

# Ensure exports directory exists
STORAGE_EXPORTS_DIR.mkdir(parents=True, exist_ok=True)

# ==============================================================================
#  STATE WARNING: IN-MEMORY CACHE
# ==============================================================================
# Just like `pipeline_jobs_cache`, this tracks active FFmpeg exports in RAM.
export_jobs_cache: Dict[str, Any] = {}
# Tracks raw subprocesses so we can terminate them
active_ffmpeg_processes: Dict[str, Any] = {}

def execute_export_task(cache_key: str, request: ExportClipRequest, input_path: Path, output_path: Path):
    """The background worker that safely executes the FFmpeg Python service."""
    export_id = export_jobs_cache[cache_key]["export_id"]
    
    def save_process(p):
        active_ffmpeg_processes[export_id] = p
        
    try:
        run_export_pipeline(request, input_path, output_path, on_process_started=save_process)
        if export_jobs_cache[cache_key]["status"] != "cancelled":
            export_jobs_cache[cache_key]["status"] = "completed"
    except Exception as e:
        print(f"Export Error [{export_id}]: {e}")
        if export_jobs_cache[cache_key]["status"] != "cancelled":
            export_jobs_cache[cache_key]["status"] = "error"
            export_jobs_cache[cache_key]["error_detail"] = str(e)
    finally:
        active_ffmpeg_processes.pop(export_id, None)

@router.post(
    "/process", 
    summary="Start Concurrent Clip Export", 
    description="""
**Async Polling Architecture:**
This endpoint queues a clip for FFmpeg export in a background thread and **returns instantly**. 
It prevents HTTP timeouts and allows the client to trigger multiple exports simultaneously.

**Deduplication:**
If an export for the exact same video and time boundaries is already running, it will return `{"status": "already_running"}` and attach to the existing job.

**Returns:** 
A unique `export_id` which the client must use to poll the `/status/{export_id}` endpoint.
    """,
    responses={
        200: {
            "description": "Job queued successfully.",
            "content": {
                "application/json": {
                    "example": {"status": "queued", "export_id": "export_123abc"}
                }
            }
        },
        404: {"description": "Original video file not found."}
    }
)
def start_export_job(request: ExportClipRequest, background_tasks: BackgroundTasks):
    input_path = STORAGE_UPLOADS_DIR / request.saved_filename
    
    if not input_path.exists():
        raise HTTPException(status_code=404, detail="Original video file not found on disk.")
        
    # Prevent Duplicate Tasks: Check if this specific clip is already exporting
    # We use a unique string combining video ID and clip boundaries
    cache_key = f"{request.saved_filename}_{request.start_time}_{request.end_time}"
    
    # Clean up old cached jobs to prevent memory leaks in MVP
    if cache_key in export_jobs_cache:
        existing_status = export_jobs_cache[cache_key].get("status")
        if existing_status == "processing":
            return {"status": "already_running", "export_id": export_jobs_cache[cache_key]["export_id"]}
            
    # Generate a unique temporary filename for this export
    export_id = f"export_{uuid.uuid4().hex[:8]}"
    output_path = STORAGE_EXPORTS_DIR / f"{export_id}.mp4"
    
    # Register the job
    export_jobs_cache[cache_key] = {
        "export_id": export_id,
        "status": "processing"
    }
    
    # Spawn the background thread
    background_tasks.add_task(execute_export_task, cache_key, request, input_path, output_path)
    
    return {"status": "queued", "export_id": export_id}

@router.get(
    "/status/{export_id}",
    summary="Poll Export Status",
    description="""
Poll this endpoint every 2 seconds to check if the background FFmpeg process has finished.

**Possible Statuses:**
- `queued` / `processing`: FFmpeg is actively rendering.
- `completed`: The render is done. The client can now call the `/download/{export_id}` endpoint.
- `error`: The render failed. An `error_detail` string will be provided.
- `cancelled`: The render was aborted by the user via the `/cancel/{export_id}` endpoint.
    """,
    responses={
        200: {
            "description": "Current status of the job.",
            "content": {
                "application/json": {
                    "example": {"status": "processing", "error_detail": None}
                }
            }
        },
        404: {"description": "Export job not found in memory."}
    }
)
def get_export_status(export_id: str):
    # Search the cache for this export_id
    for cache_key, job_data in export_jobs_cache.items():
        if job_data["export_id"] == export_id:
            return {"status": job_data["status"], "error_detail": job_data.get("error_detail")}
            
    raise HTTPException(status_code=404, detail="Export job not found.")

@router.get(
    "/download/{export_id}",
    summary="Download Rendered Clip",
    description="""
Returns the final generated `9:16` MP4 file as a downloadable binary stream.

**Warning:**
This endpoint should *only* be called after the `/status/{export_id}` endpoint returns `"status": "completed"`.
    """,
    responses={
        200: {"description": "Returns the MP4 video file."},
        404: {"description": "Exported file not found on disk. It may have failed or been deleted."}
    }
)
def download_exported_clip(export_id: str):
    output_path = STORAGE_EXPORTS_DIR / f"{export_id}.mp4"
    if not output_path.exists():
        raise HTTPException(status_code=404, detail="Exported file not found on disk. Did it fail?")
        
    return FileResponse(
        path=output_path,
        filename=f"viral_clip_{export_id}.mp4",
        media_type="video/mp4"
    )

@router.post(
    "/cancel/{export_id}",
    summary="Cancel Mid-Flight Export",
    description="""
**CPU Protection Feature:**
Terminates a running FFmpeg process mid-render. 

By sending a `SIGTERM` directly to the `subprocess.Popen` handle, this endpoint instantly frees up server CPU and memory. 
The job status is immediately marked as `"cancelled"`, which the frontend polling loop will detect on its next tick.
    """,
    responses={
        200: {
            "description": "Job cancelled successfully.",
            "content": {
                "application/json": {
                    "example": {"status": "cancelled"}
                }
            }
        },
        404: {"description": "Export job not found in memory."}
    }
)
def cancel_export_job(export_id: str):
    for cache_key, job_data in export_jobs_cache.items():
        if job_data["export_id"] == export_id:
            job_data["status"] = "cancelled"
            
            # Kill the underlying process if it exists
            process = active_ffmpeg_processes.get(export_id)
            if process:
                try:
                    process.terminate()
                except Exception as e:
                    print(f"Failed to terminate process {export_id}: {e}")
                    
            return {"status": "cancelled"}
            
    raise HTTPException(status_code=404, detail="Export job not found.")
