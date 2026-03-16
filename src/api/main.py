"""FastAPI application — Jerome 7 / YU Show Up."""

import logging
import os
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from src.db.database import init_db
from src.api.routes import pledge, log, seven7, streak, pod, health, streak_page, timer, daily, share, share_card, nudge, landing, leaderboard, analytics, analytics_page, live, twitter, twin, invite, voice, embed, session_card, coach_chat, agents_observatory, world_report, milestones, mesh_api, tokens, globe, sponsor, onboarding, agentcard, milestone_card, social_share, stats
from src.api.routes import legal, subscribe

# ── Structured logging ────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("jerome7")

_IS_PROD = bool(os.getenv("RAILWAY_ENVIRONMENT"))


# ── Lifespan (replaces deprecated @app.on_event) ─────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    logger.info("Jerome7 started — DB initialized")

    # Pre-warm today's session cache so the first visitor doesn't wait ~25s for Gemini
    try:
        from src.api.routes.timer import _cache as timer_cache, coach
        from src.agents.session_types import today_session_type
        from datetime import datetime, timezone

        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if timer_cache.get("date") != today or not timer_cache.get("session"):
            session_type = today_session_type()
            try:
                data = await coach.generate_wellness(session_type)
            except Exception:
                data = await coach.generate_daily()
            timer_cache["date"] = today
            timer_cache["session"] = data
            logger.info("Session cache pre-warmed for %s (%s)", today, session_type)
    except Exception:
        logger.warning("Failed to pre-warm session cache — first visitor will trigger generation")

    yield
    logger.info("Jerome7 shutting down")


app = FastAPI(
    title="Jerome 7 — YU Show Up",
    description="7 minutes a day. An act of love. A community of builders showing up.",
    version="0.1.0",
    lifespan=lifespan,
    docs_url=None if _IS_PROD else "/docs",
    redoc_url=None if _IS_PROD else "/redoc",
    openapi_url=None if _IS_PROD else "/openapi.json",
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


# ── Security headers + request logging ────────────────────────────────────────
@app.middleware("http")
async def security_and_logging(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    ms = round((time.time() - start) * 1000)

    # Log slow requests and errors
    if ms > 500 or response.status_code >= 400:
        logger.info(
            "%s %s %s %dms",
            request.method, request.url.path, response.status_code, ms,
        )

    # Security headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(self), geolocation=()"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://plausible.io https://cdn.jsdelivr.net; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data: blob:; "
        "connect-src 'self' https://plausible.io https://api.elevenlabs.io; "
        "media-src 'self' blob:; "
        "worker-src 'self' blob:"
    )
    if _IS_PROD:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

    return response


# ── Root-level static files ───────────────────────────────────────────────────
@app.get("/robots.txt", include_in_schema=False)
async def robots_txt():
    return FileResponse("static/robots.txt", media_type="text/plain")


@app.get("/sitemap.xml", include_in_schema=False)
async def sitemap_xml():
    return FileResponse("static/sitemap.xml", media_type="application/xml")


# ── Static files ──────────────────────────────────────────────────────────────
app.mount("/static", StaticFiles(directory="static"), name="static")


# ── Custom 404 ────────────────────────────────────────────────────────────────
@app.exception_handler(404)
async def custom_404(request: Request, exc):
    accept = request.headers.get("accept", "")
    if request.url.path.startswith("/api/") or "application/json" in accept:
        return JSONResponse(status_code=404, content={"error": "Not found"})
    return HTMLResponse(
        status_code=404,
        content="""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="theme-color" content="#0d1117">
<link rel="icon" type="image/svg+xml" href="/static/favicon.svg">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700;800&display=swap">
<title>Jerome7 — 404</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: #0d1117; color: #c9d1d9; font-family: 'JetBrains Mono', monospace;
         min-height: 100vh; display: flex; align-items: center; justify-content: center; }
  .c { text-align: center; }
  h1 { font-size: 4rem; color: #E85D04; }
  p { color: #484f58; margin: 16px 0; font-size: 0.9rem; }
  a { color: #E85D04; text-decoration: none; font-weight: 700; font-size: 1.1rem; }
  a:hover { text-decoration: underline; }
</style>
</head><body>
<div class="c">
  <h1>404</h1>
  <p>This page doesn't exist. But you do.</p>
  <a href="/timer">START YOUR 7 MINUTES &rarr;</a>
</div>
</body></html>""",
    )


# ── Custom 500 ────────────────────────────────────────────────────────────────
@app.exception_handler(500)
async def custom_500(request: Request, exc):
    accept = request.headers.get("accept", "")
    if request.url.path.startswith("/api/") or "application/json" in accept:
        return JSONResponse(status_code=500, content={"error": "Internal server error"})
    return HTMLResponse(
        status_code=500,
        content="""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="theme-color" content="#0d1117">
<link rel="icon" type="image/svg+xml" href="/static/favicon.svg">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700;800&display=swap">
<title>Jerome7 — 500</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: #0d1117; color: #c9d1d9; font-family: 'JetBrains Mono', monospace;
         min-height: 100vh; display: flex; align-items: center; justify-content: center; }
  .c { text-align: center; }
  h1 { font-size: 4rem; color: #E85D04; }
  p { color: #484f58; margin: 16px 0; font-size: 0.9rem; }
  a { color: #E85D04; text-decoration: none; font-weight: 700; font-size: 1.1rem; }
  a:hover { text-decoration: underline; }
</style>
</head><body>
<div class="c">
  <h1>500</h1>
  <p>Something went wrong. We're on it.</p>
  <a href="/">BACK TO HOME &rarr;</a>
</div>
</body></html>""",
    )


# ── Routes ────────────────────────────────────────────────────────────────────
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
app.include_router(legal.router)
app.include_router(subscribe.router)
