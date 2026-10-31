"""
Video Processor Module for TeachCheck AI
Handles video validation, frame extraction (approx 1 frame every 5s, max 6 frames),
and audio extraction using bundled FFmpeg via imageio-ffmpeg.
"""

import os
import subprocess
import cv2
import imageio_ffmpeg


class VideoProcessingError(Exception):
    """Custom exception for video processing failures."""
    pass


def validate_video_file(file_path: str, max_size_mb: int = 200) -> dict:
    """
    Validates that the file exists, has a supported video extension,
    and does not exceed the allowed size limit.
    """
    if not os.path.exists(file_path):
        raise VideoProcessingError(f"Video file not found: {file_path}")

    valid_extensions = [".mp4", ".mov", ".avi"]
    _, ext = os.path.splitext(file_path)
    if ext.lower() not in valid_extensions:
        raise VideoProcessingError(
            f"Unsupported video format '{ext}'. Supported formats: {', '.join(valid_extensions)}"
        )

    file_size_bytes = os.path.getsize(file_path)
    file_size_mb = file_size_bytes / (1024 * 1024)
    if file_size_mb > max_size_mb:
        raise VideoProcessingError(
            f"File size ({file_size_mb:.1f} MB) exceeds maximum limit of {max_size_mb} MB."
        )

    return {
        "file_path": file_path,
        "extension": ext.lower(),
        "size_mb": round(file_size_mb, 2)
    }


def get_video_metadata(video_path: str) -> dict:
    """
    Retrieves video metadata including duration, fps, resolution, and total frames.
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise VideoProcessingError(f"OpenCV failed to open video file: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap.release()

    if fps <= 0 or total_frames <= 0:
        duration_sec = 0.0
    else:
        duration_sec = total_frames / fps

    return {
        "fps": fps,
        "total_frames": total_frames,
        "width": width,
        "height": height,
        "duration_sec": duration_sec,
        "duration_str": f"{int(duration_sec // 60):02d}:{int(duration_sec % 60):02d}"
    }


def extract_representative_frames(
    video_path: str,
    output_dir: str,
    interval_sec: float = 5.0,
    max_frames: int = 6
) -> list[dict]:
    """
    Extracts one frame approximately every 5 seconds, up to a maximum of 6 frames.
    Stores timestamps for each frame.
    Returns list of dicts with frame index, timestamp, and saved file path.
    """
    os.makedirs(output_dir, exist_ok=True)
    meta = get_video_metadata(video_path)
    duration = meta["duration_sec"]

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise VideoProcessingError(f"Could not open video file: {video_path}")

    # Determine frame timestamps
    # Target 1 frame every interval_sec, capped at max_frames
    timestamps = []
    current_time = 0.0

    if duration <= 0:
        timestamps = [0.0]
    else:
        while current_time < duration and len(timestamps) < max_frames:
            timestamps.append(current_time)
            current_time += interval_sec

        # If video is short, ensure we have at least one frame
        if not timestamps:
            timestamps = [0.0]

    extracted_frames = []

    try:
        for idx, ts in enumerate(timestamps):
            cap.set(cv2.CAP_PROP_POS_MSEC, ts * 1000.0)
            success, frame = cap.read()
            if not success:
                # Try seeking to beginning if first frame failed
                if idx == 0:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    success, frame = cap.read()
                if not success:
                    continue

            frame_filename = f"frame_{idx+1:02d}_{int(ts):03d}s.jpg"
            frame_filepath = os.path.join(output_dir, frame_filename)
            cv2.imwrite(frame_filepath, frame, [int(cv2.IMWRITE_JPEG_QUALITY), 90])

            extracted_frames.append({
                "frame_index": idx + 1,
                "timestamp_sec": round(ts, 1),
                "timestamp_str": f"{int(ts // 60):02d}:{int(ts % 60):02d}",
                "file_path": frame_filepath,
                "filename": frame_filename,
                "width": frame.shape[1],
                "height": frame.shape[0]
            })
    finally:
        cap.release()

    if not extracted_frames:
        raise VideoProcessingError("No frames could be extracted from video.")

    return extracted_frames


def extract_audio_from_video(video_path: str, output_audio_path: str = None) -> str:
    """
    Extracts the audio track from the video into a 16kHz mono WAV file
    using bundled FFmpeg from imageio-ffmpeg.
    """
    if output_audio_path is None:
        base_dir = os.path.dirname(video_path)
        base_name = os.path.splitext(os.path.basename(video_path))[0]
        output_audio_path = os.path.join(base_dir, f"{base_name}_audio.wav")

    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    if not ffmpeg_exe or not os.path.exists(ffmpeg_exe):
        raise VideoProcessingError("FFmpeg executable could not be located via imageio-ffmpeg.")

    cmd = [
        ffmpeg_exe,
        "-y",               # Overwrite existing
        "-i", video_path,   # Input file
        "-vn",              # Disable video recording
        "-acodec", "pcm_s16le", # Uncompressed 16-bit PCM
        "-ar", "16000",     # 16 kHz sample rate (optimal for Whisper)
        "-ac", "1",         # Mono channel
        output_audio_path
    ]

    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode != 0:
            raise VideoProcessingError(
                f"FFmpeg audio extraction failed (code {result.returncode}): {result.stderr[-500:]}"
            )
    except Exception as e:
        if isinstance(e, VideoProcessingError):
            raise
        raise VideoProcessingError(f"Failed to execute audio extraction: {str(e)}")

    if not os.path.exists(output_audio_path) or os.path.getsize(output_audio_path) == 0:
        raise VideoProcessingError("Extracted audio file is empty or missing. Video may have no audio track.")

    return output_audio_path
