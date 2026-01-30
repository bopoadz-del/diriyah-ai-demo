import importlib
import os
import tempfile

_openai_client = None
_openai_available = True


def _get_openai_client():
    global _openai_client, _openai_available
    if _openai_client is not None or not _openai_available:
        return _openai_client
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        _openai_available = False
        return None
    try:
        openai_module = importlib.import_module("openai")
        OpenAI = getattr(openai_module, "OpenAI", None)
        if OpenAI is None:
            _openai_available = False
            return None
        _openai_client = OpenAI(api_key=api_key)
    except Exception:
        _openai_available = False
        return None
    return _openai_client

def transcribe_audio(file) -> str:
    client = _get_openai_client()
    if client is None:
        return "Transcription unavailable: OpenAI client not configured"
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
        tmp.write(file.read()); tmp.flush()
        audio_path = tmp.name
    with open(audio_path, "rb") as audio_file:
        transcript = client.audio.transcriptions.create(model="whisper-1", file=audio_file)
    return transcript.text if hasattr(transcript, "text") else transcript["text"]
