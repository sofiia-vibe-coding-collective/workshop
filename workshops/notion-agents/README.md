# Notion Agent Workshop

An MCP server that gives Notion Custom Agents three creative superpowers:

- **`generate_image`** — generate pictures from text (Gemini)
- **`generate_audio`** — text-to-speech narration (ElevenLabs)
- **`generate_sound_effect`** — sound effects from descriptions (ElevenLabs)

Built for a workshop teaching non-technical people how to build Notion agents that do things Notion can't do out of the box.

## What is this for?

Notion Custom Agents can natively search your workspace, read/write databases, send Slack messages, draft emails, and trigger on schedules or mentions. What they *can't* do natively is generate images, speak out loud, or produce sound effects — so this MCP server fills that gap.

Paste this server's URL into your Notion agent as a **Custom MCP connection**, and the 3 tools above become available to any agent you build.

## Workshop day setup (attendees)

Nothing to run. The instructor hosts one shared MCP server for the whole room. Just add the URL they give you to your Notion agent:

1. Open a Notion Custom Agent → **Tools** → **Add MCP connection**
2. Paste the workshop URL: `https://…/mcp`
3. All 3 tools appear. Enable them.
4. Start building. See `workshop/CHALLENGES.md` for ideas.

## Self-hosting (for after the workshop)

### Option 1 — Deploy to Railway

1. Sign up at [railway.com](https://railway.com)
2. **New Project → Deploy from GitHub repo**
3. Pick `vibe-coding-collective/vibecoders.global`
4. In project **Settings → Source** set **Root Directory** to `workshops/notion-agents`
5. In **Variables**, add:
   - `GEMINI_API_KEY` — from [aistudio.google.com/apikey](https://aistudio.google.com/apikey)
   - `ELEVENLABS_API_KEY` — from [elevenlabs.io](https://elevenlabs.io/app/settings/api-keys)
6. **Settings → Networking → Generate Domain** to get a public URL
7. Done. Your MCP endpoint is `https://your-app.up.railway.app/mcp` — paste that into Notion.

The server auto-detects Railway's domain via `RAILWAY_PUBLIC_DOMAIN`, so generated files are served at the correct public URL with no extra config.

### Option 2 — Run locally

```bash
git clone https://github.com/YOUR-USERNAME/notion-agent-workshop
cd notion-agent-workshop
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env     # add your GEMINI_API_KEY and ELEVENLABS_API_KEY
python main.py
```

Server runs on `http://localhost:8000`. To let Notion reach it, expose via ngrok:

```bash
ngrok http 8000
```

Paste the ngrok HTTPS URL + `/mcp` into Notion.

## Environment variables

| Var | Required | Description |
|-----|----------|-------------|
| `GEMINI_API_KEY` | For images | From [aistudio.google.com/apikey](https://aistudio.google.com/apikey) |
| `ELEVENLABS_API_KEY` | For audio/SFX | From [elevenlabs.io](https://elevenlabs.io/app/settings/api-keys) |
| `PUBLIC_BASE_URL` | Yes | Public URL of this server (no trailing slash) |
| `PORT` | No | Default 8000 |
| `STATIC_MAX_AGE_DAYS` | No | How long to keep generated files (default 7) |

If keys are missing the tools still run — they return tiny placeholder files so you can test the wiring without burning credits.

## Architecture

```
Notion Custom Agent
      │
      │  MCP JSON-RPC over HTTP
      ▼
 /mcp  ◄── FastMCP server
      │
      ├─ generate_image       → image_gen.py → Gemini API
      ├─ generate_audio       → audio_gen.py → ElevenLabs TTS
      └─ generate_sound_effect → audio_gen.py → ElevenLabs SFX
                                     │
                                     ▼
                          Write bytes to static/{uuid}.{ext}
                                     │
                                     ▼
                      Return https://.../static/{uuid}.{ext}
                                     │
                                     ▼
                          Notion embeds the URL in a page
```

Everything runs in a single uvicorn process. Files older than 7 days auto-delete.

## License

MIT
