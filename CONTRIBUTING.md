# Contributing to Jerome7

7 minutes. Show up. Build with us.

Jerome7 is open source (MIT) and we welcome contributions from builders everywhere.

## Quick Start

```bash
git clone https://github.com/odominguez7/Jerome7.git
cd Jerome7
pip install -r requirements.txt
cp .env.example .env  # add your API keys
python -m uvicorn src.api.main:app --reload --port 8000
```

## Good First Issues

Look for issues tagged `good first issue`. Some ideas:

- **Improve the timer UI** -- animations, transitions, mobile polish
- **Add a language** -- translate session narration to your language
- **Write tests** -- we need pytest coverage for core routes
- **Improve CLI** -- add flags like `--no-color`, `--quiet`, `--json`
- **New session types** -- contribute breathing or meditation scripts

## How to Contribute

1. Fork the repo
2. Create a branch: `git checkout -b my-feature`
3. Make your changes
4. Test locally: `python -m uvicorn src.api.main:app --reload`
5. Commit: `git commit -m "Add: description of change"`
6. Push: `git push origin my-feature`
7. Open a Pull Request

## Project Structure

```
src/api/routes/     # All API endpoints (FastAPI)
src/api/models.py   # Pydantic models
src/agents/         # AI agents (coach, streak, pattern)
src/db/             # Database (PostgreSQL + SQLAlchemy)
cli/                # npx jerome7 CLI tool
```

## Code Style

- Python: Follow PEP 8, use type hints
- Keep routes simple -- one file per feature
- No shame-based language. "Show up" not "no excuses"
- This is a daily reset (breathwork, grounding, reflection). Never fitness/exercise/bodyweight
- Use: reset, grounding, lock in, recharge, maintenance. Avoid: wellness, self-care, mindfulness
- "Session" not "workout". "Streak" or "chain" for consistency tracking

## Need Help?

- [Discord](https://discord.gg/5AZP8DbEJm)
- [jerome7.com](https://jerome7.com)
- Open an issue

Built at MIT. Personally funded. Open source.
