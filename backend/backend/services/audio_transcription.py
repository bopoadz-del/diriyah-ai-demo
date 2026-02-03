"""
Audio transcription service for Diriyah AI.

This module implements a placeholder function to accept an uploaded
audio file, extract basic metadata and return a dummy transcript. It
lays the groundwork for integrating real speech-to-text engines such
as Whisper or cloud transcription services in future iterations.
"""

from pathlib import Path
from typing import Any, Dict
import wave


def _get_wav_metadata(file_path: Path) -> Dict[str, Any]:
    """Extract metadata from a WAV file if possible.

    Args:
        file_path: Path to the audio file.

    Returns:
        A dictionary with sample rate, channels and duration in
        seconds. If the file cannot be parsed as WAV, returns an
        empty dict.
    """
    try:
        with wave.open(str(file_path), 'rb') as wav_file:
            n_channels = wav_file.getnchannels()
            framerate = wav_file.getframerate()
            n_frames = wav_file.getnframes()
            duration = n_frames / float(framerate) if framerate else 0
            return {
                "sample_rate": framerate,
                "channels": n_channels,
                "duration_seconds": round(duration, 2),
            }
    except Exception:
        return {}


def transcribe_audio_file(file_path: Path) -> Dict[str, Any]:
    """
    Produce a dummy transcription for an uploaded audio file.

    Reads the file size and, if it has a `.wav` extension, extracts
    basic WAV metadata. A hardcoded transcript is returned to
    indicate that real transcription is not yet implemented.

    Args:
        file_path: Path to the stored audio file.

    Returns:
        A dictionary with filename, file size, optional metadata and
        a placeholder transcript.
    """
    if not file_path.exists():
        raise FileNotFoundError(f"Audio file {file_path} does not exist")

    file_size = file_path.stat().st_size
    metadata: Dict[str, Any] = {}
    if file_path.suffix.lower() == '.wav':
        metadata = _get_wav_metadata(file_path)

    transcript = (
        "[Transcription placeholder]\n"
        "This is a dummy transcript because the system does not yet "
        "implement real speech-to-text. In future iterations, this "
        "function will return the recognized words from the audio."
    )

    return {
        "filename": file_path.name,
        "file_size": file_size,
        "metadata": metadata,
        "transcript": transcript,
    }