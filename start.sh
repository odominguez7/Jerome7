#!/bin/bash
# Start Discord bot in background if token is set
if [ -n "$DISCORD_TOKEN" ]; then
  python discord_bot/bot.py &
fi

# Start API (foreground — keeps container alive)
# Single worker: avoids in-memory cache splits between workers.
# At <1K users one process handles the load fine; session cache stays consistent.
uvicorn src.api.main:app --host 0.0.0.0 --port $PORT --workers 1
