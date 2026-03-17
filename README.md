<div align="center">

<img src="https://jerome7.com/assets/logo.svg" alt="Jerome7" width="120" />

# Jerome7

**The commit you make to yourself before you commit code.**

AI-powered 7-minute wellness protocol for builders. Not a meditation app. A performance system.

[![GitHub Stars](https://img.shields.io/github/stars/odominguez7/Jerome7?style=for-the-badge&color=e8713a&label=Stars)](https://github.com/odominguez7/Jerome7/stargazers)
[![License](https://img.shields.io/badge/License-MIT-blue?style=for-the-badge)](LICENSE)
[![Jerome Count](https://img.shields.io/badge/dynamic/json?url=https://api.jerome7.com/stats&query=$.total_jeromes&label=Jeromes&style=for-the-badge&color=01696F)](https://jerome7.com/globe)
[![Discord](https://img.shields.io/discord/1303563828498292758?style=for-the-badge&logo=discord&color=5865F2)](https://discord.gg/5AZP8DbEJm)

[Live App](https://jerome7.com) · [Start Now](https://jerome7.com/timer) · [Globe](https://jerome7.com/globe) · [Discord](https://discord.gg/5AZP8DbEJm)

</div>

---

## Why

Builders burn out in silence. 72% of developers report mental health issues (Stack Overflow 2024). Headspace costs $70/year and speaks to yoga moms. Nothing exists for the person who just shipped at 2 AM and can't sleep.

Jerome7 is 7 minutes of breathwork, meditation, reflection, or preparation. Same session for every builder on Earth, rotating daily. AI-generated content. AI voice narration. Binaural beats. Streak accountability. Open source. No paywall.

**The science**: Box breathing drops cortisol 25% (Ma et al., 2017). Brief meditation boosts focus 14% (Zeidan et al., 2010). Theta binaural beats reduce anxiety 26% (Garcia-Argibay et al., 2019). Habits lock in at 66 days (Lally et al., 2010). Jerome7 is built around all four.

## Quick Start

```bash
npx jerome7
```

Or open [jerome7.com/timer](https://jerome7.com/timer) and press START.

---

## Architecture

Jerome7 is an **agentic wellness system**, not a timer with a Gemini API call. Three specialized agents coordinate to deliver personalized sessions:

```
                    +------------------+
                    |   Coach Agent    |  Gemini 2.5 Flash
                    |  Generates the   |  Session content
                    |  daily session   |  + voice script
                    +--------+---------+
                             |
              +--------------+--------------+
              |                             |
    +---------v---------+       +-----------v---------+
    |   Pattern Agent   |       |   Streak Agent      |
    |  Analyzes user    |       |  3-miss rule.       |
    |  behavior over    |       |  1 save per 30 days.|
    |  time. Completion |       |  Chain mechanics.    |
    |  rates, skip      |       |  Longest streak     |
    |  patterns, best   |       |  tracking.          |
    |  session times.   |       |                     |
    +-------------------+       +---------------------+
```

### Agent Details

| Agent | What It Does | How It Works |
|-------|-------------|-------------|
| **Coach** | Generates daily sessions via Gemini 2.5 Flash. 4 rotating types: breathwork, meditation, reflection, preparation. Validates 420-second structure. Falls back to handcrafted sessions if AI fails. | `src/agents/coach.py` |
| **Pattern** | Analyzes user behavior: completion rates, preferred session times, streak patterns, consistency scoring. Powers adaptive greetings and personalized insights. | `src/agents/pattern.py` |
| **Streak** | Enforces the 3-miss rule: miss 3 days and your chain breaks. 1 save per 30 days. Tracks current and longest streaks. The habit formation engine. | `src/agents/streak.py` |

### Protocol Support

| Protocol | Implementation | Status |
|----------|---------------|--------|
| **A2A** (Google) | Agent discovery via `/.well-known/agent.json` | Live |
| **Wellness Check API** | `GET /api/wellness-check/{jerome_number}` | Live |
| **Pattern Insights API** | `GET /api/insights/{jerome_number}` | Live |

AI assistants (Claude, ChatGPT, custom agents) can query your wellness data through these endpoints. Your streak is now part of your AI context.

---

## Viral Mechanics (for builders, by builders)

### GitHub Action: Wellness Gate

Add one YAML file to your repo. PRs won't merge until the author completes their 7 minutes.

```yaml
# .github/workflows/wellness-gate.yml
name: Jerome7 Wellness Gate
on: [pull_request]
jobs:
  wellness-check:
    runs-on: ubuntu-latest
    steps:
      - name: Check wellness
        run: |
          RESP=$(curl -s https://jerome7.com/api/wellness-check/github/${{ github.actor }})
          COMPLETED=$(echo $RESP | jq -r '.completed')
          if [ "$COMPLETED" != "true" ]; then
            echo "::warning::Complete your 7 minutes first: https://jerome7.com/timer"
            exit 1
          fi
```

One install = entire team exposed. Peer pressure through infrastructure.

### Pre-Commit Hook

```bash
npx jerome7 --setup-hook
```

Blocks your own commits until you show up. Skip anytime with `--no-verify`.

### README Badge

```markdown
![Jerome7](https://jerome7.com/badge/YOUR_NUMBER.svg)
```

Show your streak on your GitHub profile. When someone sees it, they ask "what's Jerome7?"

---

## Security and Anti-Abuse

Jerome7 is production-hardened with layered protections:

| Layer | Protection |
|-------|-----------|
| **Bot detection** | Honeypot fields + timing-based checks (< 3s = rejected silently) |
| **Rate limiting** | Per-IP (10 pledges/hr, 5 voice calls/hr) + per-user (5-min cooldown on session logs) |
| **Session validation** | Duration must be 5-15 min, max 3 sessions/day |
| **Auth tokens** | UUID Bearer tokens with 90-day expiration |
| **Fingerprint dedup** | Browser fingerprint prevents multi-account abuse from same device |
| **Real IP extraction** | Cloudflare CF-Connecting-IP > X-Forwarded-For > fallback |
| **Email verification** | HMAC-based stateless verification tokens |

All authentication is centralized in `src/api/auth.py`. No copy-pasted auth logic.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI (Python 3.13), SQLAlchemy |
| Database | PostgreSQL (prod), SQLite (dev) |
| AI | Gemini 2.5 Flash (sessions), ElevenLabs (voice) |
| Audio | Web Audio API (binaural beats, 5 frequency presets) |
| Globe | Three.js + WebGL (real-time user visualization) |
| Protocols | A2A (Google agent discovery) |
| Hosting | Railway (auto-deploys from main) |
| CLI | `npx jerome7` |

## Run Locally

```bash
git clone https://github.com/odominguez7/Jerome7.git
cd Jerome7
pip install -r requirements.txt
python -m uvicorn src.api.main:app --reload
```

## The Origin Story

I was 80 lbs overweight. Could not run a mile. Started with 7 minutes a day. That became the Boston Marathon. Then Ironman 70.3. Then MIT. Not because I was exceptional. Because I was consistent. Jerome7 is that 7 minutes, open-sourced for every builder on Earth.

---

## Contributing

Every contribution is welcome. [Read the guide](CONTRIBUTING.md).

---

<div align="center">

**Built by [Omar](https://github.com/odominguez7) (Jerome7)**

MIT License. Personally funded. Open source. No paywall.

*Show up.*

</div>
