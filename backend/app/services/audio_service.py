from __future__ import annotations

"""Audio service helpers.

The project defaults to a stub provider, but the helper functions here
determine which media file should be fed into STT/TTS pipelines. When
``settings.EXTRACT_WAV`` is enabled and the post-processed ``final.wav``
artifact exists, we prioritise it over ``final.webm`` for speech-to-text,
otherwise we fall back to the original WebM recording.
"""

from pathlib import Path
from typing import Optional, Protocol, runtime_checkable

from ..config import settings

GREETING_VOICE = "onyx"


@runtime_checkable
class AudioService(Protocol):
    """Интерфейс для работы с речью."""

    def transcribe(self, audio: bytes) -> str:
        """STT: аудио → текст."""
        ...

    def synthesize(self, text: str) -> bytes:
        """TTS: текст → аудио (например, WAV/MP3)."""
        ...


class StubAudioService(AudioService):
    """Заглушка: возвращает статичный результат для тестов."""

    _TRANSCRIBE_RESPONSE: str = "[stub] transcription unavailable"
    _SYNTH_RESPONSE: bytes = b""

    def transcribe(self, audio: bytes) -> str:  # noqa: ARG002
        return self._TRANSCRIBE_RESPONSE

    def synthesize(self, text: str) -> bytes:  # noqa: ARG002
        return self._SYNTH_RESPONSE


def get_audio_service() -> AudioService:
    """Фабрика провайдера. Заглушка — до появления реальной интеграции."""
    provider = (getattr(settings, "AUDIO_PROVIDER", None) or "stub").lower()
    if provider == "stub":
        return StubAudioService()
    raise NotImplementedError(f"Audio provider '{provider}' is not configured.")


def _media_root() -> Path:
    root_setting = getattr(settings, "MEDIA_UPLOAD_ROOT", "uploads") or "uploads"
    return Path(root_setting).expanduser().resolve()


def _session_media_dir(session_id: str, kind: str) -> Path:
    return _media_root() / session_id / kind


def _final_paths(session_id: str, kind: str) -> tuple[Path, Path]:
    base_dir = _session_media_dir(session_id, kind)
    return base_dir / "final.wav", base_dir / "final.webm"


def transcription_source_path(session_id: str, kind: str) -> Path:
    """Return the best available media file for STT for the given session.

    If ``settings.EXTRACT_WAV`` is truthy and ``final.wav`` exists, use it.
    Otherwise fall back to ``final.webm``. Raises ``FileNotFoundError`` when
    neither artifact is available.
    """

    wav_path, webm_path = _final_paths(session_id, kind)
    prefer_wav = bool(getattr(settings, "EXTRACT_WAV", 0)) and wav_path.exists()
    if prefer_wav:
        return wav_path
    if webm_path.exists():
        return webm_path
    raise FileNotFoundError(
        f"No final media found for session '{session_id}' kind '{kind}'."
    )


def transcribe_session_media(session_id: str, *, kind: str = "candidate") -> str:
    """Load the best media artifact for a session/kind and run STT on it."""

    media_path = transcription_source_path(session_id, kind)
    audio_bytes = media_path.read_bytes()
    service = get_audio_service()
    return service.transcribe(audio_bytes)


def greeting_voice(default: Optional[str] = None) -> str:
    """Return the voice used for greeting TTS endpoints."""

    return default or GREETING_VOICE
