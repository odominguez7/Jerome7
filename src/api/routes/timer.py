"""GET /timer — live countdown timer. One move at a time. No login required."""

import json
from datetime import datetime

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session as DBSession

from src.db.database import get_db
from src.agents.coach import CoachAgent

router = APIRouter()
coach = CoachAgent()

# Cache daily session for timer
_timer_cache: dict = {"date": None, "session": None}


@router.get("/timer", response_class=HTMLResponse)
async def timer_page():
    """Universal timer — no user ID needed. Uses today's daily session."""
    today = datetime.utcnow().strftime("%Y-%m-%d")

    if _timer_cache["date"] == today and _timer_cache["session"]:
        data = _timer_cache["session"]
    else:
        data = await coach.generate_daily()
        _timer_cache["date"] = today
        _timer_cache["session"] = data

    blocks_json = json.dumps(data.get("blocks", []))
    title = data.get("session_title", "the seven 7")

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
<title>Jerome7 — {title}</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700;800&display=swap');
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    background: #0d1117; color: #f0f6fc;
    font-family: 'JetBrains Mono', monospace;
    height: 100vh; display: flex; flex-direction: column;
    align-items: center; justify-content: center;
    overflow: hidden; padding: 20px;
  }}

  .brand {{ font-size: 11px; letter-spacing: 3px; color: #E85D04; margin-bottom: 6px; }}
  .session-title {{ font-size: 14px; color: #484f58; margin-bottom: 40px; }}

  .phase {{
    font-size: 10px; letter-spacing: 3px; color: #484f58;
    text-transform: uppercase; margin-bottom: 16px;
    transition: color 0.3s;
  }}
  .phase.prime {{ color: #7ee787; }}
  .phase.build {{ color: #E85D04; }}
  .phase.move {{ color: #f778ba; }}
  .phase.reset {{ color: #79c0ff; }}

  .countdown {{
    font-size: 120px; font-weight: 800; line-height: 1;
    margin-bottom: 8px; transition: color 0.3s;
  }}

  .block-name {{ font-size: 22px; font-weight: 700; margin-bottom: 12px; }}
  .block-instruction {{
    font-size: 14px; color: #8b949e; max-width: 300px;
    text-align: center; line-height: 1.5; margin-bottom: 40px;
  }}

  .progress-bar {{
    width: 100%; max-width: 300px; height: 4px;
    background: #21262d; border-radius: 2px; overflow: hidden;
    margin-bottom: 16px;
  }}
  .progress-fill {{
    height: 100%; background: #E85D04; border-radius: 2px;
    transition: width 1s linear;
  }}

  .dots {{ display: flex; gap: 8px; margin-bottom: 40px; }}
  .dot {{
    width: 8px; height: 8px; border-radius: 50%;
    background: #21262d; transition: all 0.3s;
  }}
  .dot.active {{ background: #E85D04; transform: scale(1.3); }}
  .dot.done {{ background: #484f58; }}

  .btn {{
    padding: 14px 40px; border-radius: 100px; border: none;
    cursor: pointer; font-family: inherit; font-size: 14px;
    font-weight: 700; letter-spacing: 1px;
  }}
  .btn-go {{ background: #E85D04; color: #fff; }}
  .btn-go:hover {{ background: #ff6b1a; }}
  .btn-skip {{
    position: fixed; bottom: 24px; right: 24px;
    background: transparent; color: #484f58; border: none;
    cursor: pointer; font-family: inherit; font-size: 11px;
    letter-spacing: 1px;
  }}
  .btn-skip:hover {{ color: #8b949e; }}

  .done {{ display: none; text-align: center; }}
  .done-mark {{ font-size: 48px; color: #E85D04; margin-bottom: 16px; }}
  .done-text {{ font-size: 16px; margin-bottom: 8px; }}
  .done-sub {{ font-size: 13px; color: #484f58; margin-bottom: 32px; }}
  .share-row {{ display: flex; gap: 12px; justify-content: center; flex-wrap: wrap; }}
  .share-btn {{
    padding: 10px 20px; border-radius: 8px; border: 1px solid #30363d;
    background: #161b22; color: #c9d1d9; cursor: pointer;
    font-family: inherit; font-size: 12px; font-weight: 600;
  }}
  .share-btn:hover {{ border-color: #E85D04; color: #E85D04; }}
  .share-btn.primary {{ background: #E85D04; color: #fff; border-color: #E85D04; }}

  @keyframes pulse {{ 0%,100% {{ opacity: 1; }} 50% {{ opacity: 0.7; }} }}
  .pulsing {{ animation: pulse 1s ease-in-out infinite; }}
</style>
</head>
<body>

<div id="main">
  <div class="brand">JEROME7</div>
  <div class="session-title">{title}</div>
  <div class="phase" id="phase">READY</div>
  <div class="countdown" id="countdown">7:00</div>
  <div class="block-name" id="block-name">ready when you are</div>
  <div class="block-instruction" id="instruction">tap start. 7 blocks. 60 seconds each.</div>
  <div class="progress-bar"><div class="progress-fill" id="progress"></div></div>
  <div class="dots" id="dots"></div>
  <button class="btn btn-go" id="start-btn" onclick="go()">START</button>
  <button class="btn-skip" id="skip-btn" onclick="skip()" style="display:none">skip ▸</button>
</div>

<div class="done" id="done">
  <div class="done-mark">◉</div>
  <div class="done-text">done.</div>
  <div class="done-sub">yu showed up.</div>
  <div class="share-row">
    <button class="share-btn primary" onclick="shareNative()">Share</button>
    <button class="share-btn" onclick="copyText()">Copy</button>
  </div>
</div>

<script>
const blocks = {blocks_json};
const TOTAL = 420;
let cur = 0, rem = 0, elapsed = 0, interval = null;
const PC = {{prime:'#7ee787', build:'#E85D04', move:'#f778ba', reset:'#79c0ff'}};

function init() {{
  document.getElementById('dots').innerHTML =
    blocks.map((_, i) => '<div class="dot" id="d'+i+'"></div>').join('');
}}

function show(i) {{
  const b = blocks[i], p = b.phase || 'build';
  document.getElementById('phase').textContent = p.toUpperCase();
  document.getElementById('phase').className = 'phase ' + p;
  document.getElementById('countdown').textContent = b.duration_seconds;
  document.getElementById('countdown').style.color = PC[p] || '#f0f6fc';
  document.getElementById('block-name').textContent = b.name;
  document.getElementById('instruction').textContent = b.instruction;
  rem = b.duration_seconds;
  blocks.forEach((_, j) => {{
    document.getElementById('d'+j).className =
      'dot' + (j<i?' done':j===i?' active':'');
  }});
}}

function go() {{
  document.getElementById('start-btn').style.display = 'none';
  document.getElementById('skip-btn').style.display = 'block';
  show(0); tick();
}}

function tick() {{
  interval = setInterval(() => {{
    rem--; elapsed++;
    document.getElementById('countdown').textContent = rem;
    document.getElementById('progress').style.width = (elapsed/TOTAL*100)+'%';
    if (rem<=3 && rem>0) document.getElementById('countdown').classList.add('pulsing');
    else document.getElementById('countdown').classList.remove('pulsing');
    if (rem<=0) {{
      cur++;
      if (cur<blocks.length) show(cur);
      else {{ clearInterval(interval); finish(); }}
    }}
  }}, 1000);
}}

function skip() {{
  elapsed += rem; cur++;
  if (cur<blocks.length) show(cur);
  else {{ clearInterval(interval); finish(); }}
}}

function finish() {{
  document.getElementById('main').style.display = 'none';
  document.getElementById('done').style.display = 'block';
}}

const SHARE = "◉ Day complete.\\n\\n🟧🟧🟧🟧🟧🟧🟧\\n\\nJerome7 — 7 min/day\\nhttps://github.com/odominguez7/Jerome7";
function shareNative() {{
  if (navigator.share) navigator.share({{text: SHARE}});
  else copyText();
}}
function copyText() {{
  navigator.clipboard.writeText(SHARE).then(() => {{
    document.querySelector('.share-btn:last-child').textContent = 'copied ✓';
  }});
}}
init();
</script>
</body>
</html>"""
    return HTMLResponse(content=html)
