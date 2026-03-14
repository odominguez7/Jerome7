#!/bin/bash
# Start Discord bot in background if token is set
if [ -n "$DISCORD_TOKEN" ]; then
  python discord_bot/bot.py &
fi

# Start API (foreground — keeps container alive)
uvicorn src.api.main:app --host 0.0.0.0 --port $PORT
