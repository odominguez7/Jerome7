<div align="center">

<img src="https://jerome7.com/assets/logo.svg" alt="Jerome7" width="120" />

# Jerome7

**i breathe before i ship.**

7 minutes of daily wellness for builders. Open source. No paywall. No login.

[![Jerome7 Wellness](https://jerome7.com/graph/7.svg)](https://jerome7.com/timer?ref=readme)

[![GitHub Stars](https://img.shields.io/github/stars/odominguez7/Jerome7?style=for-the-badge&color=e8713a&label=Stars)](https://github.com/odominguez7/Jerome7/stargazers)
[![License](https://img.shields.io/badge/License-MIT-blue?style=for-the-badge)](LICENSE)
[![Jerome Count](https://img.shields.io/badge/dynamic/json?url=https://api.jerome7.com/stats&query=$.total_jeromes&label=Jeromes&style=for-the-badge&color=01696F)](https://jerome7.com/globe)

[Start Now](https://jerome7.com/timer) · [Get Your Graph](https://jerome7.com/graph) · [Globe](https://jerome7.com/globe) · [Discord](https://discord.gg/5AZP8DbEJm)

</div>

---

## Add your wellness graph to your GitHub profile

One line. Updated daily. Every visitor sees your streak.

```markdown
[![Jerome7 Wellness](https://jerome7.com/graph/YOUR_NUMBER.svg)](https://jerome7.com/timer?ref=graph)
```

**How to get your number:** Open [jerome7.com/timer](https://jerome7.com/timer), breathe for 7 minutes. Your Jerome# is assigned automatically. No signup. No login. Just show up.

---

## Why

72% of developers report mental health issues (Stack Overflow 2024). Headspace costs $70/year and speaks to yoga moms. Nothing exists for the builder who just shipped at 2 AM and can't sleep.

Jerome7 is 7 minutes of breathwork, meditation, reflection, or preparation. Same session for every builder on Earth, rotating daily. AI-generated. AI-narrated. Binaural beats. Streak accountability. Free forever.

**The science**: Box breathing drops cortisol 25% (Ma et al., 2017). Brief meditation boosts focus 14% (Zeidan et al., 2010). Theta binaural beats reduce anxiety 26% (Garcia-Argibay et al., 2019). Habits lock in at 66 days (Lally et al., 2010). Jerome7 is built around all four.

## Quick Start

```bash
npx jerome7
```

Or open [jerome7.com/timer](https://jerome7.com/timer) and press START.

---

## Architecture

Three AI agents coordinate to deliver personalized sessions:

| Agent | What It Does | Source |
|-------|-------------|--------|
| **Coach** | Generates daily sessions via Gemini 2.5 Flash. 4 rotating types: breathwork, meditation, reflection, preparation. | `src/agents/coach.py` |
| **Pattern** | Analyzes user behavior: completion rates, preferred times, consistency scoring. | `src/agents/pattern.py` |
| **Streak** | 3-miss rule: miss 3 days and your chain breaks. 1 save per 30 days. | `src/agents/streak.py` |

### API Endpoints

| Endpoint | Description |
|----------|------------|
| `GET /api/wellness-check/{jerome_number}` | Check if a Jerome has completed today's session |
| `GET /api/wellness-check/github/{username}` | Same, by GitHub username |
| `GET /api/insights/{jerome_number}` | Streak data, completion rate, patterns |
| `GET /graph/{jerome_number}.svg` | Dynamic wellness contribution graph (SVG) |
| `/.well-known/agent.json` | A2A agent discovery (Google protocol) |

### GitHub Action: Wellness Gate

Add one YAML file. PRs won't merge until the author completes their 7 minutes.

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

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI (Python 3.13), SQLAlchemy |
| Database | PostgreSQL (prod), SQLite (dev) |
| AI | Gemini 2.5 Flash (sessions), ElevenLabs (voice) |
| Audio | Web Audio API (binaural beats, 5 frequency presets) |
| Globe | Three.js + WebGL (real-time visualization) |
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

<div align="center">

**Built by [Omar](https://github.com/odominguez7) (Jerome7)**

MIT License. Personally funded. Open source. No paywall.

*You are important. Take care of yourself.*

</div>
