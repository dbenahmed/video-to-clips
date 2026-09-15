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

## 🧠 Milestone 3: The "Brain" (Decoupled Global Tracking & Segmentation)
*Goal: Analyze the video to independently generate clip boundaries and a global tracking map.*
* **Backend (Global Tracker):** Implement a fast, downsampled face tracker (e.g., MediaPipe at 2 fps) across the *entire* video, compressing the results into independent Time Ranges (`[start, end, x, y]`).
* **Backend (Segmentation):** Implement a modular segmentation logic (mocked randomly for now) to generate proposed clip boundaries (start/end).
* **API (The Recipe):** Deliver the `global_tracking` map and the `clips` arrays independently so the frontend has full timeline control.

## 🎛️ Milestone 4: Interactive Video Timeline (UI/UX)
*Goal: Let the user review and freely edit the AI's suggestions without breaking tracking.*
* **Frontend (Timeline & Editor):** Create an interactive slider where users can drag the edges of auto-generated clips to extend/shorten them seamlessly.
* **Frontend (Zero-CPU Preview):** Build a custom video player that plays the horizontal video while applying a CSS `transform` overlay to a 9:16 bounding box. The box automatically reads the `global_tracking` map to pan smoothly as the video plays.

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
