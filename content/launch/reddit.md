# Reddit Launch Posts

---

## r/programming

**Title:** I built an open-source agent mesh where 5 AI agents coordinate to prevent developer burnout -- here's the architecture

**Body:**

I'm an MIT grad student who lost 80 lbs by doing 7 minutes of movement a day. I built Jerome7 to see if I could encode that consistency into an autonomous system.

**The architecture:**

5 AI agents running on FastAPI + PostgreSQL, coordinating through a shared context mesh:

- **Coach agent** calls Gemini 2.5 Flash with the last 5 session feedbacks (difficulty rating, body notes, completion rate). It adapts exercise selection and intensity without user intervention.
- **Nudge agent** builds a skip probability model from session timestamp gaps. Predicts when you'll break the chain and intervenes before it happens. Rate-limited, never spams.
- **Streak agent** implements a 3-miss break rule instead of binary streaks. One save per 30 days. Milestone tracking at 7/14/30/50/100/200/365.
- **Community matcher** scores compatibility on timezone overlap + fitness level + availability window. Forms pods of 3-5. Minimum threshold prevents bad matches.
- **Scheduler agent** is pure deterministic logic -- analyzes timestamps, finds optimal windows, no AI calls.

**The MCP piece:**

Jerome7 exposes itself as an MCP server with 6 tools. Any MCP-compatible agent (Claude, GPT, etc.) can call `jerome7_daily`, `jerome7_log`, `jerome7_streak`, etc. through standard tool calls. Your AI assistant becomes your accountability partner natively.

**The interesting technical decisions:**

- Agent-to-agent communication: Coach reads Streak state and Nudge patterns. Nudge reads Scheduler windows. Community reads everything. No centralized orchestrator.
- 3D globe (Three.js) renders real session data -- every dot is a builder who showed up today.
- Non-financial token system: earn tokens for sessions, contributions, helping others. Spend on guided audio and coaching calls. Not crypto.
- ElevenLabs TTS narrates sessions block-by-block with Web Speech API fallback.
- `npx jerome7` runs the full session in your terminal.

**Stack:** FastAPI, PostgreSQL, Gemini 2.5 Flash, Railway, Cloudflare, MCP protocol, ElevenLabs TTS

Open source, Apache 2.0, free forever. No premium tier.

- GitHub: https://github.com/odominguez7/Jerome7
- Live: https://jerome7.com
- CLI: `npx jerome7`

Would love feedback on the agent coordination pattern. The mesh approach vs. a centralized orchestrator has tradeoffs I'm still working through.

---

## r/webdev

**Title:** I built a full-stack wellness app with a 3D globe, AI voice narration, MCP integration, and a 5-agent backend -- all open source

**Body:**

Hey r/webdev. I'm Omar, MIT student. Built this as a community project and wanted to share the stack.

**What it is:** Jerome7 generates one 7-minute bodyweight session per day. Same for everyone on Earth. Like Wordle, but you move. 5 AI agents handle personalization, nudges, accountability pods, and chain tracking behind the scenes.

**The stack and what I learned:**

**Backend:**
- FastAPI + PostgreSQL on Railway ($5/mo hobby plan)
- Gemini 2.5 Flash for session generation (cost was a big factor -- way cheaper than OpenAI for this use case)
- Auto-deploy from GitHub to Railway

**Frontend pages:**
- `/` -- Landing with session preview, agent system explainer, live feed
- `/globe` -- 3D Three.js globe where every dot is a real builder who showed up today. Renders from live PostgreSQL data.
- `/timer` -- Universal 7-minute countdown
- `/leaderboard` -- Global leaderboard with country flags (detected via Cloudflare CF-IPCountry header)
- `/analytics` -- Visual dashboard (retention curves, demographics, chain distributions)
- `/live` -- Real-time collective movement dashboard, auto-refreshes every 30s
- `/share/{user_id}` -- Shareable chain cards with OG/Twitter meta tags for social previews
- `/voice` -- AI-narrated sessions via ElevenLabs TTS with Web Speech API fallback

**Integrations:**
- MCP server (Model Context Protocol) -- 6 tools that let any AI assistant interact with Jerome7 natively
- Discord bot with slash commands, daily posting, and nudge loops
- `npx jerome7` CLI that pulls today's session into your terminal
- Twitter/X auto-poster for daily sessions and leaderboard

**Infrastructure:**
- Cloudflare DNS-only for the domain
- PostgreSQL on Railway (migrated from SQLite for persistence across deploys)
- Country detection via CF-IPCountry header with timezone inference fallback

**Tokens:** Non-financial commitment tokens. Complete a session = 10 tokens. Help others = 25. Code contribution = 50. Redeemable for guided audio, coaching calls, community events.

Everything is open source under Apache 2.0. Free forever, no premium tier.

- Live: https://jerome7.com
- Globe: https://jerome7.com/globe
- GitHub: https://github.com/odominguez7/Jerome7
- Discord: https://discord.gg/5AZP8DbEJm

Happy to answer questions about any part of the stack.

---

## r/selfimprovement

**Title:** I lost 80 lbs by showing up for 7 minutes a day. I built a free tool so anyone can do the same thing.

**Body:**

Two years ago I was 280 lbs. Couldn't run a block. I tried every app, every program, every "transformation challenge." Nothing stuck because everything demanded too much on day one.

Then I tried something embarrassingly simple: 7 minutes of bodyweight movement. Every day. No gym. No equipment. No plan beyond "show up."

That turned into 80 lbs lost. The Boston Marathon. An Ironman 70.3. An MBA at MIT.

The trick was never the exercises. It was making the commitment so small that I couldn't talk myself out of it. Seven minutes. That's a commercial break. That's the time it takes to brew coffee.

**So I built Jerome7.**

It gives you one 7-minute session per day. Same session for every person on Earth. 7 blocks, 60 seconds each. Bodyweight only, no equipment, small space. You open it, you do it, you close it. Done.

**How the chain works:**

- Show up = do the 7 minutes
- Miss 1 day? Chain holds
- Miss 2 days? Still holds. Life happens.
- Miss 3 days? Chain breaks. Start fresh.
- 1 save per 30 days for when life genuinely gets in the way
- Your longest chain never resets. That record is yours forever.

The 3-miss rule exists because binary streaks are psychologically fragile. One bad day shouldn't erase 47 good ones.

**It has AI that learns you:**

- If you said something hurt last session, tomorrow's session avoids it
- It learns when you're likely to skip and nudges you before you break the chain
- It matches you into a small accountability group (3-5 people at your level and timezone)
- An AI voice can narrate each block so you just follow along

**The globe:**

There's a live 3D globe at jerome7.com/globe that lights up with every person who showed up today. Watching dots appear across time zones -- builders in Tokyo, Lagos, Sao Paulo, all doing the same session -- is genuinely motivating.

**It's free. Forever.**

No premium tier. No "unlock advanced features." No ads. I'm an MIT student subsidizing the hosting costs personally. I'm also investing $1K of my own money into the community, tracked publicly.

I built this because I believe the smallest commitment, repeated daily, is the most powerful force there is. YU matter.

- Website: https://jerome7.com
- From your terminal: `npx jerome7`
- Discord community: https://discord.gg/5AZP8DbEJm
- GitHub (open source): https://github.com/odominguez7/Jerome7
