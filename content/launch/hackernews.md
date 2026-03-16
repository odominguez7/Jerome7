# Show HN Post

**Title:** Show HN: Jerome7 -- 5 AI Agents That Talk to Each Other to Prevent Developer Burnout

---

Hey HN,

I'm Omar. MIT Sloan MBA + MIT AI Studio (Media Lab). Two years ago I was 280 lbs and couldn't run a block. I started doing 7 minutes of bodyweight movement a day. That turned into losing 80 lbs, the Boston Marathon, and an Ironman 70.3.

The thing that worked wasn't any particular exercise. It was the ritual. Seven minutes is short enough that you can't negotiate your way out of it.

**What Jerome7 is:**

One 7-minute bodyweight session. Same for everyone on Earth, every day. Like Wordle, but you move. 7 blocks, 60 seconds each. No decisions, no browsing, no customization. You open it, you do it, you're done.

**The 5 agents (and why they talk to each other):**

This is where it gets technical. Jerome7 runs 5 autonomous AI agents that coordinate via an agent-to-agent protocol:

1. **Coach** -- Generates today's session via Gemini 2.5 Flash. Reads your last 5 session feedbacks (difficulty, enjoyment, body notes). If you said "knees hurt," tomorrow has zero impact work. If completion is dropping, difficulty scales down.

2. **Nudge** -- Builds a skip probability model from your session gaps. If you typically ghost at 6pm Wednesdays, the nudge fires at 4pm. Rate-limited to 1 per 4 hours. Never shames.

3. **Streak** -- Implements a 3-miss rule borrowed from behavioral research on habit formation. Miss 1 day, chain holds. Miss 2, still holds. Miss 3, it breaks. One save per 30 days for travel/illness. Binary streaks are too fragile -- this is the fix.

4. **Community** -- Scores builder compatibility on timezone overlap, fitness level, and availability windows. Forms accountability pods of 3-5. Threshold-based matching (0.4 minimum) prevents bad pairings.

5. **Scheduler** -- Analyzes session timestamps to find habitual training windows. For pods, finds the time that works for the most members. Deterministic, no AI calls.

These agents share anonymized context through our mesh. The Coach reads Streak state and Nudge patterns. The Nudge reads Scheduler windows. The Community matcher reads everyone's data to form pods. They coordinate to keep you consistent without you managing any of it.

**MCP-native:**

This is the part I think is genuinely novel. Jerome7 is an MCP server with 6 tools. Your AI assistant -- Claude, GPT, Gemini, anything that speaks Model Context Protocol -- can check your chain, pull today's session, log completions, and nudge you through standard tool calls. The fitness layer becomes a capability your agent has, not a separate app you open.

**The globe:**

Every builder who shows up today is a dot on a 3D globe at jerome7.com/globe. Watch the world light up as sessions happen across time zones.

**Tokens:**

Non-financial commitment tokens. Earn 10 for completing a session, 25 for helping others, 50 for code contributions. Spend on guided audio, coaching calls, community events. Not crypto. Not monetized. Just a way to make showing up tangible.

**AI voice mode:**

ElevenLabs TTS narrates each block live. "Block 3: Bear Crawl. Starting now." Falls back to Web Speech API if no key is set. The voice turns 7 minutes into a guided experience.

**The $1,000 promise:**

I'm investing $1K of my own money into this community. Every dollar tracked publicly at jerome7.com/sponsor. Because this isn't a startup -- it's a commitment.

**Details:**

- Personally funded. Open source. No paywall. No ads. Apache 2.0.
- `npx jerome7` gets you a session from your terminal
- FastAPI + PostgreSQL + Gemini 2.5 Flash
- Hosted on Railway, domain on Cloudflare

**Links:**

- Live: https://jerome7.com
- Globe: https://jerome7.com/globe
- GitHub: https://github.com/odominguez7/Jerome7
- Discord: https://discord.gg/5AZP8DbEJm
- CLI: `npx jerome7`

I'd love technical feedback on the agent mesh architecture and the MCP integration pattern. Happy to go deep on any of it.
