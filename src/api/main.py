"""FastAPI application — Jerome 7 / YU Show Up."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.db.database import init_db
from src.api.routes import pledge, log, seven7, streak, pod, health, streak_page, timer, daily, share, nudge, landing, leaderboard, analytics

app = FastAPI(
    title="Jerome 7 — YU Show Up",
    description="7 minutes a day. An act of love. A community of builders showing up.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(landing.router)
app.include_router(health.router)
app.include_router(pledge.router)
app.include_router(log.router)
app.include_router(seven7.router)
app.include_router(streak.router)
app.include_router(pod.router)
app.include_router(streak_page.router)
app.include_router(timer.router)
app.include_router(daily.router)
app.include_router(share.router)
app.include_router(nudge.router)
app.include_router(leaderboard.router)
app.include_router(analytics.router)


@app.on_event("startup")
def on_startup():
    init_db()
