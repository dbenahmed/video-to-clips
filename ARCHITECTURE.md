# 🏛️ Architecture & Engineering Decisions

This document details the core architectural decisions, design patterns, and engineering trade-offs made while building the Video-to-Clips AI pipeline.

---

## 1. Why We Chose Python (A brief note)
While Node.js is excellent for handling web requests and standard file I/O, we chose Python for the backend because it is the undisputed industry standard for Computer Vision and AI. Building the core feature of this app—dynamic subject tracking and frame-by-frame analysis—would require fragile workarounds and complex C++ bindings in Node.js. Python, with its native support for OpenCV, MediaPipe, and seamless FFmpeg integration, allows us to build the 'smart crop' feature rapidly, reliably, and with highly readable code.

---

## 2. Core AI Pipeline Design Patterns

### The Global Tracker
Scans the entire video at a low framerate. It maps out exactly where the primary subject is at any given second.
**Output Example**: `[ {"time_sec": 1.0, "x": 450, "y": 500}, {"time_sec": 2.0, "x": 460, "y": 500} ]`

### The Segmenter
Analyzes the video (via AI transcripts and audio) to find interesting viral segments. It returns a simple list of proposed clip boundaries based on a similarity drop threshold.
**Output Example**: `[ { "clip_id": 1, "start": 15.0, "end": 45.0 } ]`

### The Performance Bottleneck (Downsampling)
Scanning every single frame of a 10-minute, 60fps video for a face means analyzing 36,000 frames. This could take minutes.
- **Solution**: Downsample the tracking. Instead of scanning 60 frames per second, the backend scans 1 or 2 frames per second (2 fps). Since humans don't teleport, the frontend can smoothly animate (interpolate) the crop box between those points. This reduces processing time by **96%**.

---

## 3. The Hybrid Tracking System (MediaPipe + OpenCV)
To track subjects accurately without destroying CPU performance, we implemented a hybrid approach:

### MediaPipe (By Google)
MediaPipe is a modern, deep-learning framework designed specifically to track human anatomy in real-time (the exact technology used in Google Meet).
- **How it works**: Uses pre-trained AI neural networks (like "BlazeFace") to actively understand anatomy ("this is a nose").
- **Pros**: Incredible accuracy (rarely loses a face) and blazing fast (optimized for smartphones). Zero training required.
- **Cons**: Strictly trained for human anatomy. It cannot track objects like sports cars or animals.

### OpenCV (CSRT Tracker)
OpenCV is the grandfather of Computer Vision. Trackers like CSRT are "pixel matchers" that track clusters of colors/shapes.
- **How it works**: You give OpenCV a box in Frame 1. In Frame 2, it looks for the pixel cluster that most closely matches it.
- **Pros**: Tracks anything (faces, dogs, cars). Completely general-purpose.
- **Cons**: Outdated built-in face detection (Haar Cascades from 2001). Easily confused if a subject walks behind a pole or someone wearing similar colors crosses their path.

**The Hybrid Solution**: We use MediaPipe as the primary facial detector. If MediaPipe loses the face, OpenCV CSRT (the gold standard for balancing accuracy and CPU speed) acts as a lightning-fast fallback to bridge the gap.

---

## 4. Advanced Challenges & Optimizations

### The "Podcast" Problem (Multiple Subjects)
What if there are two people on screen (e.g., an interviewer and a guest)? The tracker might jump rapidly back and forth between them.
- **Solution**: For V1, we track the largest face. A future optimization is to group subjects (Subject 1, Subject 2) and actively switch the crop based on Active Speaker Detection.

### B-Roll Fallback (No Subject on Screen)
A clip cuts to a shot of a video game or a landscape where there are no faces.
- **Solution**: The tracking array utilizes a fallback state. If no face is detected from time `t1` to `t2`, the crop data naturally defaults to `center_x: 50%, center_y: 50%` to maintain a centered aspect ratio.

### "UI-to-Render Drift" (The Source of Truth Pattern)
A classic problem in video engineering is when the frontend preview differs from the final exported video due to mathematical boundary clamping.
- **Solution (Recommended)**: The Python backend acts as the single Source of Truth. It pre-calculates the exact top-left `crop_x` and `crop_y` coordinates, applies clamping (so the crop doesn't float off the video edge), and saves these to `recipe.json`. 
- **Result**: The React frontend blindly draws the box at those exact pixels, and FFmpeg blindly cuts at those exact pixels. 100% identical results.

### Time-Based vs Frame-Based Exporting
- **Decision**: For this MVP, we explicitly chose a Time-Based Architecture (seconds). Moving to a pure Frame-Based architecture requires rewriting the AI layer, React frontend (since HTML5 `<video>` scrubs in seconds), and FFmpeg logic. It is overkill for a TikTok clip generator and seconds-based math is exponentially more scalable for V1.

---

## 5. Architectural Fixes

### Eliminating "Connection Lost" Timeouts
Browsers naturally drop idle HTTP connections after 2-5 minutes. Because the initial AI process was synchronous, the 10-minute AI crunch caused browsers to give up and drop the request. Clicking the button again spawned multiple pipelines, crashing the memory.
- **The Fix (Background Tasks)**: The `pipeline.py` router was refactored to utilize FastAPI Background Tasks. Now, the frontend hits `/process` and the backend instantly spins up a secure background worker, returning a 200 Success in milliseconds. The frontend uses a lightweight polling loop (`setInterval`) on `/progress` to drive the UI loading bar.

---

## 6. Codebase File Architecture

Below is the mapping of our separation of concerns across the backend services and routers:

### 📡 Routers (API Layer)
- **`routers/pipeline.py`**: The main entry point for the background AI tasks. Coordinates the asynchronous execution of semantic segmentation and hybrid tracking.
- **`routers/export.py`**: Handles final rendering requests, spinning off FFmpeg threads to physically cut the video.
- **`routers/video.py`**: Handles ingestion routes, bridging the gap between local file uploads and YouTube downloads.

### 🧠 Services (Business Logic)
- **`services/tracking.py`**: Contains the complex Hybrid Tracking logic (MediaPipe bounding boxes + OpenCV CSRT fallback algorithms).
- **`services/segmentation.py`**: Houses the OpenAI Whisper transcription logic and semantic topic chunking logic.
- **`services/export_service.py`**: The FFmpeg engine. Dynamically generates massive `filter_complex` graphs to slice, stitch, and mathematically align audio with pan-and-scan video cropping.
- **`services/upload_service.py`**: Standardizes file saving and chunking protocols for raw `multipart/form-data` uploads.
- **`services/youtube_service.py`**: Wraps `yt-dlp` to rapidly pull external video buffers directly into local storage.
