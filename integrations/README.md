# Jerome7 — Agent Integrations

Add Jerome7 to any AI agent. No API key needed. Community-powered. Open source.

## Quick Install

### OpenClaw

```bash
# One command — paste this in your OpenClaw host terminal
mkdir -p ~/.openclaw/skills/jerome7 && curl -sL \
  https://raw.githubusercontent.com/odominguez7/Jerome7/main/integrations/openclaw/SKILL.md \
  -o ~/.openclaw/skills/jerome7/SKILL.md
```

Then in your agent chat, just say:
- **"jerome7"** or **"my session"** → today's session
- **"log my session"** or **"done"** → log it
- **"my streak"** → see your chain
- **"leaderboard"** → who's showing up globally
- **"sign me up"** → create your account

### ZeroClaw

```bash
# Copy the TOML to your skills directory
curl -sL \
  https://raw.githubusercontent.com/odominguez7/Jerome7/main/integrations/zeroclaw/jerome7.toml \
  -o ~/.zeroclaw/skills/jerome7.toml
```

### MCP (Claude, any MCP-compatible agent)

```json
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

## API Reference

All endpoints at `https://jerome7.com`. No auth required.

| What | Method | Endpoint | Body |
|------|--------|----------|------|
| Today's session | GET | `/daily` | — |
| Join | POST | `/pledge` | `{"name": "...", "timezone": "...", "source": "openclaw"}` |
| Log session | POST | `/log/{user_id}` | `{"duration_minutes": 7}` |
| Check streak | GET | `/streak/{user_id}` | — |
| Check status | GET | `/status/{user_id}` | — |
| Leaderboard | GET | `/leaderboard/data` | — |
| Submit feedback | POST | `/log/{user_id}/feedback` | `{"difficulty": 1\|3\|5}` |
| Analytics | GET | `/analytics/overview` | — |
| Retention | GET | `/analytics/retention` | — |

### Optional Pledge Fields

| Field | Values | Notes |
|-------|--------|-------|
| `age_bracket` | `18-24`, `25-34`, `35-44`, `45-54`, `55+` | Optional |
| `gender` | `male`, `female`, `other`, `skip` | Optional |
| `country` | ISO 2-letter code | Auto-derived from timezone if omitted |
| `source` | `discord`, `openclaw`, `zeroclaw`, `web`, `api`, `mcp` | Auto-tagged by integration |
| `goal` | `move_more`, `build_strength`, `destress`, `just_try` | Optional |

## Links

| | |
|---|---|
| Live | [jerome7.com](https://jerome7.com) |
| Timer | [jerome7.com/timer](https://jerome7.com/timer) |
| Leaderboard | [jerome7.com/leaderboard](https://jerome7.com/leaderboard) |
| Discord | [discord.gg/5AZP8DbEJm](https://discord.gg/5AZP8DbEJm) |
| GitHub | [github.com/odominguez7/Jerome7](https://github.com/odominguez7/Jerome7) |
