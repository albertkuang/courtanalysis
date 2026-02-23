"""
Serve Analyzer API - FastAPI server wrapping analyze_serve.py
Provides endpoints for video upload and serve analysis.
"""

import os
import shutil
import tempfile
import uuid
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from analyze_serve import ServeAnalyzer

# ── App Setup ─────────────────────────────────────────────────────────────────
app = FastAPI(title="Tennis Serve Analyzer API", version="1.0.0")

# CORS for localhost frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Output directory for analysis results
OUTPUT_DIR = Path(__file__).parent / "analysis_output"
OUTPUT_DIR.mkdir(exist_ok=True)

# Serve static files (snapshots)
app.mount("/output", StaticFiles(directory=str(OUTPUT_DIR)), name="output")

# ── Global Model Instance ─────────────────────────────────────────────────────
# Load model once at startup (nano model for CPU)
analyzer = None


@app.on_event("startup")
async def startup_event():
    global analyzer
    print("Loading YOLOv8-Pose model...")
    analyzer = ServeAnalyzer(model_size='n')
    print("Model ready.")


# ── API Endpoints ────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    """Friendly root endpoint to confirm server is up."""
    return {
        "message": "Tennis Serve Analyzer API is running!",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "analyze": "/analyze (POST)",
            "docs": "/docs"
        },
        "status": "ready" if analyzer is not None else "loading_model"
    }


@app.get("/health")
async def health_check():
    """Check if the server is running and model is loaded."""
    return {"status": "ok", "model_loaded": analyzer is not None}


@app.post("/analyze")
async def analyze_video(video: UploadFile = File(...)):
    """
    Upload a video file and get serve analysis results.
    Returns JSON with metrics, snapshots (as data URLs), and phase timeline.
    """
    if analyzer is None:
        raise HTTPException(status_code=503, detail="Model not loaded yet")

    # Validate file type
    allowed = {'.mp4', '.mov', '.avi', '.mkv', '.webm'}
    ext = Path(video.filename).suffix.lower()
    if ext not in allowed:
        raise HTTPException(status_code=400,
                            detail=f"Unsupported file type: {ext}. Allowed: {allowed}")

    # Save uploaded video to temp file
    job_id = str(uuid.uuid4())[:8]
    job_dir = OUTPUT_DIR / job_id
    job_dir.mkdir(exist_ok=True)

    video_path = job_dir / f"input{ext}"
    try:
        with open(video_path, "wb") as f:
            shutil.copyfileobj(video.file, f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save video: {e}")

    # Run analysis
    try:
        results = analyzer.analyze(str(video_path), save_snapshots=True,
                                   output_dir=str(job_dir))
        # Remove the large video file after analysis
        video_path.unlink(missing_ok=True)
        # Remove frame data from results (not JSON serializable)
        return JSONResponse(content=results)
    except Exception as e:
        # Cleanup on error
        shutil.rmtree(job_dir, ignore_errors=True)
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@app.post("/analyze-local")
async def analyze_local_video(path: str):
    """
    Analyze a video file that already exists on the server.
    Useful for testing without uploading.
    """
    if analyzer is None:
        raise HTTPException(status_code=503, detail="Model not loaded yet")

    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail=f"Video not found: {path}")

    job_id = str(uuid.uuid4())[:8]
    job_dir = OUTPUT_DIR / job_id
    job_dir.mkdir(exist_ok=True)

    try:
        results = analyzer.analyze(path, save_snapshots=True,
                                   output_dir=str(job_dir))
        return JSONResponse(content=results)
    except Exception as e:
        shutil.rmtree(job_dir, ignore_errors=True)
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002, reload=False)
