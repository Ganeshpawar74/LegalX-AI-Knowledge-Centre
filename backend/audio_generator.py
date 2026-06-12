"""
Audio Summary generation.

Converts the AI-generated plain-language summary into speech using gTTS
(Google Text-to-Speech, free, no API key required). Audio files are cached
on disk under data/audio/<topic_id>.mp3 and regenerated only when the
underlying summary text changes.
"""
import hashlib
from pathlib import Path

from gtts import gTTS

from backend.config import AUDIO_DIR


def _text_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


def generate_audio(topic_id: str, summary_text: str, force: bool = False) -> str:
    """
    Generate (or reuse cached) MP3 audio for the given summary text.
    Returns the file path as a string.
    """
    if not summary_text.strip():
        return ""

    h = _text_hash(summary_text)
    filename = f"{topic_id}_{h}.mp3"
    path = AUDIO_DIR / filename

    if path.exists() and not force:
        return str(path)

    # Remove stale audio files for this topic
    for old_file in AUDIO_DIR.glob(f"{topic_id}_*.mp3"):
        if old_file.name != filename:
            try:
                old_file.unlink()
            except OSError:
                pass

    tts = gTTS(text=summary_text, lang="en", slow=False)
    tts.save(str(path))
    return str(path)
