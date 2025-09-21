from __future__ import annotations

import subprocess
from pathlib import Path
from typing import List


def join_webm_chunks(chunks: List[Path], out_webm: Path, ffmpeg_bin: str = "ffmpeg") -> None:
    """Concatenate webm chunks into a single file using ffmpeg concat demuxer."""
    if not chunks:
        raise ValueError("No chunks provided for concatenation")

    out_webm.parent.mkdir(parents=True, exist_ok=True)
    list_path = out_webm.parent / "list.txt"

    lines = [f"file '{chunk.resolve()}'" for chunk in chunks]
    list_path.write_text("\n".join(lines), encoding="utf-8")

    cmd = [
        ffmpeg_bin,
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(list_path),
        "-c",
        "copy",
        str(out_webm),
    ]

    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        stderr = ""
        if isinstance(exc, subprocess.CalledProcessError) and exc.stderr:
            stderr = exc.stderr.decode("utf-8", errors="ignore")
        raise RuntimeError(f"Failed to join webm chunks: {stderr or exc}") from exc
    finally:
        list_path.unlink(missing_ok=True)


def extract_wav(in_webm: Path, out_wav: Path, ffmpeg_bin: str = "ffmpeg") -> None:
    """Convert webm audio to mono 16kHz PCM WAV."""
    out_wav.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        ffmpeg_bin,
        "-i",
        str(in_webm),
        "-vn",
        "-ac",
        "1",
        "-ar",
        "16000",
        "-c:a",
        "pcm_s16le",
        str(out_wav),
    ]

    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        stderr = ""
        if isinstance(exc, subprocess.CalledProcessError) and exc.stderr:
            stderr = exc.stderr.decode("utf-8", errors="ignore")
        raise RuntimeError(f"Failed to extract wav: {stderr or exc}") from exc


def ensure_ffmpeg(ffmpeg_bin: str = "ffmpeg") -> bool:
    """Return True if ffmpeg binary is callable and responds to -version."""
    try:
        subprocess.run(
            [ffmpeg_bin, "-version"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False
    return True
