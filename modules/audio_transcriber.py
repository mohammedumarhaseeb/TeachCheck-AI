"""
Audio Transcriber Module for TeachCheck AI
Transcribes speech using Faster-Whisper (tiny model, CPU, INT8).
Provides timestamped segments and fallback support for manual transcripts.
"""

import os
import re
from faster_whisper import WhisperModel


class TranscriptionError(Exception):
    """Custom exception for audio transcription failures."""
    pass


# Global cache for whisper model instance
_MODEL_CACHE = {}


def get_whisper_model(model_size: str = "tiny") -> WhisperModel:
    """
    Returns a cached Faster-Whisper model on CPU with int8 quantization.
    """
    if model_size not in _MODEL_CACHE:
        try:
            _MODEL_CACHE[model_size] = WhisperModel(
                model_size,
                device="cpu",
                compute_type="int8",
                cpu_threads=4
            )
        except Exception as e:
            raise TranscriptionError(
                f"Failed to load Faster-Whisper model '{model_size}': {str(e)}. "
                "You can use the Manual Transcript fallback below."
            )
    return _MODEL_CACHE[model_size]


def format_seconds_to_timestamp(seconds: float) -> str:
    """Converts seconds into MM:SS format."""
    total_sec = max(0, int(seconds))
    mins = total_sec // 60
    secs = total_sec % 60
    return f"{mins:02d}:{secs:02d}"


def transcribe_audio(
    audio_path: str,
    model_size: str = "tiny"
) -> list[dict]:
    """
    Transcribes audio using Faster-Whisper.
    Returns a list of timestamped segment dicts:
    [
        {
            "segment_id": 1,
            "start": 0.0,
            "end": 4.5,
            "timestamp": "00:00 - 00:04",
            "text": "Hello world and welcome to this lecture."
        },
        ...
    ]
    """
    if not os.path.exists(audio_path):
        raise TranscriptionError(f"Audio file does not exist: {audio_path}")

    model = get_whisper_model(model_size)

    try:
        segments_gen, info = model.transcribe(
            audio_path,
            beam_size=5,
            word_timestamps=False,
            vad_filter=True  # Filter out silences
        )

        segments = []
        for idx, segment in enumerate(segments_gen):
            text_cleaned = segment.text.strip()
            if not text_cleaned:
                continue

            start_str = format_seconds_to_timestamp(segment.start)
            end_str = format_seconds_to_timestamp(segment.end)
            segments.append({
                "segment_id": idx + 1,
                "start": round(segment.start, 2),
                "end": round(segment.end, 2),
                "timestamp": f"{start_str} - {end_str}",
                "text": text_cleaned
            })

        if not segments:
            # If no speech was detected, provide a clear warning
            raise TranscriptionError(
                "No speech was detected in the audio track. "
                "Please provide a manual transcript or ensure the video has clear speech."
            )

        return segments

    except Exception as e:
        if isinstance(e, TranscriptionError):
            raise
        raise TranscriptionError(
            f"Transcription failed: {str(e)}. "
            "Please use the manual transcript input fallback to proceed."
        )


def format_transcript_as_text(segments: list[dict]) -> str:
    """
    Formats list of segments into a readable multiline timestamped string.
    """
    lines = []
    for s in segments:
        ts = s.get("timestamp", f"{format_seconds_to_timestamp(s.get('start', 0))} - {format_seconds_to_timestamp(s.get('end', 0))}")
        lines.append(f"[{ts}] {s.get('text', '')}")
    return "\n".join(lines)


def parse_manual_transcript(raw_text: str) -> list[dict]:
    """
    Parses a manually entered transcript into structured segments.
    Supports either timestamped lines '[00:00 - 00:05] Text' or plain text lines.
    """
    if not raw_text or not raw_text.strip():
        raise TranscriptionError("Manual transcript cannot be empty.")

    lines = [line.strip() for line in raw_text.strip().split("\n") if line.strip()]
    segments = []

    # Pattern: [MM:SS - MM:SS] text or [MM:SS] text
    ts_range_pattern = re.compile(r"^\[?(\d{1,2}:\d{2})\s*-\s*(\d{1,2}:\d{2})\]?\s*(.*)$")
    ts_single_pattern = re.compile(r"^\[?(\d{1,2}:\d{2})\]?\s*(.*)$")

    default_step = 5.0

    for idx, line in enumerate(lines):
        m_range = ts_range_pattern.match(line)
        if m_range:
            start_str, end_str, text = m_range.groups()
            segments.append({
                "segment_id": idx + 1,
                "timestamp": f"{start_str} - {end_str}",
                "text": text.strip()
            })
            continue

        m_single = ts_single_pattern.match(line)
        if m_single:
            start_str, text = m_single.groups()
            segments.append({
                "segment_id": idx + 1,
                "timestamp": start_str,
                "text": text.strip()
            })
            continue

        # If plain line with no timestamp, estimate timestamp
        start_sec = idx * default_step
        end_sec = (idx + 1) * default_step
        segments.append({
            "segment_id": idx + 1,
            "start": start_sec,
            "end": end_sec,
            "timestamp": f"{format_seconds_to_timestamp(start_sec)} - {format_seconds_to_timestamp(end_sec)}",
            "text": line
        })

    return segments
