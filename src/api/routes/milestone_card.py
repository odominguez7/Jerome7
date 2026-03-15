"""GET /milestone/{user_id}/{milestone} — OG share card for streak milestones."""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session as DBSession

from src.db.database import get_db
from src.db.models import User

router = APIRouter()

MILESTONE_MESSAGES = {
    7: "First week. The habit is forming.",
    14: "Two weeks strong. This is real.",
    30: "30 days. A new baseline.",
    50: "50 days. Most never get here.",
    100: "Triple digits. Legendary.",
    200: "200 days. You're a force of nature.",
    365: "One year. 7 minutes changed everything.",
}


@router.get("/milestone/{user_id}/{milestone}", response_class=HTMLResponse)
def milestone_card(user_id: str, milestone: int, db: DBSession = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    jerome_num = user.jerome_number or "?"
    name = user.name
    message = MILESTONE_MESSAGES.get(milestone, f"{milestone} days. Still showing up.")

    og_title = f"Jerome{jerome_num} hit a {milestone}-day streak"
    og_desc = f"{message} — jerome7.com"

    tweet_text = (
        f"Day {milestone}. 7 minutes. \\u2713\\n\\n"
        f"I'm Jerome{jerome_num}. @Jerome7app\\n\\n"
        f"https://jerome7.com/join"
    )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Jerome{jerome_num} — {milestone}-day streak | Jerome7</title>
<meta property="og:title" content="{og_title}">
<meta property="og:description" content="{og_desc}">
<meta property="og:image" content="https://jerome7.com/streak/{name}/card.png">
<meta property="og:url" content="https://jerome7.com/milestone/{user_id}/{milestone}">
<meta property="og:type" content="website">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{og_title}">
<meta name="twitter:description" content="{og_desc}">
<meta name="twitter:image" content="https://jerome7.com/streak/{name}/card.png">
<style>
  @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700;800&display=swap');
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    background: #0d1117; color: #c9d1d9;
    font-family: 'JetBrains Mono', monospace;
    display: flex; align-items: center; justify-content: center;
    min-height: 100vh; padding: 20px;
  }}
  .card {{
    background: #161b22; border: 1px solid #30363d;
    border-radius: 16px; padding: 40px; max-width: 440px;
    width: 100%; text-align: center;
  }}
  .brand {{ color: #E85D04; font-size: 11px; font-weight: 700; letter-spacing: 3px; margin-bottom: 24px; }}
  .milestone-num {{ font-size: 72px; font-weight: 800; color: #E85D04; line-height: 1; }}
  .milestone-label {{ font-size: 14px; color: #8b949e; margin-bottom: 16px; }}
  .jerome-id {{ font-size: 18px; font-weight: 700; color: #f0f6fc; margin-bottom: 8px; }}
  .message {{ font-size: 14px; color: #8b949e; margin-bottom: 32px; line-height: 1.5; }}
  .actions {{ display: flex; flex-direction: column; gap: 8px; }}
  .btn {{
    display: block; text-align: center; padding: 12px 20px;
    border-radius: 100px; text-decoration: none;
    font-family: inherit; font-size: 13px; font-weight: 700;
    letter-spacing: 1px; transition: all 0.2s;
  }}
  .btn-primary {{ background: #E85D04; color: #fff; }}
  .btn-primary:hover {{ background: #ff6b1a; }}
  .btn-outline {{
    background: transparent; color: #c9d1d9;
    border: 1px solid #30363d;
  }}
  .btn-outline:hover {{ border-color: #484f58; background: #1a1a1a; }}
</style>
</head>
<body>
<div class="card">
  <div class="brand">JEROME7</div>
  <div class="milestone-num">{milestone}</div>
  <div class="milestone-label">day streak</div>
  <div class="jerome-id">Jerome{jerome_num}</div>
  <div class="message">{message}</div>
  <div class="actions">
    <a class="btn btn-primary" href="https://jerome7.com">Join Jerome7</a>
    <a class="btn btn-outline" href="https://twitter.com/intent/tweet?text={tweet_text.replace(' ', '+').replace('#', '%23').replace(chr(10), '%0A')}" target="_blank">Share on Twitter</a>
  </div>
</div>
</body>
</html>"""
    return HTMLResponse(content=html)
