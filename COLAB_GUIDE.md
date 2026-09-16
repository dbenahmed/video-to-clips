# 🚀 Google Colab GPU Showcase Guide

If you are evaluating this project and want to see the pure power of the AI pipeline running on a dedicated NVIDIA GPU (without the complexity of setting up local servers), you can use Google Colab!

We have included a dedicated `colab_showcase.py` script that completely bypasses the React frontend and FastAPI layers. It directly interfaces with the core AI modules, utilizing CUDA to run Semantic Segmentation (Whisper) and Hybrid Tracking (MediaPipe + OpenCV) at blistering speeds.

## How to generate a "Before & After" Showcase Video:

### Step 1: Zip the Project
1. In your local file explorer, select the `backend/` folder and the `colab_showcase.py` file.
2. Compress them into a single zip file (e.g., `showcase.zip`).

### Step 2: Prepare Google Colab
1. Go to [Google Colab](https://colab.research.google.com/) and create a **New Notebook**.
2. In the top menu, click **Runtime** > **Change runtime type**.
3. Under Hardware Accelerator, select **T4 GPU** and click Save.
4. On the left sidebar, click the **Folder icon** (Files), and upload your `showcase.zip` file.

### Step 3: Run the AI Pipeline
Create a single code block in the notebook, paste the following commands, and click the Play button:

```bash
# 1. Unzip the project files
!unzip -q showcase.zip

# 2. Install the exact backend dependencies (including GPU PyTorch)
!pip install -r backend/requirements.txt

# 3. Run the Showcase Pipeline!
!python colab_showcase.py
```

### The Result
The script will automatically download a sample video, run the AI models, and trigger an FFmpeg pan-and-scan export on the best viral clip.

Once it finishes, open the `backend/storage/uploads/` folder in the Colab file explorer on the left. 
You will find your final, beautifully cropped, perfectly synced `SHOWCASE_RESULT_...mp4` video! Right-click and download it to see the final product.

*(Note: You can easily open and edit `colab_showcase.py` before zipping it to test a different YouTube URL).*
