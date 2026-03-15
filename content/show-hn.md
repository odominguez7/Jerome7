# Show HN: Jerome7 -- 5 AI Agents, 7 Minutes, One Daily Session for Every Builder on Earth

Hey HN,

I'm Omar. Two years ago I weighed 280 lbs and couldn't run a block. I started with 7 minutes of bodyweight exercises a day -- that's it. No gym, no equipment, no plan beyond "just show up." I lost 80 lbs, ran the Boston Marathon, then finished an Ironman 70.3.

The thing that worked wasn't any particular workout. It was the consistency. Seven minutes is short enough that you can't talk yourself out of it.

**What Jerome7 is:**

Every day, Jerome7 generates one 7-minute bodyweight session. Same session for everyone on Earth, same day. Like Wordle, but you move. You open it, you do the 7 blocks (1 minute each), you're done. No decision fatigue, no browsing exercises, no personalization rabbit hole.

**The 5 agents:**

This is the part I'm most interested in feedback on. Jerome7 runs 5 autonomous AI agents that work together to keep you consistent:

1. **Coach** -- Adapts exercise difficulty based on your logged history. If you're consistently completing all blocks, it progressively loads. If you're struggling, it scales down. Uses Gemini 2.5 Flash for generation.

2. **Nudge** -- Predicts when you're likely to skip based on your historical patterns (time of day, day of week, streak length). Sends an intervention *before* the skip happens, not after.

3. **Streak** -- Implements a 3-miss chain break mechanic. You don't lose your streak on one missed day. You lose it after 3. This is borrowed from behavioral research on habit formation -- binary streaks are too fragile.

4. **Community** -- Matches you into accountability pods of 3-5 people based on timezone, fitness level, and activity window. Small group > large community for accountability.

5. **Scheduler** -- Learns your preferred session times and patterns over the first two weeks, then optimizes nudge timing accordingly.

**Tech stack:**

- FastAPI + PostgreSQL
- Gemini 2.5 Flash for session generation
- MCP-native: Jerome7 exposes itself as an MCP server, so it works natively with Claude, GPT-4, Gemini, or any MCP-compatible client
- `npx jerome7` gets you a session from your terminal

The MCP piece is what I think is genuinely new. Your AI assistant can check your streak, pull today's session, log completions, and nudge you -- all through standard tool calls. The fitness app becomes a capability your agent has, not a separate app you have to open.

**Why "Jerome7":**

Named after Jerome Morrow from Gattaca. The guy who had every genetic advantage but still needed someone else's determination to get to space. The name felt right for a project about proving that consistency beats talent.

**Details:**

- Free forever. No premium tier. No "unlock advanced features."
- Open source, Apache 2.0
- Built at MIT

**Links:**

- Live: https://jerome7.com
- GitHub: https://github.com/odominguez7/jerome7
- Discord: https://discord.gg/jerome7
- CLI: `npx jerome7`

I'd love feedback on the agent architecture specifically. The nudge prediction and streak mechanics are where I've spent the most time iterating. Happy to go deep on any of it.
