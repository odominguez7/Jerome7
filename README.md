<div align="center">

<img src="https://jerome7.com/static/favicon.svg" alt="Jerome7" width="100" />

# Jerome7

**show your commitment before you commit.**

7-minute daily reset for builders. AI-generated breathwork, meditation, reflection, and preparation.
Same session for every builder on Earth, every day. Open source. Free forever.

[![Jerome7 Graph](https://jerome7.com/graph/7.svg)](https://jerome7.com/timer?ref=readme)

[![Start Now](https://img.shields.io/badge/START_NOW-E85D04?style=for-the-badge&logoColor=white)](https://jerome7.com/timer)
[![GitHub Stars](https://img.shields.io/github/stars/odominguez7/Jerome7?style=for-the-badge&color=30363d&label=Stars)](https://github.com/odominguez7/Jerome7/stargazers)
[![License: MIT](https://img.shields.io/badge/MIT-blue?style=for-the-badge)](LICENSE)
[![Discord](https://img.shields.io/badge/Discord-5865F2?style=for-the-badge&logo=discord&logoColor=white)](https://discord.gg/5AZP8DbEJm)

[Live App](https://jerome7.com/timer) · [Globe](https://jerome7.com/globe) · [CLI](#cli) · [API](#api) · [MCP Server](#mcp-server) · [Contributing](CONTRIBUTING.md)

</div>

---

### Try it right now

```bash
npx jerome7
```

Or open [jerome7.com/timer](https://jerome7.com/timer). No signup. No login. Just breathe.

---

## Why this exists

86% of Gen Z reports burnout before 25. We optimize code but never optimize the person writing it.

**Your commit history means nothing if you're falling apart.**

Jerome7 is a 7-minute daily reset. Four session types rotate every 24 hours -- breathwork, meditation, reflection, preparation -- so the entire community practices together. AI generates each session. AI narrates it. Binaural beats keep you locked in. Your streak holds you accountable.

The science behind it:

| Intervention | Effect | Source |
|---|---|---|
| Box breathing | 25% cortisol reduction | Ma et al., 2017 |
| Brief meditation | 14% focus improvement | Zeidan et al., 2010 |
| Theta binaural beats | 26% anxiety reduction | Garcia-Argibay et al., 2019 |
| Daily habit threshold | 66 days to lock in | Lally et al., 2010 |

Jerome7 is built around all four.

---

## How it works

```
Every day at midnight UTC, the rotation advances:

  Day 1 → Guided Breathwork (box breathing, body scan)
  Day 2 → Guided Meditation (breath awareness, gratitude)
  Day 3 → Reflection (journaling prompt, silent sit)
  Day 4 → Preparation (visualization, priorities, power statement)
  Day 5 → Back to Breathwork...
```

Three AI agents coordinate behind the scenes:

| Agent | Role | Source |
|---|---|---|
| **Coach** | Generates daily sessions via Gemini 2.5 Flash. Adapts from community feedback -- if difficulty is too high, it scales back. If people skip certain phases, it makes them more accessible. | [`src/agents/coach.py`](src/agents/coach.py) |
| **Streak** | Tracks consistency with a 3-miss rule. Miss 1-2 days? You're safe. Miss 3? Chain breaks. One save per 30 days for life stuff. Longest streak never resets -- that's your permanent record. | [`src/agents/streak.py`](src/agents/streak.py) |
| **Pattern** | Analyzes behavior across the community. Completion rates, preferred times, consistency scoring. Feeds insights back to Coach. | [`src/agents/pattern.py`](src/agents/pattern.py) |

---

## Add your streak to your GitHub profile

One line in your profile README. Updated daily. Every visitor sees your chain.

```markdown
[![Jerome7](https://jerome7.com/graph/YOUR_NUMBER.svg)](https://jerome7.com/timer?ref=graph)
```

**Get your number:** Open [jerome7.com/timer](https://jerome7.com/timer), breathe for 7 minutes. Your Jerome# is assigned automatically.

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    jerome7.com                          │
│                                                         │
│  ┌─────────┐  ┌──────────┐  ┌──────────┐  ┌─────────┐ │
│  │  Timer   │  │  Globe   │  │  Voice   │  │ Landing │ │
│  │ (7-min   │  │ (Three.js│  │(ElevenLabs│  │  Page   │ │
│  │ session) │  │  WebGL)  │  │  TTS)    │  │         │ │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └─────────┘ │
│       │              │              │                    │
│  ┌────┴──────────────┴──────────────┴─────────────────┐ │
│  │              FastAPI (Python 3.13)                  │ │
│  │                                                     │ │
│  │  ┌─────────┐  ┌──────────┐  ┌───────────┐         │ │
│  │  │  Coach  │  │  Streak  │  │  Pattern  │         │ │
│  │  │  Agent  │  │  Agent   │  │  Agent    │         │ │
│  │  └────┬────┘  └────┬─────┘  └─────┬─────┘         │ │
│  │       │             │              │                │ │
│  │  ┌────┴─────────────┴──────────────┴─────────────┐ │ │
│  │  │          SQLAlchemy ORM + PostgreSQL           │ │ │
│  │  └───────────────────────────────────────────────┘ │ │
│  └─────────────────────────────────────────────────────┘ │
│                                                         │
│  Integrations: Discord Bot · MCP Server · A2A Protocol  │
│  CLI: npx jerome7                                       │
└─────────────────────────────────────────────────────────┘
         │                    │
    Gemini 2.5 Flash    ElevenLabs TTS
    (session gen)       (voice narration)
```

### Tech stack

| Layer | Technology |
|---|---|
| **Backend** | FastAPI, Python 3.13, SQLAlchemy, Alembic |
| **Database** | PostgreSQL (prod), SQLite (dev) |
| **AI** | Gemini 2.5 Flash (session generation), ElevenLabs (voice narration) |
| **Audio** | Web Audio API (binaural beats -- 5 frequency presets: theta, alpha, delta, beta, gamma) |
| **3D** | Three.js + WebGL (real-time globe showing builders worldwide) |
| **Frontend** | Server-rendered HTML, vanilla JS, JetBrains Mono, dark theme |
| **Protocols** | [A2A](https://google.github.io/A2A/) (Google agent discovery), [MCP](https://modelcontextprotocol.io) (Anthropic tool integration) |
| **Hosting** | Railway (auto-deploys from `main`) |
| **CLI** | Node.js (`npx jerome7`) |
| **Bot** | discord.py (slash commands, streak tracking, daily auto-post) |

---

## Run locally

```bash
git clone https://github.com/odominguez7/Jerome7.git
cd Jerome7
pip install -r requirements.txt
cp .env.example .env          # add your GEMINI_API_KEY + VERIFY_SECRET
python -m uvicorn src.api.main:app --reload --port 8000
```

Open [localhost:8000/timer](http://localhost:8000/timer).

### Environment variables

| Variable | Required | Description |
|---|---|---|
| `GEMINI_API_KEY` | Yes | Google Gemini API key for session generation |
| `VERIFY_SECRET` | Prod only | HMAC secret for email tokens. App crashes on boot if missing in production |
| `DATABASE_URL` | No | PostgreSQL connection string. Defaults to SQLite for local dev |
| `ELEVENLABS_API_KEY` | No | Enables AI voice narration (falls back to browser speech) |
| `DISCORD_TOKEN` | No | Enables the Discord bot |
| `SMTP_HOST` / `SMTP_USER` / `SMTP_PASSWORD` | No | Enables daily reminder emails |

Full list in [`.env.example`](.env.example).

### Run tests

```bash
python -m pytest tests/ -v
```

### Lint

```bash
python -m ruff check .
```

---

## CLI

```bash
npx jerome7              # today's session in your terminal
npx jerome7 --wellness   # voice-guided mode
npx jerome7 --streak 42  # check a Jerome#'s streak
```

No install. No account. Works on macOS, Linux, and Windows.

---

## API

All endpoints are live at `https://jerome7.com`.

| Endpoint | Method | Description |
|---|---|---|
| `/timer` | GET | Full 7-minute guided session (HTML) |
| `/daily` | GET | Today's session as JSON |
| `/globe` | GET | Real-time 3D globe of builders worldwide |
| `/voice/{user_id}` | GET | AI-narrated voice session |
| `/pledge` | POST | Register a new builder |
| `/log/{user_id}` | POST | Log a completed session |
| `/streak/{user_id}` | GET | Streak data + 30-day chain |
| `/graph/{jerome_number}.svg` | GET | Dynamic SVG streak graph |
| `/api/wellness-check/{jerome_number}` | GET | Did this Jerome show up today? |
| `/api/wellness-check/github/{username}` | GET | Same, by GitHub username |
| `/api/insights/{user_id}` | GET | Consistency score, patterns |
| `/health` | GET | Service health check |
| `/.well-known/agent.json` | GET | A2A agent discovery |

### Pre-commit hook

Block your own commits until you've done your 7 minutes:

```bash
# .git/hooks/pre-commit
#!/bin/sh
STATUS=$(curl -s https://jerome7.com/api/wellness-check/YOUR_NUMBER | jq -r '.completed')
if [ "$STATUS" != "true" ]; then
  echo "Do your 7 minutes first: https://jerome7.com/timer"
  exit 1
fi
```

---

## MCP Server

Connect Jerome7 to Claude, GPT, or any MCP-compatible agent.

```bash
# Claude Code
claude mcp add jerome7 -- python -m mcp_server.server

# Claude Desktop — add to claude_desktop_config.json
{
  "mcpServers": {
    "jerome7": {
      "command": "python",
      "args": ["-m", "mcp_server.server"],
      "cwd": "/path/to/Jerome7"
    }
  }
}
```

Available tools: `jerome7_daily`, `jerome7_pledge`, `jerome7_log`, `jerome7_streak`, `jerome7_nudge`, `jerome7_pod_match`.

Full docs: [`mcp_server/README.md`](mcp_server/README.md)

---

## Discord Bot

Slash commands for your server:

| Command | What it does |
|---|---|
| `/pledge` | Join Jerome7, get your number |
| `/seven7` | See today's session |
| `/log` | Log your session, update your streak |
| `/streak` | View your chain (Wordle-style grid) |
| `/checkin` | Set your energy level |
| `/pod` | Find your accountability crew (3-5 builders) |
| `/save` | Use a streak save (1 per 30 days) |

Daily auto-posts to `#show-up-daily`. Nudges at-risk streaks via DM.

---

## Project structure

```
src/
  api/
    main.py              FastAPI app, CORS, security headers, router registration
    models.py            Pydantic request/response schemas (validated)
    auth.py              Token auth + rate limiting
    email_utils.py       HMAC email verification tokens
    reminders.py         Daily email reminder loop
    routes/              20 route modules (timer, voice, globe, pledge, etc.)
  agents/
    coach.py             Session generation (Gemini 2.5 Flash)
    streak.py            3-miss rule, saves, chain tracking
    pattern.py           User behavior analysis
    context.py           Shared state object for all agents
    session_types.py     Daily rotation (breathwork/meditation/reflection/preparation)
  db/
    models.py            SQLAlchemy ORM (11 tables)
    database.py          Engine, sessions, lightweight migrations
cli/
  index.js               npx jerome7 (Node.js)
discord_bot/
  bot.py                 Slash commands, daily posts, nudges
mcp_server/
  server.py              MCP tools for Claude/GPT integration
tests/
  test_streak.py         Streak logic (3-miss rule, saves, milestones)
  test_models.py         Pydantic validation
  test_email_utils.py    Token generation + tamper detection
```

---

## The origin story

> *"I never saved anything for the swim back."*
> -- Jerome Eugene Morrow, Gattaca

7 years ago: 80 lbs overweight. Sedentary. Stuck in a loop I could feel but couldn't name.

I didn't have a plan. I just started. And I never stopped.

That became the Boston Marathon. Ironman 70.3. Marrying the love of my life. This year, MIT -- where I found AI, code, and the world of building and shipping.

**None of this happened because I'm the smartest person in the room. It happened because I showed up every day.** Consistency is a muscle. You can train it. You train it by doing one thing, always, without exception.

That's what Jerome7 is. The one thing. 7 minutes. Named after a man engineered to be perfect who gave his identity to someone told he'd never be enough. For builders who don't accept what others say they can or can't do.

---

## Contributing

We welcome contributions from builders everywhere. See [CONTRIBUTING.md](CONTRIBUTING.md) for setup, code style, and good first issues.

```bash
git clone https://github.com/odominguez7/Jerome7.git
cd Jerome7
pip install -r requirements.txt
cp .env.example .env
python -m uvicorn src.api.main:app --reload --port 8000
```

**Good first issues:**
- Improve timer UI (animations, transitions, mobile polish)
- Add a language (translate session narration)
- New session types (contribute breathing or meditation scripts)
- Improve the CLI (flags, formatting, offline mode)

---

## Star this repo

Every star tells the next burned-out dev scrolling at 1 AM: *someone built this for you.*

**At 1,000 stars I will personally fund the ElevenLabs AI voice for every session.** Right now sessions use browser speech as fallback. Hit 1,000 and every builder on Earth gets a professionally narrated daily reset. No paywall. No catch. I pay for it.

---

<div align="center">

**Built by [Omar](https://github.com/odominguez7) · Jerome #7 · MIT Sloan '26**

MIT License. Personally funded. Open source. Free forever.

*Consistency compounds. Code ships. But only if you're still standing.*

</div>
