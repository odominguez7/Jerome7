---
name: jerome7
description: Daily 7-minute accountability sessions. AI-generated. Streak-powered.
version: 1.0.0
author: omar
tools:
  - shell
  - http_request
---

# Jerome7 — Daily Seven

## What this skill does

Jerome7 delivers a daily 7-minute accountability session. Each session is AI-generated and adapts to the user. Users pledge, log completions, and build streaks over time.

This skill connects to the Jerome7 API so the AI agent can manage sessions, register users, log completions, and check streaks.

## Commands

- `jerome7 daily` — Fetch today's session
- `jerome7 pledge <name> <email>` — Register a new user
- `jerome7 log <user_id>` — Log a completed session
- `jerome7 streak <user_id>` — Check a user's current streak
- `jerome7 timer` — Open the 7-minute session timer

## Instructions for the AI

### Fetch today's session

Send a GET request to retrieve the current daily session:

```
GET https://jerome7.com/daily
Accept: application/json
```

Display the session content in a clean, minimal format. Keep it scannable — no walls of text.

### Register a user

Send a POST request with the user's information:

```
POST https://jerome7.com/pledge
Content-Type: application/json

{
  "name": "<name>",
  "email": "<email>"
}
```

Return the user ID from the response. Tell the user to save it for logging sessions.

### Log a completed session

After a user finishes their 7 minutes, log it:

```
POST https://jerome7.com/log/{user_id}
Content-Type: application/json
```

Confirm the log was recorded and show the updated streak count.

### Check streak data

Retrieve a user's streak information:

```
GET https://jerome7.com/streak/{user_id}
Accept: application/json
```

Display the streak count and any milestone information. Keep it brief.

### Timer

Direct the user to the session timer:

```
https://jerome7.com/timer
```

This is a browser-based 7-minute countdown timer for the session.

## Response formatting

- Keep all responses minimal and clean
- Use short confirmation messages after actions
- Show streak numbers prominently
- No unnecessary filler text
