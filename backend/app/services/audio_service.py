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

    def synthesize(self, text: str) -> bytes:
        """TTS: текст → аудио (например, WAV/MP3)."""


class StubAudioService(AudioService):
    """Заглушка: поднимает NotImplementedError, чтобы не забыть внедрить позже."""

    def transcribe(self, audio: bytes) -> str:  # noqa: ARG002
        raise NotImplementedError("AudioService: распознавание речи не настроено (provider=stub).")

    def synthesize(self, text: str) -> bytes:  # noqa: ARG002
        raise NotImplementedError("AudioService: синтез речи не настроен (provider=stub).")


def get_audio_service() -> AudioService:
    """
    Фабрика провайдера. Когда подключим реальный API, добавим сюда ветку.
    """
    provider = (getattr(settings, "AUDIO_PROVIDER", None) or "stub").lower()
    # пример будущей ветки:
    # if provider == "gcp":
    #     return GoogleCloudAudioService(...)
    return StubAudioService()
