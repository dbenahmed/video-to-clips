# 🎬 Video-to-Clips AI Pipeline

An end-to-end, full-stack application that utilizes Artificial Intelligence to automatically transcribe, segment, and dynamically crop standard landscape videos into viral vertical (9:16) clips for TikTok, Shorts, and Reels.

## 🌟 Key Features
- **AI Semantic Segmentation**: Uses OpenAI's Whisper model to transcribe audio and chunk the video into logical, viral topics based on a mathematical similarity drop threshold.
- **Hybrid Subject Tracking**: Combines Google's MediaPipe (Deep Learning) with OpenCV (CSRT) to track humans flawlessly, ensuring the subject never leaves the vertical frame.
- **"Pan-and-Scan" Exporting**: Generates massive dynamic FFmpeg filter-graphs that mathematically align audio and stitch tracking sub-clips into a single, perfectly synced video.
- **Asynchronous Processing**: Enterprise-grade background task architecture prevents browser HTTP timeouts during heavy ML workloads.

## 🚀 Getting Started

We provide two distinct setup paths depending on your technical background:

### Option A: The "One-Click" Install (For non-developers/clients)
If you just want to test the software without typing terminal commands, please read the **[SETUP_GUIDE.md](./SETUP_GUIDE.md)**.
It includes a 1-click boot script for Windows (`start_windows.bat`) and Mac/Linux (`start_linux.sh`).

### Option B: The Developer Setup (For Engineers)
If you want to manually configure the Python virtual environments and run the servers from the terminal, please read the **[DEVELOPER_GUIDE.md](./DEVELOPER_GUIDE.md)**.

## 📚 Documentation & Architecture

To understand the complex engineering decisions, design patterns, and trade-offs that power this application, please read the **[ARCHITECTURE.md](./ARCHITECTURE.md)** file.

It details:
- Why Python was chosen over Node.js for the core backend.
- How we solved the "UI-to-Render Drift" problem using the Source of Truth pattern.
- How we bypassed severe performance bottlenecks using coordinate downsampling.
- The architectural choice between Time-based vs. Frame-based math.

## 💻 Tech Stack
- **Backend**: Python, FastAPI, OpenCV, MediaPipe, Whisper, FFmpeg (`imageio-ffmpeg`).
- **Frontend**: React (Vite), JavaScript, Vanilla CSS.
- **Communication**: REST APIs with asynchronous background polling.
