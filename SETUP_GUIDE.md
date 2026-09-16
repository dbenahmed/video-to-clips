# 🎬 Video-to-Clips AI
**One-Click Setup Guide**

Welcome! This application runs entirely on your local machine to process and automatically edit videos into vertical clips using Artificial Intelligence. 

To make this as easy as possible, we have included a **One-Click Boot Script**. You do not need to be a developer or touch a terminal.

---

## Step 1: Install Prerequisites
Before you click the boot script, you need two standard programs installed on your computer. If you already have them, you can skip to Step 2.

### 1. Python (Required for AI processing)
- Download here: [https://www.python.org/downloads/](https://www.python.org/downloads/)
- ⚠️ **IMPORTANT FOR WINDOWS USERS:** During installation, you MUST check the box at the bottom that says **"Add Python to PATH"** before you click Install.

### 2. Node.js (Required for the User Interface)
- Download here: [https://nodejs.org/](https://nodejs.org/) (Download the "LTS" version).
- Install it normally with the default settings.

---

## Step 2: Start the Application

### If you are on Windows:
1. Double-click the `start_windows.bat` file in this folder.
2. A black command window will appear. It will automatically download and install everything it needs (this might take a few minutes the very first time you run it).
3. Two more windows will open (one for the backend AI engine, one for the frontend interface). **Do not close them!** They are keeping your app running.
4. Your web browser will automatically open to `http://localhost:5173`. If it doesn't, open Google Chrome and type that URL manually.

### If you are on Mac:
1. Double-click the `start_mac.command` file in this folder.
2. A terminal window will open and automatically install all required packages.
3. Your browser will automatically open to `http://localhost:5173` once it finishes.
4. To stop the application, simply close the terminal window.

*(Note for Mac users: If it says "permission denied" when double-clicking, open your Mac Terminal, drag the `start_mac.command` file into it, type `chmod +x ` before the file path, and press Enter to allow it to run).*

### If you are on Linux:
1. Open your terminal in this directory.
2. Run `chmod +x start_linux.sh` to make the script executable.
3. Run `./start_linux.sh`
4. It will install everything and open your browser. To stop the servers, just close the terminal.

---

## Step 3: Enjoy!
You are now running a local, AI-powered video editing pipeline.
- Drop a video file or paste a YouTube link.
- Let the AI track faces and segment topics.
- Adjust settings like Target FPS or Clip Length if needed.
- Export your viral clips directly to your computer!
