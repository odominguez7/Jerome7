---
title: I Built 5 Autonomous AI Agents to Stop Me From Skipping My Daily 7 Minutes
published: false
description: How I used FastAPI, Gemini 2.5 Flash, and the Model Context Protocol to build an AI-powered fitness system that predicts when you'll skip -- and intervenes before you do.
tags: ai, python, opensource, fitness
cover_image:
canonical_url:
---

## I Lost 80 Lbs Starting With 7 Minutes a Day

I'm not a gym person. Two years ago I was 280 lbs, working long hours, and every fitness app I tried assumed I had motivation to spare. They'd give me a 45-minute workout plan, a meal prep schedule, and a progress dashboard. I'd use it for 11 days and quit.

What actually worked was stupidly simple: 7 minutes of bodyweight exercises. Every single day. No equipment, no gym, no decisions. Just show up and move for 7 minutes.

That practice took me from 280 lbs to 200 lbs, then to the Boston Marathon, then to an Ironman 70.3. Not because 7 minutes is some magic number -- but because it's short enough that you can't negotiate your way out of it.

I built Jerome7 to give that same system to every builder on Earth. And then I built 5 AI agents to make sure you actually stick with it.

## The Problem: Every Fitness App Assumes Motivation

Here's what I noticed after losing the weight: the hard part was never the workout. It was the 30 seconds before the workout where your brain generates every possible excuse.

Every fitness app I've seen treats motivation as an input. "You're motivated, here's your plan." But motivation is the thing that fails. It's unreliable, it fluctuates, and it actively works against you on the days that matter most.

What if instead of assuming motivation, your system *predicted when motivation would fail* and intervened before it happened?

## The Insight: AI Agents That Intervene Before You Skip

Jerome7 generates one 7-minute bodyweight session every day. Same session for everyone on Earth, same day. Think Wordle, but you move. Seven 1-minute blocks, you do them, you're done.

But the session itself is just the surface. Underneath, 5 autonomous AI agents are working to keep you consistent.

## The 5 Agents

### 1. Coach Agent

**What it does:** Adapts exercise difficulty based on your completion history.

**How it works:** The Coach tracks your block completion rate over a rolling 14-day window. If you're consistently finishing all 7 blocks, it introduces progressive overload -- harder variations, longer holds, more explosive movements. If your completion rate drops below 70%, it scales back to maintain the "I can do this" threshold.

Session generation uses Gemini 2.5 Flash. The prompt includes your recent history, current fitness level classification, and constraints (bodyweight only, no equipment, indoor-safe). The model generates exercise selections and rep counts calibrated to your trajectory.

### 2. Nudge Agent

**What it does:** Predicts when you're likely to skip and sends a pre-emptive intervention.

**How it works:** The Nudge agent builds a skip-probability model from your behavioral patterns. Features include: day of week, time since last session, current streak length, historical skip days, and gap patterns. It doesn't use anything fancy -- logistic regression on your personal history is enough when you have 2+ weeks of data.

When skip probability crosses a configurable threshold (default: 0.6), the agent triggers a nudge. The key insight is *timing* -- the nudge fires during your typical session window, not after you've already missed it.

### 3. Streak Agent

**What it does:** Manages a 3-miss chain break mechanic instead of binary streaks.

**How it works:** Traditional streaks are psychologically fragile. Miss one day and your 47-day streak is gone. Research on habit formation shows this "what the hell" effect causes most post-streak abandonment.

Jerome7 uses a 3-miss chain. You get 3 grace days before your streak resets. Miss Monday? Still alive. Miss Tuesday? Two strikes. Miss Wednesday? Chain breaks. This maps more closely to how real habit resilience works -- it's not about perfection, it's about bouncing back.

The Streak agent tracks your chain state, surfaces your current strike count, and adjusts nudge urgency as you approach the break threshold.

### 4. Community Agent

**What it does:** Matches you into accountability pods of 3-5 people.

**How it works:** The agent clusters users by timezone (within 2 hours), fitness level classification, and activity window overlap. Pods are intentionally small because accountability research consistently shows that small groups outperform large communities for behavior change.

Pod members can see each other's completion status for the day (not details, just done/not-done). Social proof at the smallest viable scale.

### 5. Scheduler Agent

**What it does:** Learns your preferred session time and optimizes nudge delivery.

**How it works:** For the first 14 days, the Scheduler observes when you complete sessions. It builds a probability distribution over your active hours and identifies your modal session time. After the learning period, it shifts nudge timing to align with your natural pattern -- 15 minutes before your typical start time.

If your pattern shifts (e.g., you switch from morning to evening sessions), the agent detects the drift and re-calibrates over a 7-day window.

## Architecture

```
+--------------------------------------------------+
|                   Clients                         |
|  Web App | npx jerome7 | Claude | GPT-4 | Gemini |
+--------------------------------------------------+
              |            |
              v            v
        +----------+  +----------+
        | REST API |  | MCP API  |
        | /daily   |  | tools    |
        | /log     |  | /pledge  |
        | /streak  |  | /nudge   |
        +----------+  +----------+
              |            |
              v            v
        +-------------------------+
        |      FastAPI Core       |
        |  Session Generation     |
        |  User Management        |
        |  Agent Orchestration    |
        +-------------------------+
              |           |
              v           v
     +-----------+  +-----------+
     | PostgreSQL|  | Gemini    |
     | Users     |  | 2.5 Flash |
     | Sessions  |  | Session   |
     | Streaks   |  | Gen       |
     | Pods      |  |           |
     +-----------+  +-----------+
```

## The MCP Angle: Why This Matters Beyond Fitness

Jerome7 is MCP-native. It exposes itself as a Model Context Protocol server, which means any MCP-compatible AI assistant can interact with it through standard tool calls.

Your Claude Desktop can:
- Pull today's session (`jerome7_daily`)
- Check your streak (`jerome7_streak`)
- Log a completed session (`jerome7_log`)
- Get nudge status (`jerome7_nudge`)
- Find you an accountability pod (`jerome7_pod_match`)

This matters because it's a concrete example of what the agent ecosystem looks like when fitness becomes a *capability* your AI assistant has, rather than a separate app you have to open and navigate. The assistant can proactively check if you've done your session, remind you at the right time, and log it -- all within the conversation you're already having.

If you're building MCP servers, Jerome7 is a working reference implementation of a real-world MCP service with user state, daily content generation, and multi-agent coordination.

## Results

Jerome7 is live and being used by builders across multiple countries. Daily retention data and streak distributions are available on the dashboard. The 3-miss chain break mechanic has measurably reduced post-miss abandonment compared to traditional binary streaks.

## Why I'm Personally Funding This

Jerome7 is personally funded by the founder while the community grows. No premium tier, no "unlock advanced features," no subscription. It's open source under Apache 2.0, built at MIT.

Seven minutes of movement shouldn't have a paywall. The people who need this most -- the ones working 12-hour days, the ones who've failed at every gym membership, the ones who think fitness isn't for them -- are exactly the people who won't pay $15/month for another app.

The entire thesis of Jerome7 is that the barrier should be as close to zero as possible. Free, no equipment, no decisions, 7 minutes. That's it.

## Try It

- **Live:** [jerome7.com](https://jerome7.com)
- **CLI:** `npx jerome7` -- get today's session in your terminal
- **GitHub:** [github.com/odominguez7/jerome7](https://github.com/odominguez7/jerome7) -- star the repo if this resonates
- **Discord:** [discord.gg/jerome7](https://discord.gg/jerome7) -- join the community
- **MCP:** Add Jerome7 as an MCP server in Claude Desktop or any compatible client

If you've ever struggled with consistency -- not just in fitness, but in anything -- I'd love to hear what you think. The agent architecture is the part I'm most interested in feedback on.

Seven minutes. Every day. That's the whole thing.
