"""GET /api/embed — embeddable session endpoint for third-party apps.

Any app can fetch today's session and embed it. No API key needed.
Returns a clean, minimal JSON payload designed for embedding.
"""

from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session as DBSession
from sqlalchemy import func

from src.db.database import get_db
from src.db.models import User, Streak, Session as SessionModel
from src.api.routes.daily import get_daily

router = APIRouter()


@router.get("/api/embed/session")
async def embed_session(db: DBSession = Depends(get_db)):
    """Today's session in a clean format for embedding in any app.

    Returns minimal payload — blocks, title, total time.
    No authentication required. Free forever.
    """
    session = await get_daily(db)
    blocks = session.get("blocks", [])

    return {
        "version": "1.0",
        "date": datetime.utcnow().strftime("%Y-%m-%d"),
        "session_title": session.get("session_title", "the seven 7"),
        "total_seconds": sum(b.get("duration_seconds", 60) for b in blocks),
        "total_blocks": len(blocks),
        "blocks": [
            {
                "name": b.get("name"),
                "instruction": b.get("instruction"),
                "duration_seconds": b.get("duration_seconds", 60),
                "phase": b.get("phase", "build"),
            }
            for b in blocks
        ],
        "closing": session.get("closing", "You showed up."),
        "attribution": {
            "name": "Jerome7",
            "url": "https://jerome7.com",
            "github": "https://github.com/odominguez7/Jerome7",
            "license": "MIT",
        },
    }


@router.get("/api/embed/stats")
def embed_stats(db: DBSession = Depends(get_db)):
    """Community stats for embedding — show Jerome7 social proof in your app."""
    total_users = db.query(User).count()
    total_sessions = db.query(SessionModel).count()
    active_streaks = db.query(Streak).filter(Streak.current_streak > 0).count()
    countries = (
        db.query(func.count(func.distinct(User.country)))
        .filter(User.country.isnot(None))
        .scalar()
    )

    return {
        "version": "1.0",
        "total_builders": total_users,
        "total_sessions": total_sessions,
        "active_streaks": active_streaks,
        "countries": countries,
        "minutes_moved": total_sessions * 7,
        "attribution": {
            "name": "Jerome7",
            "url": "https://jerome7.com",
        },
    }


@router.get("/api/embed/widget")
def embed_widget():
    """HTML snippet that apps can iframe or inject.

    Returns a self-contained HTML widget showing today's session title
    and a "Start" button linking to jerome7.com/timer.
    """
    from fastapi.responses import HTMLResponse

    html = """<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: -apple-system, 'Segoe UI', monospace;
    background: #0d1117; color: #c9d1d9;
  }
  .widget {
    padding: 20px; text-align: center;
    border: 1px solid #21262d; border-radius: 8px;
    max-width: 320px; margin: 0 auto;
  }
  .brand { font-size: 10px; letter-spacing: 3px; color: #E85D04; font-weight: 700; margin-bottom: 12px; }
  .title { font-size: 16px; font-weight: 700; color: #f0f6fc; margin-bottom: 4px; }
  .sub { font-size: 11px; color: #484f58; margin-bottom: 16px; }
  .btn {
    display: inline-block; padding: 10px 28px;
    background: #E85D04; color: #fff; font-weight: 700;
    font-size: 11px; letter-spacing: 2px; text-decoration: none;
    border-radius: 4px;
  }
  .btn:hover { background: #c24e03; }
  .footer { font-size: 9px; color: #21262d; margin-top: 12px; }
  .footer a { color: #484f58; text-decoration: none; }
</style>
</head>
<body>
<div class="widget">
  <div class="brand">JEROME7</div>
  <div class="title" id="title">Loading...</div>
  <div class="sub">7 blocks · 60s each · same for everyone</div>
  <a href="https://jerome7.com/timer" target="_blank" class="btn">START</a>
  <div class="footer"><a href="https://jerome7.com" target="_blank">jerome7.com</a> · free forever</div>
</div>
<script>
  fetch('https://jerome7.com/api/embed/session')
    .then(r => r.json())
    .then(d => { document.getElementById('title').textContent = d.session_title.toUpperCase(); })
    .catch(() => { document.getElementById('title').textContent = 'THE SEVEN 7'; });
</script>
</body>
</html>"""

    return HTMLResponse(content=html, headers={
        "Access-Control-Allow-Origin": "*",
        "Cache-Control": "public, max-age=3600",
    })
