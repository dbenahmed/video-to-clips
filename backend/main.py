"""
Main Application Entrypoint
===========================
Project: Video-to-Clips
Description: Fast, modular FastAPI backend for video ingestion, AI tracking, and vertical clipping.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import STORAGE_DIR, CORS_ORIGINS
from app.routers.video import router as video_router
from app.routers.pipeline import router as pipeline_router

# ==============================================================================
# OpenAPI Tags Metadata (Shown prominently in Swagger UI at /docs)
# ==============================================================================
tags_metadata = [
    {
        "name": "Video Ingestion",
        "description": (
            "Endpoints responsible for getting video content into the system. "
            "Supports **Direct Multipart File Uploads** and **Automated YouTube Video Downloads** via `yt-dlp`. "
            "All ingested files are assigned a collision-resistant UUID and saved inside the dedicated `storage/uploads/` directory."
        ),
    },
    {
        "name": "Pipeline",
        "description": (
            "The core AI engine. Exposes endpoints to trigger the full **Semantic Video Segmentation** "
            "and **Hybrid Subject Tracking** algorithms on uploaded videos. Highly configurable."
        ),
    },
    {
        "name": "Health & Status",
        "description": (
            "Monitoring and connectivity diagnostic endpoints. "
            "Used by the React frontend navbar to confirm real-time server availability."
        ),
    },
]

# ==============================================================================
# 1. FastAPI Application Initialization with Rich Swagger Documentation
# ==============================================================================
app = FastAPI(
    title="🎬 Video-to-Clips API",
    description="""
## Overview
Welcome to the **Video-to-Clips** backend specification.

This API serves as the engine for turning raw horizontal videos into engaging **9:16 vertical shorts and clips**.

### 🌟 Current Capabilities (Milestones 1, 2 & 3):
* **Direct Video File Uploads**: Upload `.mp4`, `.mov`, `.avi`, `.mkv`, and `.webm` files safely with chunk-based disk writes.
* **YouTube Ingestion**: Provide any public YouTube URL to download the highest-quality MP4 stream automatically using `yt-dlp`.
* **UUID Isolation**: Every video receives a globally unique session ID to prevent collisions.
* **Direct Media Streaming**: Ingested files are immediately accessible via the mounted `/storage` route for instant browser playback.
* **Semantic Video Segmentation**: AI-powered transcription and topic clustering to extract 30-60s golden clips.
* **Hybrid Subject Tracking**: MediaPipe + OpenCV tracking to keep the subject centered in 9:16 vertical crops.

### 🛣️ Next Up (Frontend Integration):
* Build out the React UI to consume the `/api/v1/pipeline/process` endpoint.
* Implement a loading screen for the pipeline processing.
    """,
    version="1.0.0",
    openapi_tags=tags_metadata,
    docs_url="/docs",       # Interactive Swagger UI: http://127.0.0.1:8000/docs
    redoc_url="/redoc",     # Alternative clean ReDoc: http://127.0.0.1:8000/redoc
)

# ==============================================================================
# 2. CORS (Cross-Origin Resource Sharing) Middleware
# ==============================================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==============================================================================
# 3. Static File Mounting
# ==============================================================================
# Mounts the backend/storage folder so videos can be streamed via HTTP:
# e.g., http://127.0.0.1:8000/storage/uploads/<saved_filename>
app.mount(
    "/storage",
    StaticFiles(directory=str(STORAGE_DIR)),
    name="storage",
)

# ==============================================================================
# 4. Router Registration
# ==============================================================================
app.include_router(video_router)
app.include_router(pipeline_router)


# ==============================================================================
# 5. Health Check & Diagnostic Endpoints
# ==============================================================================
@app.get(
    "/",
    tags=["Health & Status"],
    summary="Root Service Status",
    description="Returns service availability, welcome message, and link to interactive documentation.",
)
def read_root():
    return {
        "status": "online",
        "service": "Video-to-Clips API",
        "version": "1.0.0",
        "documentation": "/docs",
    }


@app.get(
    "/api/test",
    tags=["Health & Status"],
    summary="Frontend-to-Backend Connectivity Test",
    description="Ping-pong endpoint queried by the React frontend to display the live green 'FastAPI Online' badge.",
)
def test_endpoint():
    return {
        "status": "success",
        "message": "Backend and Frontend are successfully connected!",
    }
