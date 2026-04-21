"""
image_gen.py — Gemini image generation (Nano Banana / Imagen Flash)

Returns raw PNG bytes. Uses Gemini 3.1 Flash image preview model.
If GEMINI_API_KEY is missing, returns a tiny placeholder PNG so the
workshop flow still works end-to-end for local dev without keys.
"""

import base64
import logging
import os

import httpx

log = logging.getLogger("workshop.image_gen")

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = "gemini-3.1-flash-image-preview"
GEMINI_URL = (
    f"https://generativelanguage.googleapis.com/v1beta/models/"
    f"{GEMINI_MODEL}:generateContent"
)

# 1x1 gray PNG for stub mode
_PLACEHOLDER_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x00\x00\x00\x00:~\x9bU\x00\x00\x00\x0bIDATx\x9cc\xfa\xff\xff?"
    b"\x00\x05\xfe\x02\xfeA\xb0\x96\x11\x00\x00\x00\x00IEND\xaeB`\x82"
)


async def generate(prompt: str, style: str = "") -> bytes:
    """Generate an image from a text prompt. Returns PNG bytes."""
    if not GEMINI_API_KEY:
        log.warning("GEMINI_API_KEY not set — returning stub PNG")
        return _PLACEHOLDER_PNG

    full_prompt = f"{prompt}, {style}" if style else prompt

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            GEMINI_URL,
            headers={
                "x-goog-api-key": GEMINI_API_KEY,
                "Content-Type": "application/json",
            },
            json={
                "contents": [{"parts": [{"text": full_prompt}]}],
                "generationConfig": {"responseModalities": ["IMAGE"]},
            },
        )
        resp.raise_for_status()
        data = resp.json()

    # Response shape: candidates[0].content.parts[*].inline_data.data (base64)
    for candidate in data.get("candidates", []):
        for part in candidate.get("content", {}).get("parts", []):
            inline = part.get("inline_data") or part.get("inlineData")
            if inline and inline.get("data"):
                return base64.b64decode(inline["data"])

    raise RuntimeError(f"Gemini returned no image. Full response: {data}")
