# 🛠️ Video-to-Clips AI

**Developer Setup Guide**

This guide is intended for developers, engineers, and technical evaluators who want to run the stack manually from the terminal.

If you are looking for the non-technical 1-click install, please refer to the `SETUP_GUIDE.md`.

## Prerequisites

- **Python 3.9+**
- **Node.js 18+**
- _(Optional)_ **FFmpeg** installed on your system PATH (The Python backend attempts to bundle its own binaries via `imageio-ffmpeg`, but having native FFmpeg installed is highly recommended).
- _(Optional)_ **CUDA Toolkit** installed for hardware-accelerated AI processing (PyTorch & OpenCV).

---

## 1. Backend Setup (FastAPI)

We highly recommend using a virtual environment (`venv`) to ensure that the heavy AI libraries (PyTorch, OpenCV, Whisper) do not conflict with your global Python packages.

Open a new terminal session and navigate to the project root:

```bash
# 1. Navigate to the backend directory
cd backend

# 2. Create an isolated virtual environment
python -m venv venv

# 3. Activate the virtual environment
# On Mac/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# 4. Install dependencies
# Note: This will download PyTorch, which is a large package.
pip install -r requirements.txt

# 5. Start the FastAPI development server
uvicorn main:app --reload --port 8000
# (Alternatively, if you installed fastapi[standard]: fastapi dev main.py)
```

_The backend API server is now running on `http://localhost:8000`. Keep this terminal open._

---

## 2. Frontend Setup (React/Vite)

Open a **second** terminal session and navigate to the project root:

```bash
# 1. Navigate to the frontend directory
cd frontend

# 2. Install Node dependencies
npm install

# 3. Start the Vite development server
npm run dev
```

_The frontend server is now running. Open your browser and navigate to the URL provided in the terminal (usually `http://localhost:5173`)._

---

## Architecture Overview

For technical evaluators reviewing this codebase:

- **`backend/app/routers/pipeline.py`**: The main entry point for the background AI tasks. It coordinates asynchronous execution of segmentation and tracking.
- **`backend/app/ai/tracking.py`**: A hybrid subject tracking algorithm using MediaPipe for face detection and OpenCV CSRT trackers as a fallback.
- **`backend/app/ai/segmentation.py`**: Uses OpenAI's Whisper model to transcribe audio and chunk semantic topics using a similarity drop threshold matrix.
- **`backend/app/services/export_service.py`**: Dynamically writes massive FFmpeg `filter_complex` graphs to slice, stitch, and mathematically align audio with pan-and-scan video cropping.
