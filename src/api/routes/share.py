"""GET /share/{user_id} — shareable streak card. Terminal aesthetic. Screenshotable."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session as DBSession

from src.db.database import get_db
from src.db.models import User, Streak

router = APIRouter()

DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


@router.get("/share/{user_id}", response_class=HTMLResponse)
def share_card(user_id: str, db: DBSession = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    streak_row = db.query(Streak).filter(Streak.user_id == user_id).first()
    current = streak_row.current_streak if streak_row else 0
    longest = streak_row.longest_streak if streak_row else 0
    total = streak_row.total_sessions if streak_row else 0

    # Build 4-week grid (28 days)
    from src.agents.streak import StreakAgent
    agent = StreakAgent()
    chain = agent.get_chain(user_id, db, days=28)
    # Pad to 28
    while len(chain) < 28:
        chain.insert(0, "empty")
    chain = chain[-28:]

    # Build grid rows (4 weeks, 7 cols)
    weeks_html = ""
    for w in range(4):
        cols = ""
        for d in range(7):
            idx = w * 7 + d
            filled = chain[idx] == "filled"
            cls = "filled" if filled else "empty"
            cols += f'<div class="cell {cls}"></div>'
        weeks_html += f'<div class="week">{cols}</div>'

    # Day labels
    day_labels = "".join(f'<div class="day-label">{d}</div>' for d in DAYS)

    name = user.name
    today = datetime.utcnow().strftime("%b %d, %Y")

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta property="og:title" content="{name} — {current} days unbroken">
<meta property="og:description" content="Jerome7 · YU Show Up · Day {current}">
<title>{name} — Jerome7</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&display=swap');
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    background: #0d1117; color: #c9d1d9;
    font-family: 'JetBrains Mono', monospace;
    display: flex; align-items: center; justify-content: center;
    min-height: 100vh; padding: 20px;
  }}
  .card {{
    background: #161b22; border: 1px solid #30363d; border-radius: 12px;
    padding: 28px 32px; max-width: 380px; width: 100%;
  }}
  .header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }}
  .brand {{ color: #E85D04; font-size: 13px; font-weight: 700; letter-spacing: 2px; }}
  .date {{ color: #484f58; font-size: 11px; }}
  .name {{ font-size: 18px; font-weight: 700; color: #f0f6fc; margin-bottom: 4px; }}
  .streak-line {{ font-size: 13px; color: #E85D04; margin-bottom: 20px; }}
  .grid-header {{ display: grid; grid-template-columns: repeat(7, 1fr); gap: 4px; margin-bottom: 4px; }}
  .day-label {{ text-align: center; font-size: 9px; color: #484f58; }}
  .week {{ display: grid; grid-template-columns: repeat(7, 1fr); gap: 4px; margin-bottom: 4px; }}
  .cell {{
    aspect-ratio: 1; border-radius: 3px;
    min-width: 0;
  }}
  .cell.filled {{ background: #E85D04; }}
  .cell.empty {{ background: #21262d; }}
  .stats {{
    display: flex; justify-content: space-between;
    margin-top: 20px; padding-top: 16px; border-top: 1px solid #21262d;
  }}
  .stat {{ text-align: center; }}
  .stat-num {{ font-size: 18px; font-weight: 700; color: #f0f6fc; }}
  .stat-label {{ font-size: 9px; color: #484f58; letter-spacing: 1px; margin-top: 2px; }}
  .footer {{
    margin-top: 20px; text-align: center;
    font-size: 11px; color: #484f58;
  }}
  .footer a {{ color: #E85D04; text-decoration: none; }}
  .cta {{
    display: block; text-align: center; margin-top: 16px;
    background: #E85D04; color: #fff; padding: 10px 20px;
    border-radius: 8px; text-decoration: none; font-size: 13px; font-weight: 700;
  }}
  .cta:hover {{ background: #ff6b1a; }}
</style>
</head>
<body>
<div class="card">
  <div class="header">
    <div class="brand">JEROME7</div>
    <div class="date">{today}</div>
  </div>
  <div class="name">{name}</div>
  <div class="streak-line">{current} days unbroken</div>
  <div class="grid-header">{day_labels}</div>
  {weeks_html}
  <div class="stats">
    <div class="stat"><div class="stat-num">{current}</div><div class="stat-label">CURRENT</div></div>
    <div class="stat"><div class="stat-num">{longest}</div><div class="stat-label">LONGEST</div></div>
    <div class="stat"><div class="stat-num">{total}</div><div class="stat-label">TOTAL</div></div>
  </div>
  <div class="footer">yu showed up · <a href="https://github.com/odominguez7/Jerome7">github.com/odominguez7/Jerome7</a></div>
  <a class="cta" href="https://github.com/odominguez7/Jerome7">Join Jerome7 — 7 min/day</a>
</div>
</body>
</html>"""
    return HTMLResponse(content=html)
