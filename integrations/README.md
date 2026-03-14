# Jerome7 Integrations

Add Jerome7's daily 7-minute accountability sessions to your AI agent platform.

## OpenClaw

**File:** `openclaw/SKILL.md`

### Setup

1. Copy `openclaw/SKILL.md` into your OpenClaw skills directory
2. The skill uses `http_request` and `shell` tools — make sure both are enabled
3. No API key required

### What it provides

- `jerome7 daily` — Get today's session
- `jerome7 pledge` — Register a user
- `jerome7 log` — Log a completed session
- `jerome7 streak` — Check streak data
- `jerome7 timer` — Open the session timer

## ZeroClaw

**File:** `zeroclaw/jerome7.toml`

### Setup

1. Copy `zeroclaw/jerome7.toml` into your ZeroClaw tools config directory
2. The config defines HTTP-based tools that call the Jerome7 API directly
3. No API key required

### What it provides

Four tools are defined:

| Tool | Method | Endpoint |
|------|--------|----------|
| `jerome7_daily` | GET | `/daily` |
| `jerome7_pledge` | POST | `/pledge` |
| `jerome7_log` | POST | `/log/{user_id}` |
| `jerome7_streak` | GET | `/streak/{user_id}` |

## API Base URL

All endpoints use `https://jerome7.com` as the base URL.

Session timer: [https://jerome7.com/timer](https://jerome7.com/timer)

## Links

- Site: [https://jerome7.com](https://jerome7.com)
- Discord: [https://jerome7.com/discord](https://jerome7.com/discord)
