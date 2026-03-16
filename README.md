<div align="center">

<img src="https://jerome7.com/assets/logo.svg" alt="Jerome7" width="120" />

# Jerome7

**7 minutes. Show up. The world gets better.**

The open-source AI wellness infrastructure for builders, coders, and dreamers.

[![GitHub Stars](https://img.shields.io/github/stars/odominguez7/Jerome7?style=for-the-badge&color=e8713a&label=Stars)](https://github.com/odominguez7/Jerome7/stargazers)
[![License](https://img.shields.io/badge/License-MIT-blue?style=for-the-badge)](LICENSE)
[![Jerome Count](https://img.shields.io/badge/dynamic/json?url=https://api.jerome7.com/stats&query=$.total_jeromes&label=Jeromes&style=for-the-badge&color=01696F)](https://jerome7.com/globe)
[![Discord](https://img.shields.io/discord/1303563828498292758?style=for-the-badge&logo=discord&color=5865F2)](https://discord.gg/5AZP8DbEJm)

[Live Site](https://jerome7.com) · [The Globe](https://jerome7.com/globe) · [Quick Start](#quick-start) · [Discord](https://discord.gg/5AZP8DbEJm)

</div>

---

## What is Jerome7?

A daily 7-minute guided session: breathwork, meditation, reflection, or preparation. Powered by 5 AI agents that learn your patterns and match you with accountability partners worldwide. Same session for every builder on Earth, rotating daily.

**No exercise. No equipment. Just earphones and a place to sit.**

## Quick Start

```bash
npx jerome7
```

**Web**: [jerome7.com/timer](https://jerome7.com/timer)
**Discord**: [Join the community](https://discord.gg/5AZP8DbEJm)
**API**: `curl https://api.jerome7.com/session/today`

---

## The 5 AI Agents

| Agent | Role |
|-------|------|
| **Coach** | Generates daily sessions via Gemini 2.5 Flash. Reads feedback. Adjusts tomorrow. |
| **Nudge** | Learns skip patterns. Fires a reminder before you ghost. |
| **Streak** | 3-miss rule. Miss 3 days, chain breaks. 1 save per 30 days. |
| **Community** | Matches pods of 3-5 builders by timezone + engagement. |
| **Scheduler** | Finds your optimal session window from history. |

All agents communicate via [A2A protocol](https://developers.googleblog.com/en/a2a-a-new-era-of-agent-interoperability/). External AI agents can connect via [AgentCard](https://jerome7.com/.well-known/agent.json) or [MCP](https://modelcontextprotocol.io).

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI (Python 3.13), SQLAlchemy |
| Database | PostgreSQL + Row-Level Security |
| AI | Gemini 2.5 Flash, ElevenLabs TTS |
| Globe | Three.js + WebGL |
| Protocols | A2A (Google), MCP (Anthropic) |
| Hosting | Railway |
| CLI | `npx jerome7` |

---

## Run Locally

```bash
git clone https://github.com/odominguez7/Jerome7.git
cd Jerome7
pip install -r requirements.txt
python -m uvicorn src.api.main:app --reload
```

---

## Contributing

We welcome every contribution. [Read the guide](CONTRIBUTING.md).

---

<div align="center">

**Built by [Omar](https://github.com/odominguez7) & [Miguel](https://jerome7.com)**

MIT · Personally funded · Open source · No paywall

*It's on YU.*

</div>
