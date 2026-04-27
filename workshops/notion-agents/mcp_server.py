"""
mcp_server.py — FastMCP server exposing 3 creative tools to Notion agents

Tools:
  - generate_image          (Gemini Imagen)
  - generate_audio          (ElevenLabs TTS)
  - generate_sound_effect   (ElevenLabs SFX)

Each tool saves its output to the shared `static/` directory and returns
a public URL built from PUBLIC_BASE_URL, which Notion embeds in pages.
"""

import logging
import os
import uuid as uuid_mod
from pathlib import Path

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

import audio_gen
import image_gen
import mixer

load_dotenv()
log = logging.getLogger("workshop.mcp")

def _resolve_public_url() -> str:
    """Pick the right public URL.

    Priority:
      1. PUBLIC_BASE_URL (explicit override)
      2. https://{RAILWAY_PUBLIC_DOMAIN} (auto-set by Railway)
      3. http://localhost:8000 (local dev fallback)
    """
    explicit = os.environ.get("PUBLIC_BASE_URL", "").strip()
    if explicit:
        return explicit.rstrip("/")
    railway_domain = os.environ.get("RAILWAY_PUBLIC_DOMAIN", "").strip()
    if railway_domain:
        return f"https://{railway_domain}"
    return "http://localhost:8000"


PUBLIC_BASE_URL = _resolve_public_url()
STATIC_DIR = Path(__file__).parent / "static"
STATIC_DIR.mkdir(exist_ok=True)

# Disable DNS rebinding protection by default.
# This server is meant to be reached from Notion via a public URL (ngrok, Railway),
# so the protection's Host header checks get in the way. Set MCP_ENABLE_HOST_CHECK=1
# if you want to re-enable it for local-only testing.
_transport = TransportSecuritySettings(
    enable_dns_rebinding_protection=os.environ.get("MCP_ENABLE_HOST_CHECK") == "1",
)

mcp = FastMCP(
    name="notion-workshop-mcp",
    json_response=True,
    host="0.0.0.0",
    transport_security=_transport,
)


def _detect_image_ext(data: bytes) -> str:
    """Detect image extension from magic bytes. Gemini may return JPEG or PNG."""
    if data[:3] == b"\xff\xd8\xff":
        return "jpg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    if data[:4] == b"GIF8":
        return "gif"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    return "png"  # safe default


def _save_and_get_url(data: bytes, ext: str) -> str:
    """Write bytes to static/{uuid}.{ext} and return its public URL."""
    filename = f"{uuid_mod.uuid4().hex}.{ext}"
    (STATIC_DIR / filename).write_bytes(data)
    return f"{PUBLIC_BASE_URL}/static/{filename}"


@mcp.tool()
async def generate_image(prompt: str, style: str = "") -> str:
    """Generate an image from a text prompt. Returns a public URL to a PNG.

    Use for cover images, illustrations, mood boards, visual summaries,
    comic panels, or any moment a Notion page needs a picture.

    Args:
        prompt: What the image should show. Be descriptive.
        style: Optional — e.g. 'photorealistic', 'cartoon', 'watercolor',
               'cyberpunk', 'minimalist line art', 'studio ghibli'.
    """
    log.info("generate_image(prompt=%r, style=%r)", prompt, style)
    data = await image_gen.generate(prompt, style)
    url = _save_and_get_url(data, _detect_image_ext(data))
    log.info("generated image → %s", url)
    return url


@mcp.tool()
async def generate_audio(text: str, voice: str = "default") -> str:
    """Generate spoken audio (text-to-speech) from text. Returns a public URL to an MP3.

    Use for voice notes, narrations, pep talks, bedtime stories,
    podcast intros, or any moment you want the agent to literally speak.

    Args:
        text: What should be said.
        voice: One of: 'default', 'warm_female', 'deep_male', 'british',
               'narrator', 'friendly'. Or any ElevenLabs voice ID.
    """
    log.info("generate_audio(voice=%r, text_len=%d)", voice, len(text))
    data = await audio_gen.generate_tts(text, voice)
    url = _save_and_get_url(data, "mp3")
    log.info("generated audio → %s", url)
    return url


@mcp.tool()
async def generate_sound_effect(prompt: str, duration_seconds: int = 5) -> str:
    """Generate a sound effect from a text description. Returns a public URL to an MP3.

    Use for meeting ambience, meditation sounds, notification chimes,
    dramatic stings, comedic effects, or any non-speech audio moment.

    Args:
        prompt: Describe the sound — e.g. 'soft rain on a tin roof',
                'triumphant fanfare', 'keyboard typing in an office'.
        duration_seconds: 1–22 seconds. Default 5.
    """
    log.info(
        "generate_sound_effect(prompt=%r, duration_seconds=%d)",
        prompt, duration_seconds,
    )
    data = await audio_gen.generate_sfx(prompt, duration_seconds)
    url = _save_and_get_url(data, "mp3")
    log.info("generated sfx → %s", url)
    return url


@mcp.tool()
async def generate_music(
    prompt: str,
    duration_seconds: int = 30,
    instrumental_only: bool = False,
) -> str:
    """Compose original music from a text prompt. Returns a public URL to an MP3.

    Use for soundtracks, intro/outro themes, background music for pages,
    workout playlists, study beats, mood-setting tracks, jingles.
    Generation typically takes 20-60 seconds depending on length.

    Args:
        prompt: Describe the music — genre, mood, instruments, tempo,
                era, vibe. E.g. 'uplifting cinematic orchestral with epic strings',
                'lofi hip-hop with jazzy piano', '80s synthwave with arpeggiated bass'.
        duration_seconds: 3–600 seconds (max 10 minutes). Default 30.
        instrumental_only: If True, guarantees no vocals. Default False —
                           model decides based on prompt.
    """
    log.info(
        "generate_music(prompt=%r, duration_seconds=%d, instrumental_only=%s)",
        prompt, duration_seconds, instrumental_only,
    )
    data = await audio_gen.generate_music(prompt, duration_seconds, instrumental_only)
    url = _save_and_get_url(data, "mp3")
    log.info("generated music → %s", url)
    return url


@mcp.tool()
async def generate_narrated_track(
    narration_text: str,
    music_prompt: str,
    voice: str = "default",
    music_volume: float = 0.45,
) -> str:
    """Generate a single MP3 with voiceover narration mixed over background music.

    Use for podcast intros, ad voiceovers, narrated trailers, guided meditations,
    bedtime stories with mood music, motivational pep talks with cinematic backing.

    The track length matches the narration's natural duration. Music is auto-sized
    to fit and faded under the voice.

    Args:
        narration_text: What the voice should say (≤ ~5000 chars).
        music_prompt: Describe the background music — genre, mood, instruments.
                      Will be generated as instrumental.
        voice: One of: 'default', 'warm_female', 'deep_male', 'british',
               'narrator', 'friendly'. Or any ElevenLabs voice ID.
        music_volume: 0.0–1.0, how loud the music sits under the voice.
                      Default 0.3 (music quiet enough to leave voice clear).
    """
    import tempfile
    import uuid as _uuid
    from pathlib import Path as _Path

    log.info(
        "generate_narrated_track(voice=%r, text_len=%d, music_prompt=%r)",
        voice, len(narration_text), music_prompt,
    )

    tmp = _Path(tempfile.mkdtemp(prefix="narrated_"))
    voice_path = tmp / "voice.mp3"
    music_path = tmp / "music.mp3"
    mixed_path = tmp / "mixed.mp3"

    try:
        voice_bytes = await audio_gen.generate_tts(narration_text, voice)
        voice_path.write_bytes(voice_bytes)

        # Match music duration to narration so it doesn't run on after the voice.
        voice_duration = await mixer.probe_duration(voice_path)
        music_seconds = max(3, min(int(voice_duration) + 2, 600))

        music_bytes = await audio_gen.generate_music(
            music_prompt, music_seconds, instrumental_only=True,
        )
        music_path.write_bytes(music_bytes)

        await mixer.mix_voice_over_music(
            voice_path, music_path, mixed_path, music_volume=music_volume,
        )

        out_filename = f"{_uuid.uuid4().hex}.mp3"
        out_path = STATIC_DIR / out_filename
        out_path.write_bytes(mixed_path.read_bytes())

        url = f"{PUBLIC_BASE_URL}/static/{out_filename}"
        log.info("generated narrated track → %s", url)
        return url
    finally:
        for f in (voice_path, music_path, mixed_path):
            try:
                f.unlink()
            except FileNotFoundError:
                pass
        try:
            tmp.rmdir()
        except OSError:
            pass
