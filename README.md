# Jerome7

**5 autonomous AI agents. 7 minutes. One daily session for everyone on earth.**

[![Live](https://img.shields.io/badge/live-jerome7.com-E85D04?style=flat-square)](https://jerome7.com)
[![Discord](https://img.shields.io/badge/discord-join-5865F2?style=flat-square)](https://discord.gg/5AZP8DbEJm)
[![License: Apache 2.0](https://img.shields.io/badge/license-Apache%202.0-blue?style=flat-square)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-3776AB?style=flat-square)](https://python.org)
[![MCP](https://img.shields.io/badge/MCP-compatible-blueviolet?style=flat-square)](#mcp-server)

---

## What is this?

Jerome7 is a **multi-agent AI system** for daily physical accountability. Not a workout app. Not a chatbot wrapper. A coordination system where 5 agents observe your behavior, learn from feedback, and act autonomously — generating sessions, preventing skips, forming accountability pods, and adapting to your body over time.

One session generated per day. Same for everyone. Like Wordle, but you move.

**[jerome7.com](https://jerome7.com)** · **[Leaderboard](https://jerome7.com/leaderboard)** · **[Timer](https://jerome7.com/timer)**

---

## Why Agentic (Why Not a Normal App)

| Normal fitness app | Jerome7 |
|---|---|
| Static exercise database | AI generates novel sessions daily via Gemini 2.5 Flash |
| You set reminders | Nudge agent learns your skip patterns and intervenes before you break |
| You pick your workout | Coach reads your feedback history, adapts difficulty, avoids what hurts |
| Solo or follow influencer | Community agent matches you into pods of 3-5 by timezone + level |
| Manual scheduling | Scheduler agent finds optimal windows from session history |
| Binary streak (miss = reset) | Streak agent: 3-miss rule, saves, milestone tracking |

**The agents don't just respond — they observe, decide, and act without human intervention.** After `/pledge`, the system runs itself: generating sessions, sending nudges, forming pods, adapting to feedback.

---

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│                    JEROME7 CORE ENGINE                   │
│                                                          │
│  ┌─────────┐  ┌─────────┐  ┌──────────┐  ┌───────────┐ │
│  │  Coach   │  │  Nudge  │  │  Streak  │  │ Community │ │
│  │  Agent   │  │  Agent  │  │  Agent   │  │  Matcher  │ │
│  │         │  │         │  │         │  │           │ │
│  │ Gemini  │  │ learns  │  │ 3-miss  │  │ timezone  │ │
│  │ 2.5     │  │ skip    │  │ rule +  │  │ + level   │ │
│  │ Flash   │  │ hours → │  │ saves + │  │ scoring → │ │
│  │    ↓    │  │ preempt │  │ miles-  │  │ pods of   │ │
│  │ adapts  │  │ DMs     │  │ tones   │  │ 3-5       │ │
│  │ from    │  │         │  │         │  │           │ │
│  │ feedback│  └────┬────┘  └────┬────┘  └─────┬─────┘ │
│  └────┬────┘       │            │              │       │
│       │      ┌─────┴────┐      │        ┌─────┴─────┐ │
│       │      │Scheduler │      │        │ Feedback  │ │
│       │      │  Agent   │◄─────┘        │   Loop    │ │
│       │      │          │               │           │ │
│       │      │ finds    │               │ difficulty│ │
│       │      │ optimal  │               │ enjoyment │ │
│       │      │ windows  │               │ body notes│ │
│       │      └──────────┘               │     ↓     │ │
│       │                                 │ feeds back│ │
│       ◄─────────────────────────────────┤ to Coach  │ │
│       │                                 └───────────┘ │
│  ┌────┴───────────────────────────────────────────┐    │
│  │              FastAPI + SQLite                  │    │
│  │  /daily  /pledge  /log  /streak  /nudge        │    │
│  │  /pod    /feedback  /leaderboard  /timer       │    │
│  └─────┬──────────┬──────────┬────────────────────┘    │
└────────┼──────────┼──────────┼─────────────────────────┘
         │          │          │
   ┌─────┴───┐ ┌───┴────┐ ┌──┴───────────┐
   │ Discord │ │  MCP   │ │  OpenClaw /  │
   │   Bot   │ │ Server │ │  ZeroClaw   │
   │         │ │        │ │   Skills    │
   │ /seven7 │ │ 6 tools│ │             │
   │ /log    │ │ stdio  │ │  SKILL.md   │
   │ /streak │ │        │ │  .toml      │
   └─────────┘ └────────┘ └─────────────┘
```

---

## The 5 Agents

### Coach Agent
Generates today's session via **Google Gemini 2.5 Flash**. Reads user context: energy level, streak state, session history, and — critically — **past feedback**. If you said "knees hurt" last session, today's session avoids impact. If completion rate is dropping, difficulty scales down. Not a prompt wrapper — a feedback-driven adaptation loop.

```python
# Context fed to Gemini includes:
# - Last 5 session feedbacks (difficulty, enjoyment, body notes)
# - Average completion rate (X/7 blocks)
# - Skip history (which days/hours user typically misses)
# - Current streak length and energy level
# - Pod activity (who else showed up today)
```

### Nudge Agent
Analyzes session gaps to build a **skip probability model**. If you typically skip at 6pm on Wednesdays, the nudge arrives at 4pm. Rate-limited (1 per 4 hours). Never shames. Optionally generates personalized messages via Gemini.

### Streak Agent
Implements the **3-miss rule**: miss 1 day, chain holds. Miss 2, still holds. Miss 3, breaks. One save per 30 days for travel/illness. Milestones at 7, 14, 30, 50, 100, 200, 365 days. Longest streak never resets.

### Community Matcher
Scores user compatibility on **timezone overlap**, **fitness level similarity**, and **availability window intersection**. Forms pods of 3-5 with generated names. Threshold-based matching (0.4 minimum) prevents bad pairings.

### Scheduler Agent
Analyzes session timestamps to find your **habitual training window**. For pods, tallies each member's preferred hour and finds the time that works for the most people. Pure logic, no AI calls — deterministic and fast.

---

## The Feedback Loop (What Makes It Learn)

```
User does session → /log → bot asks: 💪 easy  👍 good  🔥 hard
                                         ↓
                              SessionFeedback stored
                              (difficulty, body_note, completion)
                                         ↓
                              Next session: Coach reads last 5 feedbacks
                              → adapts difficulty, avoids painful exercises
                              → adjusts phase intensity
```

This is the core agentic behavior. Each session is informed by the outcomes of previous sessions. The system doesn't just generate — it **converges** toward what works for each user.

---

## Daily Seven7 Structure

Every session follows the same shape. 7 blocks. 60 seconds each. 420 seconds total.

```
PRIME  (60s)  — 1 block. Wake the body.
BUILD  (180s) — 3 blocks. Strength + mobility.
MOVE   (120s) — 2 blocks. Heart rate. Fun.
RESET  (60s)  — 1 block. Breath. Stillness.
```

Bodyweight only. No equipment. Small space. Beginner-friendly. 10-word max instructions.

---

## Integrations

### MCP Server

Jerome7 exposes a **Model Context Protocol** server with 6 tools. Any MCP-compatible agent (Claude, OpenClaw, ZeroClaw) can call Jerome7 natively.

```json
// Claude Desktop — claude_desktop_config.json
{
  "mcpServers": {
    "jerome7": {
      "command": "python",
      "args": ["-m", "mcp_server.server"],
      "env": { "JEROME7_API_URL": "https://jerome7.com" }
    }
  }
}
```

**Tools:** `jerome7_daily`, `jerome7_pledge`, `jerome7_log`, `jerome7_streak`, `jerome7_nudge`, `jerome7_pod_match`

### OpenClaw

Drop-in skill for [OpenClaw](https://github.com/openclaw/openclaw). Copy `integrations/openclaw/SKILL.md` to your OpenClaw skills directory.

### ZeroClaw

TOML config for [ZeroClaw](https://github.com/zeroclaw-labs/zeroclaw). HTTP-based tools that call the Jerome7 API. See `integrations/zeroclaw/jerome7.toml`.

---

## Quick Start

### Join via Discord (easiest)
```
1. Join: discord.gg/5AZP8DbEJm
2. Type: /pledge
3. Type: /seven7
4. Do the 7 minutes
5. Type: /log
```

### Run locally
```bash
git clone https://github.com/odominguez7/Jerome7.git
cd Jerome7
pip install -r requirements.txt

# Set environment variables
export GEMINI_API_KEY=your_key      # Google Gemini 2.5 Flash
export DATABASE_URL=sqlite:///jerome7.db

# Start the API
uvicorn src.api.main:app --host 0.0.0.0 --port 8000

# (Optional) Start the Discord bot
export DISCORD_TOKEN=your_token
export DISCORD_GUILD_ID=your_guild
export YU_API_URL=http://localhost:8000
python discord_bot/bot.py
```

### API endpoints
```
GET  /daily                  → Today's universal session
POST /pledge                 → Register a user
POST /log/{user_id}          → Log a completed session
POST /log/{user_id}/feedback → Submit session feedback
GET  /streak/{user_id}       → Streak data + chain grid
GET  /seven7/{user_id}       → Personalized session
POST /pod/{user_id}/match    → Find accountability pod
GET  /nudge/at-risk          → Users who need a nudge
GET  /leaderboard            → Global leaderboard (HTML)
GET  /leaderboard/data       → Leaderboard data (JSON)
GET  /timer                  → Live countdown timer (HTML)
GET  /share/{user_id}        → Shareable streak card (HTML)
```

---

## Tech Stack

| Component | Technology |
|---|---|
| API | FastAPI + Uvicorn |
| AI | Google Gemini 2.5 Flash |
| Database | SQLite + SQLAlchemy |
| Bot | discord.py v2 (slash commands) |
| Integrations | MCP, OpenClaw, ZeroClaw |
| Hosting | Railway |
| Domain | jerome7.com (Cloudflare DNS) |

---

## The Streak Rules

```
Show up   = 7 minutes. That's it.
Miss 1    → Chain holds.
Miss 2    → Still holds. Life happens.
Miss 3    → Chain breaks. Start over.
Save      → 1 per 30 days. Use it for travel, illness, life.
Longest   → Never resets. That's your record.
Milestones → 7, 14, 30, 50, 100, 200, 365 days.
```

---

## The Story

I was 80 pounds heavier than I am today. Not because I didn't know better — because I had decided, without ever saying it out loud, that working hard was the only thing that mattered.

I started with 7 minutes of walking. Every single day. That was the whole thing.

I ended up running the **Boston Marathon**. I finished an **Ironman 70.3**.

Not because I was exceptional. Because I was consistent. And because I stopped being alone in it.

Jerome7 is that system — open sourced, free forever, for the developer community that changed my life.

---

## Why "Jerome 7"?

Jerome Morrow is the character from *Gattaca* (1997) — genetically engineered for perfection, and still fell. This project is for the opposite person: the one who was told they were average. The one who decides that's not the whole story.

7 minutes a day. Unbroken. No algorithm tells you what you're worth.

---

## Contributing

PRs welcome. The codebase is straightforward:
- `src/agents/` — The 5 agent implementations
- `src/api/routes/` — FastAPI endpoints
- `src/db/models.py` — SQLAlchemy models
- `discord_bot/bot.py` — Discord integration
- `mcp_server/` — MCP server
- `integrations/` — OpenClaw + ZeroClaw skills

---

## License

Apache 2.0. Free forever. No premium tier. No paywall. No plan to monetize.

The infrastructure costs are covered personally as an act of giving back to the community.

---

*Built by [Omar](https://github.com/odominguez7). It's on YU. It's for YU.*
