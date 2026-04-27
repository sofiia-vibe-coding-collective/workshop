"""
mixer.py — FFmpeg helpers for combining audio tracks.

Used by generate_narrated_track to layer TTS over music. Requires
ffmpeg + ffprobe on PATH (added via nixpacks.toml on Railway, comes
preinstalled on most macs via brew).
"""

import asyncio
import logging
import shutil
from pathlib import Path

log = logging.getLogger("workshop.mixer")


def _which(name: str) -> str:
    p = shutil.which(name)
    if not p:
        raise RuntimeError(f"{name} not found on PATH — install with `brew install ffmpeg`")
    return p


async def probe_duration(path: Path) -> float:
    """Return duration of an audio file in seconds via ffprobe."""
    proc = await asyncio.create_subprocess_exec(
        _which("ffprobe"),
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(path),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, _ = await proc.communicate()
    return float(stdout.decode().strip())


async def mix_voice_over_music(
    voice_path: Path,
    music_path: Path,
    output_path: Path,
    music_volume: float = 0.3,
) -> Path:
    """Mix narration on top of background music. Output is MP3.

    music_volume (0.0–1.0) controls the music level relative to the voice.
    Default 0.3 = music plays under voice without overpowering it.
    """
    music_volume = max(0.0, min(music_volume, 1.0))
    cmd = [
        _which("ffmpeg"), "-y",
        "-i", str(voice_path),
        "-i", str(music_path),
        "-filter_complex",
        f"[0:a][1:a]amix=inputs=2:duration=longest:weights=1 {music_volume}[aout]",
        "-map", "[aout]",
        "-c:a", "libmp3lame", "-q:a", "2",
        str(output_path),
    ]
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg mix failed: {stderr.decode()[-500:]}")
    return output_path
