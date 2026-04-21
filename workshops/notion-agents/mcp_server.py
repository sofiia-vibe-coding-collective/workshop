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

load_dotenv()
log = logging.getLogger("workshop.mcp")

PUBLIC_BASE_URL = os.environ.get("PUBLIC_BASE_URL", "http://localhost:8000").rstrip("/")
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
