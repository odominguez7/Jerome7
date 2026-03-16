<div align="center">

<img src="https://jerome7.com/assets/logo.svg" alt="Jerome7" width="120" />

# Jerome7

**7 minutes. Show up. The world gets better.**

The open-source AI wellness infrastructure for builders, coders, and dreamers.

[![GitHub Stars](https://img.shields.io/github/stars/odominguez7/Jerome7?style=for-the-badge&color=e8713a&label=Stars)](https://github.com/odominguez7/Jerome7/stargazers)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue?style=for-the-badge)](LICENSE)
[![Jerome Count](https://img.shields.io/badge/dynamic/json?url=https://api.jerome7.com/stats&query=$.total_jeromes&label=Jeromes&style=for-the-badge&color=01696F)](https://jerome7.com/globe)
[![Discord](https://img.shields.io/discord/1303563828498292758?style=for-the-badge&logo=discord&color=5865F2)](https://discord.gg/5AZP8DbEJm)

[Live Site](https://jerome7.com) · [The Globe](https://jerome7.com/globe) · [Quick Start](#quick-start) · [Discord](https://discord.gg/5AZP8DbEJm) · [Docs](https://jerome7.com/docs)

</div>

---

> *"I was 80 lbs overweight. Couldn't run a mile. Started with 7 minutes a day. That became the Boston Marathon. Then Ironman 70.3. Then MIT. Not because I was exceptional. Because I was consistent."*
>
> — Omar, Jerome7 (Founder)

---

## What is Jerome7?

A daily 7-minute guided session: breathwork, meditation, reflection, or preparation. Powered by AI agents that learn your patterns and match you with accountability partners worldwide.

**No exercise. No equipment. Just earphones and a place to sit.**

The activity changes every 24 hours. Same session for every builder on Earth. Like Wordle, but for your mind.

## Quick Start

```bash
npx jerome7
```

<details>
<summary><strong>Other ways to start</strong></summary>

**Web**: [jerome7.com](https://jerome7.com)
**Discord**: [Join the community](https://discord.gg/5AZP8DbEJm)
**API**: `curl https://api.jerome7.com/session/today`

</details>

---

## Why?

86% of Gen Z report burnout before age 25. Building software is solitary.

Jerome7 is the intervention. 7 minutes of showing up — every day, together, globally.

**Backed by science**: [Peking University research](https://pmc.ncbi.nlm.nih.gov/articles/PMC10917090/) confirms 7-minute breathing reduces stress (p < .001), increases serenity, and decreases anxiety.

---

## The 5 AI Agents

| Agent | What It Does |
|-------|-------------|
| **Coach** | Generates your daily session via Gemini 2.5 Flash. Reads your feedback. Adjusts tomorrow. |
| **Nudge** | Learns your skip patterns. Fires a reminder *before* you ghost. |
| **Streak** | 3-miss rule. Miss 3 days, chain breaks. 1 save per 30 days. |
| **Community** | Matches pods of 3-5 builders by timezone + engagement level. |
| **Scheduler** | Finds your optimal session window from your history. |

Every agent communicates via [A2A protocol](https://developers.googleblog.com/en/a2a-a-new-era-of-agent-interoperability/). External AI agents can join — [see our AgentCard](https://jerome7.com/.well-known/agent.json).

### Agent Interoperability

Jerome7 welcomes connections from **any AI agent platform**:

- **OpenClaw** — enterprise-scale orchestration
- **ZeroClaw** — edge-first, Rust-based agents
- **A2A Protocol** — Google's agent-to-agent standard
- **MCP Protocol** — Anthropic's tool integration layer

> Bring your own agent. Build wellness skills. Join the mesh.

---

## The Globe

Every dot is a builder who showed up today.

**[See the world light up](https://jerome7.com/globe)**

---

## Your Jerome# Identity

Every user is Jerome#. Your number. Your identity. First come, first served.

```
Jerome7  → Omar (Founder)
Jerome8  → You? →  jerome7.com/join
Jerome9  → The next builder who shows up
...
Jerome42 → Someone, somewhere, showing up today
```

### Add Your Streak to Your README

```markdown
![My Jerome7 Streak](https://jerome7.com/embed/badge/YOUR_NUMBER)
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI (Python) |
| Database | PostgreSQL + Row-Level Security |
| AI | Gemini 2.5 Flash, ElevenLabs |
| Audio | ElevenLabs TTS + binaural ambient |
| Globe | Three.js + WebGL |
| Protocols | A2A (Google), MCP (Anthropic) |
| Hosting | Vercel + Railway |
| CLI | npx jerome7 |

---

## The $1,000 Promise

I'm investing $1,000 of my personal savings into this community.

Every dollar tracked publicly → [jerome7.com/sponsor](https://jerome7.com/sponsor)

Because data is all that matters right now. And YU matter.

---

## Contributing

We welcome every contribution. [Read the guide](CONTRIBUTING.md)

```bash
# Clone and run locally
git clone https://github.com/odominguez7/Jerome7.git
cd Jerome7
pip install -r requirements.txt
python -m uvicorn src.api.main:app --reload
```

---

## Star This Repo

If you believe 7 minutes can change a life, **[star this repo](https://github.com/odominguez7/Jerome7)**.

---

<div align="center">

**Built by [Omar](https://github.com/odominguez7) & [Miguel](https://jerome7.com)**

Apache 2.0 · Personally funded · Open source · No paywall

*It's on YU.*

</div>
