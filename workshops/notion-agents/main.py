"""
main.py — Notion Agent Workshop MCP Server

One uvicorn process on PORT (default 8000) that serves:
  /mcp       — the FastMCP endpoint Notion agents connect to
  /static/*  — public URLs for generated images and audio

Usage
─────
  pip install -r requirements.txt
  cp .env.example .env          # fill in API keys
  python main.py
"""

import asyncio
import logging
import os
import time
from pathlib import Path

import uvicorn
from dotenv import load_dotenv
from starlette.applications import Starlette
from starlette.routing import Mount
from starlette.staticfiles import StaticFiles

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(name)-24s  %(levelname)s  %(message)s",
)
log = logging.getLogger("workshop.main")

PORT = int(os.getenv("PORT", "8000"))
STATIC_MAX_AGE_DAYS = int(os.getenv("STATIC_MAX_AGE_DAYS", "7"))
STATIC_DIR = Path(__file__).parent / "static"
STATIC_DIR.mkdir(exist_ok=True)


async def cleanup_old_files() -> None:
    """Delete generated files older than STATIC_MAX_AGE_DAYS. Runs once at startup."""
    cutoff = time.time() - (STATIC_MAX_AGE_DAYS * 86400)
    removed = 0
    for f in STATIC_DIR.iterdir():
        if f.is_file() and f.stat().st_mtime < cutoff:
            f.unlink()
            removed += 1
    if removed:
        log.info("Cleaned %d file(s) older than %d days", removed, STATIC_MAX_AGE_DAYS)


def build_app() -> Starlette:
    """Build a single ASGI app that serves both MCP and /static/*."""
    from mcp_server import mcp

    mcp_app = mcp.streamable_http_app()

    # Mount /static first so it wins over the catch-all MCP mount.
    app = Starlette(
        routes=[
            Mount("/static", app=StaticFiles(directory=str(STATIC_DIR)), name="static"),
            Mount("/", app=mcp_app),
        ],
        lifespan=mcp_app.router.lifespan_context,
    )
    return app


async def run() -> None:
    await cleanup_old_files()

    app = build_app()
    config = uvicorn.Config(
        app=app,
        host="0.0.0.0",
        port=PORT,
        log_level="info",
        log_config=None,
    )
    server = uvicorn.Server(config)

    from mcp_server import PUBLIC_BASE_URL  # picks up Railway / .env / localhost
    log.info("Workshop MCP server starting on port %d", PORT)
    log.info("Notion agents connect at: %s/mcp", PUBLIC_BASE_URL)
    log.info("Generated files served at: %s/static/", PUBLIC_BASE_URL)

    await server.serve()


if __name__ == "__main__":
    asyncio.run(run())
