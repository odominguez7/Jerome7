"""FastAPI application — Jerome 7 / YU Show Up."""

import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from src.db.database import init_db
from src.api.routes import pledge, log, seven7, streak, pod, health, streak_page, timer, daily, share, share_card, nudge, landing, leaderboard, analytics, analytics_page, live, twitter, twin, invite, voice, embed, session_card, coach_chat, agents_observatory, world_report, milestones, mesh_api, tokens, globe, sponsor, onboarding, agentcard, milestone_card, social_share, stats

# ── Structured logging ────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("jerome7")


# ── Lifespan (replaces deprecated @app.on_event) ─────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    logger.info("Jerome7 started — DB initialized")
    yield
    logger.info("Jerome7 shutting down")


app = FastAPI(
    title="Jerome 7 — YU Show Up",
    description="7 minutes a day. An act of love. A community of builders showing up.",
    version="0.1.0",
    lifespan=lifespan,
)

_ALLOWED_ORIGINS = [
    "https://jerome7.com",
    "https://www.jerome7.com",
    "https://api.jerome7.com",
    "http://localhost:3000",
    "http://localhost:8000",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:8000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request logging middleware ────────────────────────────────────────────────
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    ms = round((time.time() - start) * 1000)
    if ms > 500 or response.status_code >= 400:
        logger.info(
            "%s %s %s %dms",
            request.method, request.url.path, response.status_code, ms,
        )
    return response


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
app.include_router(tokens.router)
app.include_router(globe.router)
app.include_router(sponsor.router)
app.include_router(onboarding.router)
app.include_router(agentcard.router)
app.include_router(milestone_card.router)
app.include_router(social_share.router)
app.include_router(stats.router)
