# NeuraSkill Classic - Deployment Guide

This package contains the **Classic Version** of the AI Serve Analyzer. It is designed for quick biomechanical analysis with a simplified setup.

## 📋 Prerequisites
- **Python 3.9+**
- **pip** (Python package manager)

## 🚀 Installation Steps

1. **Unzip the Package**:
   Extract the contents of `serve_analyzer_classic.zip` to a folder (e.g., `C:\NeuraSkill_Classic`).

2. **Install Dependencies**:
   - Open a terminal/command prompt in the directory.
   - Run:
     ```bash
     pip install -r requirements_serve.txt
     ```

3. **Launch the Application**:
   - Double-click `run_analyzer.bat`.
   - This will start a local web server and open the interface in your default browser at `http://localhost:8001`.

## 📂 Directory Structure
- `analyze_serve.py`: Core AI engine for pose estimation.
- `serve_api.py`: Backend API for processing videos.
- `index.html / app.js / style.css`: The web dashboard.
- `yolov8n-pose.pt`: The pre-trained YOLO model (CPU optimized).

## 🛠 Troubleshooting
- If the video doesn't load, ensure you are using a modern browser (Chrome or Edge recommended).
- Ensure Port 8001 is not being used by another application.
