"""GET /api/embed — embeddable session endpoint for third-party apps.

Any app can fetch today's session and embed it. No API key needed.
Returns a clean, minimal JSON payload designed for embedding.

Also serves SVG streak badges and a JavaScript embed widget.
"""

from datetime import datetime, timezone
from html import escape

from fastapi import APIRouter, Depends
from fastapi.responses import Response, HTMLResponse, PlainTextResponse
from sqlalchemy.orm import Session as DBSession
from sqlalchemy import func

from src.db.database import get_db
from src.db.models import User, Streak, Session as SessionModel
from src.api.routes.daily import get_daily

router = APIRouter()


# ---------------------------------------------------------------------------
# Existing endpoints
# ---------------------------------------------------------------------------

@router.get("/api/embed/session")
async def embed_session(db: DBSession = Depends(get_db)):
    """Today's session in a clean format for embedding in any app.

    Returns minimal payload — blocks, title, total time.
    No authentication required. Open source.
    """
    session = await get_daily()
    blocks = session.get("blocks", [])

    return {
        "version": "1.0",
        "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
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
def embed_stats_json(db: DBSession = Depends(get_db)):
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
  <a href="https://jerome7.com/timer" target="_blank" rel="noopener noreferrer" class="btn">START</a>
  <div class="footer"><a href="https://jerome7.com" target="_blank" rel="noopener noreferrer">jerome7.com</a> · open source</div>
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


# ---------------------------------------------------------------------------
# SVG badge helpers
# ---------------------------------------------------------------------------

def _shield_svg(label: str, value: str, color: str = "#e8713a") -> str:
    """Generate a shields.io-style SVG badge."""
    label_width = len(label) * 6.5 + 12
    value_width = len(value) * 6.5 + 12
    total_width = label_width + value_width

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{total_width}" height="20" role="img" aria-label="{escape(label)}: {escape(value)}">
  <title>{escape(label)}: {escape(value)}</title>
  <linearGradient id="s" x2="0" y2="100%">
    <stop offset="0" stop-color="#bbb" stop-opacity=".1"/>
    <stop offset="1" stop-opacity=".1"/>
  </linearGradient>
  <clipPath id="r">
    <rect width="{total_width}" height="20" rx="3" fill="#fff"/>
  </clipPath>
  <g clip-path="url(#r)">
    <rect width="{label_width}" height="20" fill="#555"/>
    <rect x="{label_width}" width="{value_width}" height="20" fill="{color}"/>
    <rect width="{total_width}" height="20" fill="url(#s)"/>
  </g>
  <g fill="#fff" text-anchor="middle" font-family="Verdana,Geneva,DejaVu Sans,sans-serif" text-rendering="geometricPrecision" font-size="11">
    <text aria-hidden="true" x="{label_width / 2}" y="15" fill="#010101" fill-opacity=".3">{escape(label)}</text>
    <text x="{label_width / 2}" y="14" fill="#fff">{escape(label)}</text>
    <text aria-hidden="true" x="{label_width + value_width / 2}" y="15" fill="#010101" fill-opacity=".3">{escape(value)}</text>
    <text x="{label_width + value_width / 2}" y="14" fill="#fff">{escape(value)}</text>
  </g>
</svg>"""


# ---------------------------------------------------------------------------
# 1. GET /embed/badge/{user_id} — SVG streak badge
# ---------------------------------------------------------------------------

@router.get("/embed/badge/{user_id}")
def embed_badge(user_id: str, db: DBSession = Depends(get_db)):
    """SVG streak badge for a user (shields.io style).

    Usage in markdown:
        ![Jerome7 Streak](https://jerome7.com/embed/badge/omar)
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        svg = _shield_svg("Jerome7", "user not found", color="#999")
        return Response(content=svg, media_type="image/svg+xml", headers={
            "Cache-Control": "no-cache",
        })

    streak_row = db.query(Streak).filter(Streak.user_id == user_id).first()
    current = streak_row.current_streak if streak_row else 0

    if current == 0:
        value = "Day 0"
    else:
        value = f"Day {current} \U0001f525"

    svg = _shield_svg("Jerome7", value)
    return Response(content=svg, media_type="image/svg+xml", headers={
        "Cache-Control": "public, max-age=3600",
        "Access-Control-Allow-Origin": "*",
    })


# ---------------------------------------------------------------------------
# 2. GET /embed/badge/{user_id}/markdown — markdown snippet
# ---------------------------------------------------------------------------

@router.get("/api/badge/{jerome_number}.svg")
def badge_by_jerome_number(jerome_number: int, db: DBSession = Depends(get_db)):
    """SVG streak badge by Jerome# number (real-time).

    Usage in markdown:
        ![Jerome42](https://jerome7.com/api/badge/42.svg)
    """
    user = db.query(User).filter(User.jerome_number == jerome_number).first()
    if not user:
        svg = _shield_svg(f"Jerome{jerome_number}", "not found", color="#999")
        return Response(content=svg, media_type="image/svg+xml", headers={
            "Cache-Control": "no-cache",
        })

    streak_row = db.query(Streak).filter(Streak.user_id == user.id).first()
    current = streak_row.current_streak if streak_row else 0

    label = f"Jerome{jerome_number}"
    if current == 0:
        value = "Day 0"
    else:
        value = f"Day {current} \U0001f525"

    svg = _shield_svg(label, value)
    return Response(content=svg, media_type="image/svg+xml", headers={
        "Cache-Control": "public, max-age=3600",
        "Access-Control-Allow-Origin": "*",
    })


@router.get("/embed/badge/{user_id}/markdown")
def embed_badge_markdown(user_id: str):
    """Return a copy-paste markdown snippet for the streak badge."""
    snippet = f"![Jerome7 Streak](https://jerome7.com/embed/badge/{escape(user_id)})"
    return PlainTextResponse(content=snippet, headers={
        "Access-Control-Allow-Origin": "*",
    })


# ---------------------------------------------------------------------------
# 3. GET /embed/stats/badge — SVG community stats badge
# ---------------------------------------------------------------------------

@router.get("/embed/stats/badge")
def embed_stats_badge(db: DBSession = Depends(get_db)):
    """SVG badge showing community stats."""
    total_users = db.query(User).count()
    countries = (
        db.query(func.count(func.distinct(User.country)))
        .filter(User.country.isnot(None))
        .scalar()
    ) or 0

    value = f"{total_users} builders \u00b7 {countries} countries"
    svg = _shield_svg("Jerome7", value)
    return Response(content=svg, media_type="image/svg+xml", headers={
        "Cache-Control": "public, max-age=3600",
        "Access-Control-Allow-Origin": "*",
    })


# ---------------------------------------------------------------------------
# 4. GET /embed/widget.js — JavaScript embed widget
# ---------------------------------------------------------------------------

_WIDGET_JS = """
(function() {
  var script = document.currentScript;
  var userId = script.getAttribute('data-user-id');
  if (!userId) { console.warn('Jerome7 widget: missing data-user-id'); return; }

  var BASE = 'https://jerome7.com';

  var container = document.createElement('div');
  container.id = 'jerome7-widget-' + userId;
  script.parentNode.insertBefore(container, script.nextSibling);

  var shadow = container.attachShadow
    ? container.attachShadow({ mode: 'open' })
    : container;

  var style = document.createElement('style');
  style.textContent = [
    ':host { display: block; width: 300px; font-family: -apple-system, "Segoe UI", Roboto, monospace; }',
    '.j7-card { background: #0d1117; border: 1px solid #21262d; border-radius: 10px; padding: 20px; color: #c9d1d9; width: 300px; box-sizing: border-box; }',
    '.j7-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 14px; }',
    '.j7-brand { font-size: 10px; letter-spacing: 3px; color: #e8713a; font-weight: 700; text-transform: uppercase; }',
    '.j7-streak { font-size: 28px; font-weight: 800; color: #f0f6fc; margin-bottom: 2px; }',
    '.j7-label { font-size: 11px; color: #484f58; margin-bottom: 16px; }',
    '.j7-bar { height: 4px; background: #21262d; border-radius: 2px; overflow: hidden; margin-bottom: 16px; }',
    '.j7-bar-fill { height: 100%; background: #e8713a; border-radius: 2px; transition: width 0.6s ease; }',
    '.j7-sessions { font-size: 11px; color: #484f58; margin-bottom: 14px; }',
    '.j7-cta { display: block; text-align: center; padding: 10px; background: #e8713a; color: #fff; font-weight: 700; font-size: 11px; letter-spacing: 2px; text-decoration: none; border-radius: 4px; margin-bottom: 12px; }',
    '.j7-cta:hover { background: #c24e03; }',
    '.j7-footer { font-size: 9px; color: #484f58; text-align: center; }',
    '.j7-footer a { color: #6e7681; text-decoration: none; }',
    '.j7-footer a:hover { color: #c9d1d9; }',
  ].join('\\n');

  shadow.appendChild(style);

  var card = document.createElement('div');
  card.className = 'j7-card';
  card.innerHTML = [
    '<div class="j7-header"><span class="j7-brand">JEROME7</span></div>',
    '<div class="j7-streak" id="j7-streak">--</div>',
    '<div class="j7-label">day streak</div>',
    '<div class="j7-bar"><div class="j7-bar-fill" id="j7-bar" style="width:0%"></div></div>',
    '<div class="j7-sessions" id="j7-sessions"></div>',
    '<a class="j7-cta" href="' + BASE + '/timer" target="_blank" rel="noopener noreferrer">START TODAY\\'S SESSION</a>',
    '<div class="j7-footer">Powered by <a href="' + BASE + '" target="_blank" rel="noopener noreferrer">Jerome7</a></div>',
  ].join('');

  shadow.appendChild(card);

  // Fetch user streak data
  fetch(BASE + '/api/streak/' + encodeURIComponent(userId))
    .then(function(r) { return r.json(); })
    .then(function(d) {
      var streak = d.current_streak || 0;
      var total = d.total_sessions || 0;
      var longest = d.longest_streak || 0;

      var streakEl = shadow.getElementById('j7-streak');
      var barEl = shadow.getElementById('j7-bar');
      var sessionsEl = shadow.getElementById('j7-sessions');

      if (streakEl) streakEl.textContent = streak;
      if (barEl) barEl.style.width = Math.min((streak / Math.max(longest, 7)) * 100, 100) + '%';
      if (sessionsEl) sessionsEl.textContent = total + ' total sessions \\u00b7 ' + longest + ' day best';
    })
    .catch(function() {
      var streakEl = shadow.getElementById('j7-streak');
      if (streakEl) streakEl.textContent = '0';
    });
})();
""".strip()


@router.get("/embed/widget.js")
def embed_widget_js():
    """Self-contained JavaScript widget.

    Usage:
        <script src="https://jerome7.com/embed/widget.js" data-user-id="omar"></script>
    """
    return Response(
        content=_WIDGET_JS,
        media_type="application/javascript",
        headers={
            "Cache-Control": "public, max-age=3600",
            "Access-Control-Allow-Origin": "*",
        },
    )


# ---------------------------------------------------------------------------
# 5. GET /embed — HTML documentation page
# ---------------------------------------------------------------------------

@router.get("/embed")
def embed_docs_page():
    """Documentation page showing how to use Jerome7 badges and widgets."""
    html = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Jerome7 — Embeddable Widgets</title>
<meta name="robots" content="noindex, nofollow">
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: -apple-system, 'Segoe UI', Roboto, monospace;
    background: #0d1117; color: #c9d1d9;
    line-height: 1.6; padding: 40px 20px;
  }
  .container { max-width: 720px; margin: 0 auto; }
  h1 { color: #f0f6fc; font-size: 28px; margin-bottom: 8px; }
  .subtitle { color: #e8713a; font-size: 12px; letter-spacing: 3px; font-weight: 700; margin-bottom: 32px; }
  h2 { color: #f0f6fc; font-size: 18px; margin: 32px 0 12px; padding-top: 24px; border-top: 1px solid #21262d; }
  h2:first-of-type { border-top: none; padding-top: 0; }
  p { margin-bottom: 12px; font-size: 14px; }
  .badge-preview { margin: 16px 0; }
  .badge-preview img { height: 20px; }
  .code-block {
    position: relative; background: #161b22; border: 1px solid #21262d;
    border-radius: 6px; padding: 16px; margin: 12px 0 20px;
    font-family: 'SFMono-Regular', Consolas, monospace; font-size: 13px;
    color: #79c0ff; overflow-x: auto; white-space: pre-wrap; word-break: break-all;
  }
  .copy-btn {
    position: absolute; top: 8px; right: 8px;
    background: #21262d; border: 1px solid #30363d; color: #c9d1d9;
    padding: 4px 10px; border-radius: 4px; cursor: pointer;
    font-size: 11px; font-family: inherit;
  }
  .copy-btn:hover { background: #30363d; }
  .copy-btn.copied { color: #e8713a; }
  .section-icon { margin-right: 6px; }
  a { color: #e8713a; text-decoration: none; }
  a:hover { text-decoration: underline; }
  .footer { margin-top: 48px; padding-top: 24px; border-top: 1px solid #21262d; font-size: 11px; color: #484f58; text-align: center; }
  .footer a { color: #6e7681; }
</style>
</head>
<body>
<div class="container">
  <div class="subtitle">EMBEDDABLE WIDGETS</div>
  <h1>Jerome7 Badges &amp; Widgets</h1>
  <p>Show your streak anywhere. Free, no API key needed.</p>

  <!-- GitHub README -->
  <h2><span class="section-icon">&#128218;</span> Add to your GitHub README</h2>
  <p>Drop this markdown into your README to show your live streak badge:</p>
  <div class="badge-preview">
    <img src="/embed/badge/YOUR_USER_ID" alt="Jerome7 badge preview">
  </div>
  <div class="code-block" id="code-readme">![Jerome7 Streak](https://jerome7.com/embed/badge/YOUR_USER_ID)<button class="copy-btn" onclick="copyCode('code-readme')">Copy</button></div>
  <p>Replace <code>YOUR_USER_ID</code> with your Jerome7 user ID.</p>

  <!-- Community badge -->
  <h2><span class="section-icon">&#127758;</span> Community Stats Badge</h2>
  <p>Show how many builders are moving with Jerome7:</p>
  <div class="badge-preview">
    <img src="/embed/stats/badge" alt="Jerome7 community badge preview">
  </div>
  <div class="code-block" id="code-community">![Jerome7 Community](https://jerome7.com/embed/stats/badge)<button class="copy-btn" onclick="copyCode('code-community')">Copy</button></div>

  <!-- Website widget -->
  <h2><span class="section-icon">&#127760;</span> Add to your Website</h2>
  <p>Embed a live streak card on any webpage. Self-contained, dark theme, no external CSS.</p>
  <div class="code-block" id="code-widget">&lt;script src="https://jerome7.com/embed/widget.js" data-user-id="YOUR_USER_ID"&gt;&lt;/script&gt;<button class="copy-btn" onclick="copyCode('code-widget')">Copy</button></div>
  <p>The widget renders a 300px card showing your current streak, total sessions, and a link to start today's session.</p>

  <!-- Blog / HTML badge -->
  <h2><span class="section-icon">&#9997;&#65039;</span> Add to your Blog</h2>
  <p>Use an HTML image tag for full control over sizing and placement:</p>
  <div class="code-block" id="code-blog">&lt;a href="https://jerome7.com"&gt;&lt;img src="https://jerome7.com/embed/badge/YOUR_USER_ID" alt="Jerome7 Streak"&gt;&lt;/a&gt;<button class="copy-btn" onclick="copyCode('code-blog')">Copy</button></div>

  <!-- API endpoints -->
  <h2><span class="section-icon">&#128268;</span> API Endpoints</h2>
  <p>All endpoints are public. No authentication required.</p>
  <div class="code-block" id="code-api">GET /embed/badge/{user_id}          SVG streak badge
GET /embed/badge/{user_id}/markdown  Markdown snippet
GET /embed/stats/badge               SVG community stats badge
GET /embed/widget.js                 JavaScript embed widget
GET /api/embed/session               JSON session data
GET /api/embed/stats                 JSON community stats<button class="copy-btn" onclick="copyCode('code-api')">Copy</button></div>

  <div class="footer">
    <a href="https://jerome7.com">Jerome7</a> &mdash; 7 minutes a day. Personally funded. Open source.
  </div>
</div>

<script>
function copyCode(id) {
  var block = document.getElementById(id);
  var btn = block.querySelector('.copy-btn');
  var text = block.textContent.replace('Copy', '').replace('Copied', '').trim();
  navigator.clipboard.writeText(text).then(function() {
    btn.textContent = 'Copied';
    btn.classList.add('copied');
    setTimeout(function() { btn.textContent = 'Copy'; btn.classList.remove('copied'); }, 2000);
  });
}
</script>
</body>
</html>"""

    return HTMLResponse(content=html, headers={
        "Cache-Control": "public, max-age=3600",
    })
