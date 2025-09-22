from pathlib import Path
import types

import pytest

from backend.app.services import media_joiner


def test_join_webm_chunks_invokes_ffmpeg(tmp_path, monkeypatch):
    chunks = []
    for idx in range(2):
        chunk_path = tmp_path / f"part_{idx}.webm"
        chunk_path.write_bytes(f"chunk-{idx}".encode("utf-8"))
        chunks.append(chunk_path)

    output_path = tmp_path / "final.webm"
    created_paths: list[Path] = []

    def fake_run(cmd, check, stdout, stderr):  # noqa: ARG001
        created_paths.append(Path(cmd[-1]))
        Path(cmd[-1]).write_bytes(b"joined-webm")
        return types.SimpleNamespace(returncode=0)

    monkeypatch.setattr(media_joiner.subprocess, "run", fake_run)

    media_joiner.join_webm_chunks(chunks, output_path, ffmpeg_bin="ffmpeg")

    assert output_path.read_bytes() == b"joined-webm"
    assert created_paths and created_paths[0] == output_path
    assert not (output_path.parent / "list.txt").exists()


def test_join_webm_chunks_requires_chunks(tmp_path):
    output_path = tmp_path / "out.webm"
    with pytest.raises(ValueError):
        media_joiner.join_webm_chunks([], output_path)


def test_extract_wav_invokes_ffmpeg(tmp_path, monkeypatch):
    source = tmp_path / "final.webm"
    result = tmp_path / "audio" / "final.wav"
    source.write_bytes(b"webm-data")

    def fake_run(cmd, check, stdout, stderr):  # noqa: ARG001
        Path(cmd[-1]).write_bytes(b"wav-data")
        return types.SimpleNamespace(returncode=0)

    monkeypatch.setattr(media_joiner.subprocess, "run", fake_run)

    media_joiner.extract_wav(source, result, ffmpeg_bin="ffmpeg")

    assert result.read_bytes() == b"wav-data"


def test_ensure_ffmpeg_false_on_error(monkeypatch):
    def fake_run(cmd, check, stdout, stderr):  # noqa: ARG001
        raise FileNotFoundError("ffmpeg not found")

    monkeypatch.setattr(media_joiner.subprocess, "run", fake_run)

    assert media_joiner.ensure_ffmpeg("ffmpeg") is False
