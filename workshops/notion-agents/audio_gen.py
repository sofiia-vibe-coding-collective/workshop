"""
audio_gen.py — ElevenLabs text-to-speech and sound effects

Returns raw MP3 bytes. If ELEVENLABS_API_KEY is missing, returns a
minimal silent MP3 so local dev works without keys.
"""

import base64
import logging
import os

import httpx

log = logging.getLogger("workshop.audio_gen")

ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY", "")
TTS_MODEL = "eleven_multilingual_v2"
OUTPUT_FORMAT = "mp3_44100_128"

# Short voice name → ElevenLabs voice ID. Curated set from the public library.
VOICE_MAP = {
    "default":      "JBFqnCBsd6RMkjVDRZzb",  # George
    "warm_female":  "EXAVITQu4vr4xnSDxMaL",  # Sarah
    "deep_male":    "JBFqnCBsd6RMkjVDRZzb",  # George
    "british":      "ThT5KcBeYPX3keUQqHPh",  # Dorothy
    "narrator":     "pNInz6obpgDQGcFmaJgB",  # Adam
    "friendly":     "AZnzlk1XvdvUeBnXmlld",  # Domi
}

# ~370-byte silent MP3 (0.1s of silence at 8kHz) for stub mode
_PLACEHOLDER_MP3 = base64.b64decode(
    "//tQxAAAAAAAAAAAAAAAAAAAAAAASW5mbwAAAA8AAAACAAACqQBV"
    "VVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVV"
    "VVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVV"
    + "A" * 400  # pad to a plausible size; players accept this
)


def _resolve_voice_id(voice: str) -> str:
    """Map a friendly voice name to an ElevenLabs voice ID.
    If the caller passed a raw voice ID, pass it through."""
    if voice in VOICE_MAP:
        return VOICE_MAP[voice]
    # Assume it's already a voice ID
    return voice


async def generate_tts(text: str, voice: str = "default") -> bytes:
    """Generate speech audio from text. Returns MP3 bytes."""
    if not ELEVENLABS_API_KEY:
        log.warning("ELEVENLABS_API_KEY not set — returning stub MP3")
        return _PLACEHOLDER_MP3

    voice_id = _resolve_voice_id(voice)
    url = (
        f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        f"?output_format={OUTPUT_FORMAT}"
    )

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            url,
            headers={
                "xi-api-key": ELEVENLABS_API_KEY,
                "Content-Type": "application/json",
            },
            json={"text": text, "model_id": TTS_MODEL},
        )
        resp.raise_for_status()
        return resp.content


async def generate_sfx(prompt: str, duration_seconds: int = 5) -> bytes:
    """Generate a sound effect from a text description. Returns MP3 bytes."""
    if not ELEVENLABS_API_KEY:
        log.warning("ELEVENLABS_API_KEY not set — returning stub MP3")
        return _PLACEHOLDER_MP3

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            "https://api.elevenlabs.io/v1/sound-generation",
            headers={
                "xi-api-key": ELEVENLABS_API_KEY,
                "Content-Type": "application/json",
            },
            json={
                "text": prompt,
                "duration_seconds": max(1, min(duration_seconds, 22)),
            },
        )
        resp.raise_for_status()
        return resp.content


async def generate_music(
    prompt: str,
    duration_seconds: int = 30,
    instrumental_only: bool = False,
) -> bytes:
    """Compose original music from a prompt. Returns MP3 bytes.

    Duration: 3-600 seconds (3s to 10 minutes). Generation is slower than
    TTS or SFX — typically 20-60 seconds depending on length.
    """
    if not ELEVENLABS_API_KEY:
        log.warning("ELEVENLABS_API_KEY not set — returning stub MP3")
        return _PLACEHOLDER_MP3

    duration_ms = max(3000, min(duration_seconds * 1000, 600000))

    async with httpx.AsyncClient(timeout=240) as client:
        resp = await client.post(
            "https://api.elevenlabs.io/v1/music",
            headers={
                "xi-api-key": ELEVENLABS_API_KEY,
                "Content-Type": "application/json",
            },
            json={
                "prompt": prompt,
                "music_length_ms": duration_ms,
                "force_instrumental": instrumental_only,
                "model_id": "music_v1",
            },
        )
        resp.raise_for_status()
        return resp.content
