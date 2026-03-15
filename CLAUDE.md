# Jerome7 — Project Instructions for Claude Code

## What is Jerome7
Daily 7-minute guided wellness for builders. Breathwork, meditation, reflection, preparation — rotating daily. Powered by 5 AI agents. Free forever. Apache 2.0.

## Stack
- **Backend**: FastAPI (Python 3.13), SQLAlchemy ORM, SQLite (dev) / PostgreSQL (prod)
- **AI**: Gemini 2.5 Flash (coach), ElevenLabs TTS (voice)
- **Frontend**: Server-rendered HTML via FastAPI HTMLResponse, vanilla JS, Three.js (globe)
- **Protocols**: A2A (Google agent discovery), MCP (Anthropic tool integration)
- **Hosting**: Railway (auto-deploys from main), GitHub
- **CLI**: Node.js (`npx jerome7`)

## Project Structure
```
src/
  api/
    main.py          — FastAPI app, CORS, router registration
    models.py        — Pydantic request/response schemas
    routes/           — All route handlers (landing, timer, globe, voice, pledge, etc.)
  agents/
    coach.py         — CoachAgent (Gemini 2.5 Flash session generation)
    session_types.py — Daily rotation logic (breathwork/meditation/reflection/preparation)
  db/
    database.py      — Engine, sessions, lightweight migrations
    models.py        — SQLAlchemy ORM models (User, Session, Streak, Pod, etc.)
cli/
  index.js           — npx jerome7 CLI tool
```

## Key Conventions
- All HTML pages are inline in Python route files (no template engine except streak_page)
- JetBrains Mono font, dark theme (#0d1117), orange accent (#E85D04)
- Nav should be minimal: JEROME7 | Globe | Discord | GitHub | START
- Jerome7 is WELLNESS (breathing, meditation) — never call it fitness/exercise/bodyweight
- Jerome# identity: auto-assigned from 8+, Jerome7 = Omar (founder)
- Session types rotate daily using epoch-based modular arithmetic

## Development
```bash
# Run locally
pip install -r requirements.txt
python3 -m uvicorn src.api.main:app --reload --port 8000

# Lint
python3 -m ruff check .

# CLI
node cli/index.js --wellness
```

## Deploy
Push to `main` → Railway auto-deploys. No manual steps needed.

## Important Rules
- NEVER use exercise/bodyweight/fitness language — this is wellness/breathing/meditation
- Keep nav clean — only Globe, Discord, GitHub, START
- All new DB columns need migration entries in `database.py:_migrate_add_columns()`
- CORS is whitelisted to specific origins (see main.py)
- The founder is Omar (Jerome7). Miguel is co-builder.
