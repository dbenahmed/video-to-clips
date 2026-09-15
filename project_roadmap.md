# 🗺️ Video-to-Clips: Project Roadmap

This is our step-by-step plan for building the application. We will tackle these milestones one by one.

## 🏗️ Milestone 1: Infrastructure & Scaffolding
*Goal: Get the foundation set up so the frontend and backend can talk to each other.*
* **Backend:** Initialize the Python FastAPI project structure.
* **Frontend:** Initialize the React (Vite) project.
* **Connectivity:** Set up CORS on the backend and verify that the React app can successfully make a dummy API call to FastAPI.

## 📥 Milestone 2: Video Ingestion
*Goal: Allow the user to get video into the system.*
* **Backend:** Create an endpoint to handle direct video file uploads (saving to a temporary folder).
* **Backend:** Create an endpoint using `yt-dlp` to download a video given a YouTube URL.
* **Frontend:** Build a premium, user-friendly UI with a drag-and-drop zone and a URL input field.

## 🧠 Milestone 3: The "Brain" (Analysis & Tracking)
*Goal: Analyze the video to find clips and track the subject.*
* **Backend (Segmentation):** Implement the modular segmentation logic (Algorithm TBD: Audio silence, scene detection, or fixed chunks) to generate initial start/end times.
* **Backend (Tracking):** Use OpenCV/MediaPipe to scan the video and calculate the dynamic X/Y coordinates needed to keep the subject centered in a 9:16 vertical frame.
* **API:** Send this "recipe" (list of clips with timestamps and crop coordinates) to the frontend.

## 🎛️ Milestone 4: Interactive Video Timeline (UI/UX)
*Goal: Let the user review and edit the AI's suggestions.*
* **Frontend:** Build a custom video player.
* **Frontend (Timeline):** Create an interactive slider where users can see the auto-generated clips, drag the edges to adjust times, or delete clips they don't want.
* **Frontend (Preview):** Draw a visual 9:16 bounding box over the video player so the user can preview exactly what the final cropped video will look like.

## ⚙️ Milestone 5: The "Brawn" (Cropping & Export)
*Goal: Do the heavy lifting to create the final video files.*
* **Backend:** Create the final export endpoint that receives the user's adjusted timestamps.
* **Backend (FFmpeg):** Write the FFmpeg commands to physically slice the high-res video and apply the dynamic 9:16 crop based on our tracking data.
* **Frontend:** Show a progress indicator and provide download buttons for the final MP4 files.

## ✨ Milestone 6: Polish & Delivery
*Goal: Make it robust and ready for a non-developer to use.*
* **Backend:** Implement automatic cleanup of temporary files to save disk space.
* **Frontend:** Finalize the UI aesthetics (colors, micro-animations, error states) to ensure a "WOW" factor.
* **Documentation:** Write clear, step-by-step local setup instructions in a `README.md`.
