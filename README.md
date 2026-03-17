<div align="center">

<img src="https://jerome7.com/assets/logo.svg" alt="Jerome7" width="120" />

# Jerome7

**i breathe before i ship.**

your daily reset. 7 minutes of grounding before you ship. open source. free forever.

[![Jerome7 Wellness](https://jerome7.com/graph/7.svg)](https://jerome7.com/timer?ref=readme)

[![GitHub Stars](https://img.shields.io/github/stars/odominguez7/Jerome7?style=for-the-badge&color=e8713a&label=Stars)](https://github.com/odominguez7/Jerome7/stargazers)
[![License](https://img.shields.io/badge/License-MIT-blue?style=for-the-badge)](LICENSE)

[Start Now](https://jerome7.com/timer) · [Get Your Graph](https://jerome7.com/graph) · [Globe](https://jerome7.com/globe) · [Discord](https://discord.gg/5AZP8DbEJm)

</div>

---

## Add your reset graph to your GitHub profile

One line. Updated daily. Every visitor sees your streak.

```markdown
[![Jerome7 Wellness](https://jerome7.com/graph/YOUR_NUMBER.svg)](https://jerome7.com/timer?ref=graph)
```

**How to get your number:** Open [jerome7.com/timer](https://jerome7.com/timer), breathe for 7 minutes. Your Jerome# is assigned automatically. No signup. No login. Just show up.

---

## The Origin Story

> *"I never saved anything for the swim back."*
> -- Jerome Eugene Morrow, Gattaca

7 years ago: 80 lbs overweight. Sedentary. Stuck in a loop I could feel but couldn't name.

I didn't have a plan. I just started. And I never stopped.

That became the Boston Marathon. Ironman 70.3. Marrying the love of my life. This year, MIT -- where I found AI, code, and the world of building and shipping. My one regret? Not finding it sooner.

**None of this happened because I'm the smartest person in the room. It happened because I showed up every day.** Consistency is a muscle. You can train it. You train it by doing one thing, always, without exception.

That's what Jerome7 is. The one thing. 7 minutes. Named after a man engineered to be perfect who gave his identity to someone told he'd never be enough. For builders who don't accept what others say they can or can't do.

---

## Why

86% of Gen Z reports burnout before 25. We optimize code but never optimize the person writing it. We celebrate shipping but never talk about what it costs.

**Your commit history means nothing if you're falling apart.**

Jerome7 is a 7-minute daily reset. Breathwork, grounding, reflection, preparation. Same session for every builder on Earth, rotating daily. AI-generated. AI-narrated. Binaural beats. Streak accountability. Free forever.

**The science:** Box breathing drops cortisol 25% (Ma et al., 2017). Brief meditation boosts focus 14% (Zeidan et al., 2010). Theta binaural beats reduce anxiety 26% (Garcia-Argibay et al., 2019). Habits lock in at 66 days (Lally et al., 2010). Jerome7 is built around all four.

Vibe-coding and AI opened a door for people like me -- but **developers, engineers, and deep domain experts matter more than ever.** What's coming is multi-skilled human teams: technical + non-technical + agentic tools, breaking every status quo together. Jerome7 is proof of that thesis.

---

## We Need an OpenClaw for Humans

I want to keep learning. I want to learn from **you.**

I dream about YC, about working harder than I've ever worked, creating jobs, and building something bigger than myself. I want to show that a non-technical person can build things that matter -- and stand beside the most talented engineers on Earth.

But this isn't about me. It's about building **open infrastructure for human maintenance** the way we built it for servers. Stress monitoring. Daily check-ins. Mental health data that's ours. A community that talks about burnout as openly as we talk about latency.

**You find a friend in me.**

---

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
| `GET /api/wellness-check/{jerome_number}` | Check if a Jerome completed today's reset |
| `GET /api/wellness-check/github/{username}` | Same, by GitHub username |
| `GET /api/insights/{jerome_number}` | Streak data, consistency, patterns |
| `GET /graph/{jerome_number}.svg` | Dynamic reset graph (SVG) |
| `/.well-known/agent.json` | A2A agent discovery (Google protocol) |

### GitHub Action: Reset Gate

Add one YAML file. PRs won't merge until the author completes their 7-minute reset.

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

---

## Star This Repo

Every star tells the next burned-out dev scrolling at 1 AM: *someone built this for you.*

## Make It Better

- **Open issues** -- tell me what's broken, what's missing, what you need
- **Submit PRs** -- improve the audio, the agents, the UX, the science
- **Fork it** -- build your version, we'll learn from each other
- **Share it** -- X, Reddit, HN, Discord. Wherever builders live.

**Show your commitment before you commit.**

---

<div align="center">

**Built by [Omar](https://github.com/odominguez7) · Jerome #7 · MIT Sloan '26**

MIT License. Personally funded. Open source. No paywall.

*Consistency compounds. Code ships. But only if you're still standing.*

</div>
