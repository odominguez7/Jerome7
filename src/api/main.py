"""FastAPI application — Jerome 7 / YU Show Up."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.db.database import init_db
from src.api.routes import pledge, log, seven7, streak, pod, health, streak_page, timer, daily, share, share_card, nudge, landing, leaderboard, analytics, analytics_page, live, twitter, twin, invite, voice, embed, session_card, coach_chat, agents_observatory, world_report, milestones, mesh_api

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
app.include_router(share_card.router)
app.include_router(share.router)
app.include_router(nudge.router)
app.include_router(leaderboard.router)
app.include_router(analytics.router)
app.include_router(analytics_page.router)
app.include_router(live.router)
app.include_router(twitter.router)
app.include_router(twin.router)
app.include_router(invite.router)
app.include_router(voice.router)
app.include_router(embed.router)
app.include_router(session_card.router)
app.include_router(coach_chat.router)
app.include_router(agents_observatory.router)
app.include_router(world_report.router)
app.include_router(milestones.router)
app.include_router(mesh_api.router)


@app.on_event("startup")
def on_startup():
    init_db()
