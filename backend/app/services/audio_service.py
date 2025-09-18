from __future__ import annotations

"""
Аудио-сервис (интерфейс). Реализации добавим позже (TTS/STT через внешний API).

Сейчас — только заглушка, чтобы можно было зависеть от интерфейса.
Провайдер выбирается настройкой settings.AUDIO_PROVIDER, по умолчанию "stub".
"""
from typing import Protocol, runtime_checkable

from ..config import settings


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
