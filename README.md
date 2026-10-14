# 🎬 Video Chunker (30s Scene Splitter)

A Python application that allows you to upload any video file, splits it into 30-second clips (or any custom duration), and automatically saves them as `scene 1.mp4`, `scene 2.mp4`, etc.

## 🚀 Features

- **Web Upload Interface**: Intuitive, modern web dashboard (Streamlit) for dragging & dropping video files (`.mp4`, `.mov`, `.mkv`, `.avi`, `.webm`).
- **Automatic 30-Second Chunking**: Automatically slices the video into 30s clips sequentially.
- **Sequential Scene Naming**: Names output clips as `scene 1.mp4`, `scene 2.mp4`, `scene 3.mp4`, ...
- **Lossless & Lightning Fast**: Uses stream copy (`-c copy`) for zero quality loss in milliseconds. Also provides frame-accurate re-encoding mode when needed.
- **Interactive Scene Preview & Gallery**: Watch each scene directly in the browser and download individual scenes or all scenes in a single `.zip` file.
- **Audio Stripping & Separate Audio Export**:
  - **Strip & Save Audio**: Option to extract each chunk's audio into separate files (`scene 1 audio.mp3`, `scene 2 audio.mp3`, etc.).
  - **Silent Video Mode**: Option to mute/strip audio from the video clips directly.
- **CLI Support**: Includes a command-line script (`cli.py`) for headless / terminal usage.
- **Self-Contained FFmpeg**: Powered by `imageio-ffmpeg`, which includes the FFmpeg binary automatically for macOS without needing manual system installs.

---

## 🛠️ Quick Start

### 1. Activate the Virtual Environment

```bash
source .venv/bin/activate
```

*(If setting up on a new machine, install dependencies with: `pip install -r requirements.txt`)*

### 2. Launch the Web Application

```bash
./.venv/bin/streamlit run app.py
```
Or with activated virtual environment:
```bash
streamlit run app.py
```

Open `http://localhost:8501` in your browser, upload your video, and click **🚀 Start Splitting Video**!

---

## 💻 Command Line Interface (CLI)

If you prefer running from the command line:

```bash
# Basic usage (splits into 30s chunks in ./output_scenes)
./.venv/bin/python cli.py path/to/video.mp4

# Custom duration (e.g. 15s) and custom output folder
./.venv/bin/python cli.py path/to/video.mp4 --chunk-duration 15 --output-dir my_scenes

# Frame-accurate re-encoding
./.venv/bin/python cli.py path/to/video.mp4 --accurate

# Extract audio tracks separately (scene 1 audio.mp3, etc.)
./.venv/bin/python cli.py path/to/video.mp4 --extract-audio

# Mute / strip audio completely from output videos
./.venv/bin/python cli.py path/to/video.mp4 --strip-audio
```

---

## 📁 Project Structure

```
VideoChunker/
├── .venv/               # Python Virtual Environment
├── app.py               # Streamlit Web Application
├── chunker.py           # Core Video Chunking & Metadata Engine
├── cli.py               # Command-Line Interface
├── requirements.txt     # Dependencies (streamlit, imageio-ffmpeg)
└── README.md            # Documentation
```

Option 1:

./.venv/bin/streamlit run app.py

http://localhost:8501


Option 2: Command Line (CLI)

# Basic usage (splits into 30s clips saved in output_scenes/):
./.venv/bin/python cli.py path/to/your_video.mp4

# Frame-accurate cutting:
./.venv/bin/python cli.py path/to/your_video.mp4 --accurate

# Custom duration and destination folder:
./.venv/bin/python cli.py path/to/your_video.mp4 --chunk-duration 30 --output-dir my_scenes
