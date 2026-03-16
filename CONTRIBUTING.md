# Contributing to Jerome7

7 minutes. Show up. Build with us.

Jerome7 is open source (MIT) and we welcome contributions from builders everywhere.

## Quick Start

```bash
# Clone
git clone https://github.com/odominguez7/Jerome7.git
cd Jerome7

# Install
pip install -r requirements.txt

# Run locally
uvicorn src.api.main:app --reload --port 8000

# Visit http://localhost:8000
```

## Good First Issues

Look for issues tagged `good first issue` — these are designed for new contributors.

Some ideas:
- **Add a new exercise type** — extend the session generator with yoga, stretching, or mobility blocks
- **Improve the timer UI** — animations, sound effects, dark/light mode toggle
- **Add a language** — translate session instructions to your language
- **Write tests** — we need pytest coverage for core routes
- **Improve CLI** — add flags like `--no-color`, `--quiet`, `--json`

## How to Contribute

1. Fork the repo
2. Create a branch: `git checkout -b my-feature`
3. Make your changes
4. Test locally: `uvicorn src.api.main:app --reload`
5. Commit: `git commit -m "Add: description of change"`
6. Push: `git push origin my-feature`
7. Open a Pull Request

## Project Structure

```
src/api/routes/     # All API endpoints (FastAPI)
src/api/models.py   # Pydantic models
src/db/             # Database (PostgreSQL + SQLAlchemy)
mcp_server/         # MCP server (6 tools for AI agents)
cli/                # npx jerome7 CLI tool
integrations/       # OpenClaw, ZeroClaw configs
```

## Code Style

- Python: Follow PEP 8, use type hints
- Keep routes simple — one file per feature
- No shame-based language in user-facing copy (see our messaging guide)
- "Session" not "workout". "Chain" not "streak". "Show up" not "no excuses".

## Need Help?

- [Discord](https://discord.gg/5AZP8DbEJm)
- [jerome7.com](https://jerome7.com)
- Open an issue

Built at MIT. Personally funded. Open source.
