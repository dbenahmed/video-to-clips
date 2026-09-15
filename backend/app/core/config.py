"""
Configuration Module
====================
- Centralizes all application settings,
  directory paths, media constraints, and binary tool locations.
- Shared constants (directories, allowed extensions, FFmpeg binary)
  are defined once here.
"""

import shutil
from pathlib import Path

# Base backend directory: c:\Users\...\backend
BACKEND_DIR: Path = Path(__file__).resolve().parent.parent.parent

# Storage directories
STORAGE_DIR: Path = BACKEND_DIR / "storage"
UPLOADS_DIR: Path = STORAGE_DIR / "uploads"
CLIPS_DIR: Path = STORAGE_DIR / "clips"

# Ensure all critical storage directories exist at application startup
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
CLIPS_DIR.mkdir(parents=True, exist_ok=True)

# Allowed video extensions for direct uploads
ALLOWED_VIDEO_EXTENSIONS: set[str] = {
    ".mp4",
    ".mov",
    ".avi",
    ".mkv",
    ".webm",
}

# CORS settings: Which origins are allowed to interact with the API
CORS_ORIGINS: list[str] = [
    "http://localhost:5173",  # Default Vite React local dev server
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "*",                      # Permissive fallback for local testing
]

# FFmpeg Executable Detection (Zero System-wide Pollution)
# 1. First priority: Isolated venv binary from `imageio-ffmpeg`
# 2. Second priority: Standard system PATH (used later inside Docker containers)
try:
    import imageio_ffmpeg
    FFMPEG_PATH: str = imageio_ffmpeg.get_ffmpeg_exe()
except Exception:
    FFMPEG_PATH: str = shutil.which("ffmpeg") or "ffmpeg"
