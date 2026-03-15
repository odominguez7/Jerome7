"""GET /timer — live countdown timer. One move at a time. No login required."""

import json
from datetime import datetime

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

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

  .card-preview {{
    background: #0f1419; border: 1px solid #30363d; border-radius: 12px;
    padding: 20px 24px; margin: 24px auto 0; max-width: 320px;
    text-align: left; font-size: 13px; line-height: 1.7;
    white-space: pre-line; color: #c9d1d9;
  }}
  .card-preview .card-header {{
    color: #E85D04; font-weight: 700; font-size: 14px;
  }}
  .card-preview .card-divider {{ color: #30363d; }}
  .card-preview .card-exercise {{ color: #c9d1d9; }}
  .card-preview .card-footer {{
    color: #484f58; font-size: 12px;
  }}
  .card-preview .card-site {{
    color: #E85D04; font-size: 12px; font-weight: 600;
  }}

  .share-section {{ margin-top: 20px; }}
  .share-section .share-row {{ margin-bottom: 12px; }}
  .view-card-link {{
    display: inline-block; margin-top: 8px;
    color: #484f58; font-size: 11px; text-decoration: none;
    letter-spacing: 1px; transition: color 0.2s;
  }}
  .view-card-link:hover {{ color: #E85D04; }}
  .copied-toast {{
    display: none; color: #7ee787; font-size: 11px;
    margin-top: 6px; letter-spacing: 1px;
  }}

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
  <div class="card-preview" id="card-preview"></div>
  <div class="share-section">
    <div class="share-row">
      <button class="share-btn primary" onclick="copyCard()">Copy to Clipboard</button>
      <button class="share-btn" onclick="shareTwitter()">Share on Twitter</button>
    </div>
    <div class="share-row">
      <button class="share-btn" onclick="shareNative()">Share</button>
    </div>
    <div class="copied-toast" id="copied-toast">copied to clipboard ✓</div>
    <a class="view-card-link" id="view-card-link" href="/card/" target="_blank">VIEW YOUR CARD ▸</a>
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

function getStreakDay() {{
  // Priority: URL param > localStorage streak
  const urlDay = new URLSearchParams(window.location.search).get('day');
  if (urlDay) return urlDay;
  // localStorage streak tracking
  const data = JSON.parse(localStorage.getItem('jerome7_streak') || '{{}}'  );
  return data.day || 1;
}}

function recordSessionComplete() {{
  const today = new Date().toISOString().slice(0, 10);
  const data = JSON.parse(localStorage.getItem('jerome7_streak') || '{{}}');
  const lastDate = data.lastDate || '';
  if (lastDate === today) return; // already logged today

  // Check if yesterday was logged (chain continues) or gap (chain breaks after 3 misses)
  let day = data.day || 0;
  if (lastDate) {{
    const last = new Date(lastDate);
    const now = new Date(today);
    const diffDays = Math.floor((now - last) / 86400000);
    if (diffDays <= 3) {{
      day++; // chain continues
    }} else {{
      day = 1; // chain broke, restart
    }}
  }} else {{
    day = 1; // first session
  }}

  localStorage.setItem('jerome7_streak', JSON.stringify({{
    day: day,
    lastDate: today,
    totalSessions: (data.totalSessions || 0) + 1,
  }}));
}}

function buildCardText() {{
  const dayNum = getStreakDay();
  const sep = '━━━━━━━━━━━━━━━━━';
  const exercises = blocks.map(b => '🟧 ' + b.name).join('\\n');
  return 'JEROME7 \\u00b7 Day ' + dayNum + ' \\ud83d\\udd25\\n'
    + sep + '\\n'
    + exercises + '\\n'
    + sep + '\\n'
    + dayNum + '-day chain \\ud83d\\udd17 unbroken\\n'
    + 'jerome7.com';
}}

function renderCardPreview() {{
  const dayNum = getStreakDay();
  const sep = '━━━━━━━━━━━━━━━━━';
  const header = '<span class="card-header">JEROME7 \\u00b7 Day ' + dayNum + ' \\ud83d\\udd25</span>';
  const divider = '<span class="card-divider">' + sep + '</span>';
  const exercises = blocks.map(b => '<span class="card-exercise">\\ud83d\\udfe7 ' + b.name + '</span>').join('\\n');
  const footer = '<span class="card-footer">' + dayNum + '-day chain \\ud83d\\udd17 unbroken</span>';
  const site = '<span class="card-site">jerome7.com</span>';
  document.getElementById('card-preview').innerHTML =
    header + '\\n' + divider + '\\n' + exercises + '\\n' + divider + '\\n' + footer + '\\n' + site;
}}

function finish() {{
  recordSessionComplete();
  document.getElementById('main').style.display = 'none';
  document.getElementById('done').style.display = 'block';
  renderCardPreview();
  const uid = new URLSearchParams(window.location.search).get('user_id');
  if (uid) document.getElementById('view-card-link').href = '/card/' + uid;
  else document.getElementById('view-card-link').style.display = 'none';
}}

function copyCard() {{
  const text = buildCardText();
  navigator.clipboard.writeText(text).then(() => {{
    const toast = document.getElementById('copied-toast');
    toast.style.display = 'block';
    setTimeout(() => {{ toast.style.display = 'none'; }}, 2000);
  }});
}}

function shareTwitter() {{
  const text = buildCardText();
  const url = 'https://twitter.com/intent/tweet?text=' + encodeURIComponent(text);
  window.open(url, '_blank');
}}

function shareNative() {{
  const text = buildCardText();
  if (navigator.share) navigator.share({{text: text}});
  else copyCard();
}}
init();
</script>
</body>
</html>"""
    return HTMLResponse(content=html)
