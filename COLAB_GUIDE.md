# 🚀 Google Colab GPU Showcase Guide

If you are evaluating this project and want to see the pure power of the AI pipeline running on a dedicated NVIDIA GPU (without the complexity of setting up local servers), you can use Google Colab!

We have included a dedicated `colab_showcase.py` script that completely bypasses the React frontend and FastAPI layers. It directly interfaces with the core AI modules, utilizing CUDA to run Semantic Segmentation (Whisper) and Hybrid Tracking (MediaPipe + OpenCV) at blistering speeds.

## How to run the Showcase in Colab

### Option 1: The Git Clone Method (Recommended & Fastest)

If your code is pushed to GitHub, you do not need to zip or upload anything!

1. Go to [Google Colab](https://colab.research.google.com/) and create a **New Notebook**.
2. Click **Runtime** > **Change runtime type** > Select **T4 GPU**.
3. Create a code block, paste this, and press Play:

```bash
!git clone https://github.com/dbenahmed/video-to-clips
%cd video-to-clips
!pip install -r backend/requirements.txt
!python colab_showcase.py
```

### Option 2: The Zip Upload Method

If your repository is private or you prefer uploading manually, you must zip the files carefully to avoid uploading massive dependencies.

1. **CRITICAL**: Delete the `backend/venv/` and `backend/__pycache__/` folders on your computer first! (They are over 1GB. You can always recreate `venv` later by running `start_windows.bat`).
2. Zip the `backend/` folder and `colab_showcase.py` into `showcase.zip`.
3. In a new Colab Notebook (with T4 GPU enabled), upload `showcase.zip` to the file explorer on the left.
4. Run this code block:

```bash
!unzip -q showcase.zip
!pip install -r backend/requirements.txt
!python colab_showcase.py
```

### The Result

The script will automatically download a sample video, run the AI models, and trigger an FFmpeg pan-and-scan export on the best viral clip.

Once it finishes, open the `backend/storage/uploads/` folder in the Colab file explorer on the left.
You will find your final, beautifully cropped, perfectly synced `SHOWCASE_RESULT_...mp4` video! Right-click and download it to see the final product.

_(Note: You can easily open and edit `colab_showcase.py` before zipping it to test a different YouTube URL)._
