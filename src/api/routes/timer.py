"""GET /session/{user_id}/timer — live countdown timer page for a Seven 7 session."""

import asyncio
import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session as DBSession

from src.db.database import get_db
from src.db.models import Seven7Session, User
from src.agents.coach import CoachAgent
from src.agents.context import build_user_context

router = APIRouter()
coach = CoachAgent()


@router.get("/session/{user_id}/timer", response_class=HTMLResponse)
def timer_page(user_id: str, db: DBSession = Depends(get_db)):
    from datetime import datetime

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    session = (
        db.query(Seven7Session)
        .filter(Seven7Session.user_id == user_id, Seven7Session.generated_at >= today_start)
        .first()
    )

    if not session:
        ctx = build_user_context(user_id, db)
        data = asyncio.run(coach.generate(ctx, db))
    else:
        data = {
            "greeting": session.greeting,
            "session_title": session.session_title,
            "closing": session.closing,
            "blocks": session.blocks or [],
        }

    blocks_json = json.dumps(data["blocks"])
    title = data.get("session_title", "The Seven 7")
    greeting = data.get("greeting", "")
    closing = data.get("closing", "YU SHOW UP")
    name = user.name

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta property="og:title" content="Jerome7 — {name}'s Seven 7">
<meta property="og:description" content="{title}">
<title>Jerome7 — {title}</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    background: #0F1C2E;
    color: #fff;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    min-height: 100vh;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 24px;
  }}
  .brand {{ font-size: 13px; letter-spacing: 4px; color: #E85D04; text-transform: uppercase; margin-bottom: 8px; }}
  .title {{ font-size: 28px; font-weight: 700; text-align: center; margin-bottom: 6px; }}
  .greeting {{ font-size: 15px; color: #94a3b8; text-align: center; margin-bottom: 40px; }}

  .timer-ring {{ position: relative; width: 220px; height: 220px; margin: 0 auto 32px; }}
  svg {{ transform: rotate(-90deg); }}
  .ring-bg {{ fill: none; stroke: #1e3a5f; stroke-width: 10; }}
  .ring-progress {{ fill: none; stroke: #E85D04; stroke-width: 10; stroke-linecap: round;
    stroke-dasharray: 628; stroke-dashoffset: 0; transition: stroke-dashoffset 1s linear; }}
  .timer-center {{
    position: absolute; top: 50%; left: 50%;
    transform: translate(-50%, -50%);
    text-align: center;
  }}
  .timer-seconds {{ font-size: 52px; font-weight: 800; line-height: 1; }}
  .timer-label {{ font-size: 11px; color: #94a3b8; letter-spacing: 2px; margin-top: 4px; }}

  .block-name {{ font-size: 22px; font-weight: 700; text-align: center; margin-bottom: 8px; }}
  .block-instruction {{ font-size: 15px; color: #cbd5e1; text-align: center; max-width: 340px; line-height: 1.6; margin: 0 auto 8px; }}
  .block-why {{ font-size: 13px; color: #E85D04; text-align: center; font-style: italic; margin-bottom: 32px; }}

  .progress-dots {{ display: flex; gap: 8px; justify-content: center; margin-bottom: 32px; }}
  .dot {{ width: 10px; height: 10px; border-radius: 50%; background: #1e3a5f; transition: background 0.3s; }}
  .dot.active {{ background: #E85D04; }}
  .dot.done {{ background: #4a7fa5; }}

  .btn {{
    padding: 14px 36px; border-radius: 100px; border: none; cursor: pointer;
    font-size: 16px; font-weight: 700; letter-spacing: 1px; transition: all 0.2s;
  }}
  .btn-start {{ background: #E85D04; color: #fff; }}
  .btn-start:hover {{ background: #ff6b1a; }}
  .btn-skip {{ background: transparent; color: #94a3b8; border: 1px solid #1e3a5f; margin-left: 12px; }}
  .btn-skip:hover {{ color: #fff; }}

  .done-screen {{ display: none; text-align: center; }}
  .done-screen .big {{ font-size: 64px; margin-bottom: 16px; }}
  .done-title {{ font-size: 28px; font-weight: 800; margin-bottom: 8px; }}
  .done-closing {{ font-size: 16px; color: #94a3b8; margin-bottom: 32px; max-width: 320px; margin-left: auto; margin-right: auto; }}
  .share-btn {{
    background: #1e3a5f; color: #fff; padding: 12px 28px; border-radius: 100px;
    border: none; cursor: pointer; font-size: 14px; font-weight: 600;
  }}
  .share-btn:hover {{ background: #2a4f7a; }}
</style>
</head>
<body>

<div id="main">
  <div class="brand">Jerome7</div>
  <div class="title" id="session-title">{title}</div>
  <div class="greeting">{greeting}</div>

  <div class="timer-ring">
    <svg width="220" height="220" viewBox="0 0 220 220">
      <circle class="ring-bg" cx="110" cy="110" r="100"/>
      <circle class="ring-progress" id="ring" cx="110" cy="110" r="100"/>
    </svg>
    <div class="timer-center">
      <div class="timer-seconds" id="seconds">--</div>
      <div class="timer-label">SECONDS</div>
    </div>
  </div>

  <div class="block-name" id="block-name">Ready</div>
  <div class="block-instruction" id="block-instruction">Press start when you're ready.</div>
  <div class="block-why" id="block-why">&nbsp;</div>

  <div class="progress-dots" id="dots"></div>

  <div>
    <button class="btn btn-start" id="start-btn" onclick="startSession()">Start</button>
    <button class="btn btn-skip" id="skip-btn" onclick="skipBlock()" style="display:none">Skip</button>
  </div>
</div>

<div class="done-screen" id="done">
  <div class="big">◉</div>
  <div class="done-title">Session complete.</div>
  <div class="done-closing">{closing}</div>
  <button class="share-btn" onclick="shareSession()">Share your chain</button>
</div>

<script>
const blocks = {blocks_json};
let current = 0;
let remaining = 0;
let timer = null;
const CIRCUMFERENCE = 2 * Math.PI * 100;

function buildDots() {{
  const dots = document.getElementById('dots');
  dots.innerHTML = blocks.map((_, i) => `<div class="dot" id="dot-${{i}}"></div>`).join('');
}}

function updateRing(remaining, total) {{
  const frac = remaining / total;
  const offset = CIRCUMFERENCE * (1 - frac);
  document.getElementById('ring').style.strokeDashoffset = offset;
}}

function showBlock(i) {{
  const b = blocks[i];
  document.getElementById('block-name').textContent = b.name;
  document.getElementById('block-instruction').textContent = b.instruction;
  document.getElementById('block-why').textContent = b.why_today;
  document.getElementById('seconds').textContent = b.duration_seconds;
  remaining = b.duration_seconds;
  updateRing(remaining, b.duration_seconds);
  // dots
  document.querySelectorAll('.dot').forEach((d, j) => {{
    d.className = 'dot' + (j < i ? ' done' : j === i ? ' active' : '');
  }});
}}

function startSession() {{
  document.getElementById('start-btn').style.display = 'none';
  document.getElementById('skip-btn').style.display = 'inline-block';
  buildDots();
  showBlock(0);
  tick();
}}

function tick() {{
  timer = setInterval(() => {{
    remaining--;
    document.getElementById('seconds').textContent = remaining;
    updateRing(remaining, blocks[current].duration_seconds);
    if (remaining <= 0) {{
      clearInterval(timer);
      current++;
      if (current < blocks.length) {{
        showBlock(current);
        tick();
      }} else {{
        endSession();
      }}
    }}
  }}, 1000);
}}

function skipBlock() {{
  clearInterval(timer);
  current++;
  if (current < blocks.length) {{
    showBlock(current);
    tick();
  }} else {{
    endSession();
  }}
}}

function endSession() {{
  document.getElementById('main').style.display = 'none';
  document.getElementById('done').style.display = 'block';
}}

function shareSession() {{
  const text = "Just did my Seven 7 with Jerome7. 7 minutes. Showed up. YU SHOW UP — join me: https://github.com/odominguez7/Jerome7";
  if (navigator.share) {{
    navigator.share({{ text }});
  }} else {{
    navigator.clipboard.writeText(text).then(() => alert('Copied to clipboard!'));
  }}
}}

buildDots();
</script>
</body>
</html>"""
    return HTMLResponse(content=html)
