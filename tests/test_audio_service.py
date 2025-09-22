from pathlib import Path

import pytest

from backend.app.services import audio_service


class RecorderStub(audio_service.StubAudioService):
    def __init__(self):
        self.received: bytes | None = None

    def transcribe(self, audio: bytes) -> str:  # type: ignore[override]
        self.received = audio
        return "transcribed"


def test_transcription_source_prefers_wav(tmp_path, monkeypatch):
    monkeypatch.setattr(audio_service.settings, "MEDIA_UPLOAD_ROOT", str(tmp_path))
    monkeypatch.setattr(audio_service.settings, "EXTRACT_WAV", 1)

    session_dir = tmp_path / "sess" / "audio"
    session_dir.mkdir(parents=True)
    wav_path = session_dir / "final.wav"
    webm_path = session_dir / "final.webm"
    wav_path.write_bytes(b"wav")
    webm_path.write_bytes(b"webm")

    selected = audio_service.transcription_source_path("sess", "audio")
    assert selected == wav_path


def test_transcription_source_fallback_webm(tmp_path, monkeypatch):
    monkeypatch.setattr(audio_service.settings, "MEDIA_UPLOAD_ROOT", str(tmp_path))
    monkeypatch.setattr(audio_service.settings, "EXTRACT_WAV", 1)

    session_dir = tmp_path / "sess2" / "audio"
    session_dir.mkdir(parents=True)
    webm_path = session_dir / "final.webm"
    webm_path.write_bytes(b"webm")

    selected = audio_service.transcription_source_path("sess2", "audio")
    assert selected == webm_path


def test_transcription_source_missing_files(tmp_path, monkeypatch):
    monkeypatch.setattr(audio_service.settings, "MEDIA_UPLOAD_ROOT", str(tmp_path))
    monkeypatch.setattr(audio_service.settings, "EXTRACT_WAV", 1)

    with pytest.raises(FileNotFoundError):
        audio_service.transcription_source_path("unknown", "audio")


def test_transcribe_session_media_reads_file(tmp_path, monkeypatch):
    monkeypatch.setattr(audio_service.settings, "MEDIA_UPLOAD_ROOT", str(tmp_path))
    monkeypatch.setattr(audio_service.settings, "EXTRACT_WAV", 1)

    session_dir = tmp_path / "sess3" / "audio"
    session_dir.mkdir(parents=True)
    wav_path = session_dir / "final.wav"
    wav_path.write_bytes(b"audio-bytes")

    recorder = RecorderStub()
    monkeypatch.setattr(audio_service, "get_audio_service", lambda: recorder)

    result = audio_service.transcribe_session_media("sess3", kind="audio")

    assert result == "transcribed"
    assert recorder.received == b"audio-bytes"
