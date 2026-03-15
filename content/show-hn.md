# Show HN: Jerome7 — 7-Min Daily Wellness for Developers (Open Source)

Hey HN — I'm Omar. I was 80 lbs overweight. Couldn't run a mile.

Started with 7 minutes of walking a day. That turned into the Boston Marathon,
then an Ironman 70.3, then MIT. Not because I was exceptional — because I was
consistent.

Jerome7 is what I wish existed back then. It's a daily 7-minute guided session
(breathwork, meditation, reflection — rotating daily) built specifically for
builders and coders. No exercise equipment. Just earphones and a place to sit.

**How it works:**

Every day, Jerome7 generates one wellness session. Same session for every builder
on Earth. The type rotates: breathwork → meditation → reflection → preparation.
Like Wordle, but for your mind.

Every user gets a Jerome# — a permanent identity (I'm Jerome7). First come,
first served. Low numbers become status symbols.

**The 5 AI agents:**

Tech stack: FastAPI + PostgreSQL + Gemini 2.5 Flash for AI coaching.
We have 5 AI agents that communicate via A2A protocol:

1. **Coach** — Generates sessions. Reads your feedback. Adjusts tomorrow.
2. **Nudge** — Learns skip patterns. Fires a reminder before you ghost.
3. **Streak** — 3-miss rule (not 1). 1 save per 30 days.
4. **Community** — Matches pods of 3-5 by timezone + engagement.
5. **Scheduler** — Finds your optimal session window.

**MCP-native:** Jerome7 is an MCP server. Claude, GPT, Gemini — any
MCP-compatible agent can check your streak, pull today's session, and
nudge you through standard tool calls.

**The globe:** Every builder who shows up is a dot on a 3D globe at
jerome7.com/globe. Watch the world light up.

**The science:** Peking University research (2023) confirms 7-minute breathing
reduces stress (p < .001), increases serenity, decreases anxiety.

**Details:**
- Free forever. No premium tier. No paywall. Apache 2.0.
- `npx jerome7` or `npx jerome7 --wellness` from your terminal
- 14 builders from 8+ countries so far

Would love feedback on the agent architecture and whether the 7-minute
format resonates. Happy to dive deep on the technical side.

- Live: https://jerome7.com
- GitHub: https://github.com/odominguez7/Jerome7
- Globe: https://jerome7.com/globe
- Discord: https://discord.gg/5AZP8DbEJm
