"""
TeachCheck AI — Python Video & Audio Processing Microservice
FastAPI service providing FFmpeg audio extraction, Faster-Whisper transcription,
and OpenCV representative frame extraction. Protected via server-to-server secret.
"""

import os
import sys
import time
import shutil
import base64
from typing import Optional
from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, Header, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# Load environment
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(BASE_DIR)
load_dotenv(os.path.join(BASE_DIR, ".env"))

# Add parent directory to sys.path to reuse existing modules
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

from modules.video_processor import (
    validate_video_file,
    get_video_metadata,
    extract_representative_frames,
    extract_audio_from_video,
    VideoProcessingError
)
from modules.audio_transcriber import (
    transcribe_audio,
    TranscriptionError
)

INTERNAL_AUTH_SECRET = os.getenv("INTERNAL_AUTH_SECRET", "tc_internal_secret_change_in_production_12345")
MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "200"))
TEMP_DIR = os.path.join(BASE_DIR, "temp")
os.makedirs(TEMP_DIR, exist_ok=True)

app = FastAPI(
    title="TeachCheck AI Processor",
    description="Internal Python multimedia extraction microservice for TeachCheck AI",
    version="1.0.0"
)

# CORS: Only allow localhost or configured internal origins
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


def verify_internal_secret(x_internal_secret: Optional[str] = Header(None)):
    """Validates the internal server-to-server authentication secret."""
    if not x_internal_secret or x_internal_secret != INTERNAL_AUTH_SECRET:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized: Invalid or missing X-Internal-Secret header"
        )


@app.get("/health")
def health_check():
    """Health status endpoint."""
    return {
        "status": "healthy",
        "service": "teachcheck-python-processor",
        "timestamp": time.time(),
        "max_upload_size_mb": MAX_FILE_SIZE_MB
    }


@app.post("/api/v1/process-video")
async def process_video(
    video: UploadFile = File(...),
    x_internal_secret: Optional[str] = Header(None)
):
    """
    Accepts an educational video file, extracts representative frames,
    extracts audio, transcribes speech, and returns structured evidence.
    """
    verify_internal_secret(x_internal_secret)

    # 1. Validate file format
    valid_exts = [".mp4", ".mov", ".avi"]
    filename = video.filename or "uploaded_video.mp4"
    _, ext = os.path.splitext(filename)
    if ext.lower() not in valid_exts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported format '{ext}'. Allowed: {', '.join(valid_exts)}"
        )

    # 2. Setup isolated run directory
    run_id = f"proc_{int(time.time())}_{os.getpid()}"
    run_dir = os.path.join(TEMP_DIR, run_id)
    frames_dir = os.path.join(run_dir, "frames")
    os.makedirs(frames_dir, exist_ok=True)

    saved_video_path = os.path.join(run_dir, f"input{ext.lower()}")
    audio_path = os.path.join(run_dir, "extracted_audio.wav")

    try:
        # Save video to disk while enforcing max file size
        total_bytes = 0
        max_bytes = MAX_FILE_SIZE_MB * 1024 * 1024
        with open(saved_video_path, "wb") as out_f:
            while chunk := await video.read(1024 * 1024):  # 1MB chunks
                total_bytes += len(chunk)
                if total_bytes > max_bytes:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"File exceeds maximum upload size of {MAX_FILE_SIZE_MB} MB"
                    )
                out_f.write(chunk)

        # 3. Extract video metadata
        meta = get_video_metadata(saved_video_path)

        # 4. Extract representative frames (up to 6)
        raw_frames = extract_representative_frames(
            video_path=saved_video_path,
            output_dir=frames_dir,
            interval_sec=5.0,
            max_frames=6
        )

        # Base64 encode frames for safe network payload
        encoded_frames = []
        for rf in raw_frames:
            with open(rf["file_path"], "rb") as img_f:
                b64_content = base64.b64encode(img_f.read()).decode("utf-8")
            encoded_frames.append({
                "frame_index": rf["frame_index"],
                "timestamp_sec": rf["timestamp_sec"],
                "timestamp_str": rf["timestamp_str"],
                "filename": rf["filename"],
                "width": rf["width"],
                "height": rf["height"],
                "mime_type": "image/jpeg",
                "image_base64": b64_content
            })

        # 5. Extract audio and transcribe with Faster-Whisper
        segments = []
        try:
            extract_audio_from_video(saved_video_path, audio_path)
            segments = transcribe_audio(audio_path, model_size="tiny")
        except Exception as audio_err:
            # Non-crashing audio fallback
            segments = [{
                "segment_id": 1,
                "timestamp": "00:00 - 00:30",
                "text": "Audio unavailable or silent. Manual transcript can be provided."
            }]

        return {
            "success": True,
            "filename": filename,
            "video_metadata": meta,
            "transcript_segments": segments,
            "frames": encoded_frames,
            "total_frames": len(encoded_frames),
            "total_segments": len(segments)
        }

    except HTTPException:
        raise
    except VideoProcessingError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Multimedia processing error: {str(e)}"
        )
    finally:
        # Immediate cleanup of temporary processing folder to protect disk space
        if os.path.exists(run_dir):
            shutil.rmtree(run_dir, ignore_errors=True)


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    host = os.getenv("HOST", "127.0.0.1")
    uvicorn.run("main:app", host=host, port=port, reload=False)

