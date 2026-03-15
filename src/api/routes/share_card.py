"""GET /share/{user_id} — shareable streak card with OG meta tags for Twitter/Discord/WhatsApp."""

from datetime import datetime, date, timedelta

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session as DBSession

from src.db.database import get_db
from src.db.models import User, Streak, Session

router = APIRouter()

DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

# Country code -> flag emoji
_CODE_TO_FLAG = {
    "US": "\U0001f1fa\U0001f1f8", "CA": "\U0001f1e8\U0001f1e6",
    "MX": "\U0001f1f2\U0001f1fd", "BR": "\U0001f1e7\U0001f1f7",
    "AR": "\U0001f1e6\U0001f1f7", "CO": "\U0001f1e8\U0001f1f4",
    "PE": "\U0001f1f5\U0001f1ea", "CL": "\U0001f1e8\U0001f1f1",
    "GB": "\U0001f1ec\U0001f1e7", "FR": "\U0001f1eb\U0001f1f7",
    "DE": "\U0001f1e9\U0001f1ea", "ES": "\U0001f1ea\U0001f1f8",
    "IT": "\U0001f1ee\U0001f1f9", "NL": "\U0001f1f3\U0001f1f1",
    "PT": "\U0001f1f5\U0001f1f9", "SE": "\U0001f1f8\U0001f1ea",
    "NO": "\U0001f1f3\U0001f1f4", "DK": "\U0001f1e9\U0001f1f0",
    "FI": "\U0001f1eb\U0001f1ee", "PL": "\U0001f1f5\U0001f1f1",
    "IN": "\U0001f1ee\U0001f1f3", "JP": "\U0001f1ef\U0001f1f5",
    "KR": "\U0001f1f0\U0001f1f7", "CN": "\U0001f1e8\U0001f1f3",
    "AU": "\U0001f1e6\U0001f1fa", "NZ": "\U0001f1f3\U0001f1ff",
    "SG": "\U0001f1f8\U0001f1ec", "PH": "\U0001f1f5\U0001f1ed",
    "NG": "\U0001f1f3\U0001f1ec", "KE": "\U0001f1f0\U0001f1ea",
    "EG": "\U0001f1ea\U0001f1ec", "ZA": "\U0001f1ff\U0001f1e6",
    "IL": "\U0001f1ee\U0001f1f1", "AE": "\U0001f1e6\U0001f1ea",
    "TR": "\U0001f1f9\U0001f1f7",
}


def _get_flag(country: str | None) -> str:
    """Return flag emoji for a country code, or globe if unknown."""
    if country and country in _CODE_TO_FLAG:
        return _CODE_TO_FLAG[country]
    return "\U0001f310"  # globe


def _build_chain(user_id: str, db: DBSession, days: int = 30) -> list[str]:
    """Build a list of 'filled'/'empty' for the last N days from Session data."""
    today = date.today()
    start = today - timedelta(days=days - 1)

    sessions = (
        db.query(Session)
        .filter(Session.user_id == user_id)
        .all()
    )
    session_dates = set()
    for s in sessions:
        if s.logged_at:
            d = s.logged_at.date() if isinstance(s.logged_at, datetime) else s.logged_at
            session_dates.add(d)

    chain = []
    for i in range(days):
        d = start + timedelta(days=i)
        chain.append("filled" if d in session_dates else "empty")
    return chain


@router.get("/share/{user_id}", response_class=HTMLResponse)
def share_card(user_id: str, db: DBSession = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    streak_row = db.query(Streak).filter(Streak.user_id == user_id).first()
    current = streak_row.current_streak if streak_row else 0
    longest = streak_row.longest_streak if streak_row else 0
    total = streak_row.total_sessions if streak_row else 0

    flag = _get_flag(user.country)
    name = user.name
    today_str = datetime.utcnow().strftime("%b %d, %Y")

    # Build 30-day chain
    chain = _build_chain(user_id, db, days=30)

    # Chain dots HTML
    dots_html = ""
    for i, day in enumerate(chain):
        cls = "dot-filled" if day == "filled" else "dot-empty"
        dots_html += f'<div class="dot {cls}"></div>'

    # OG image URL (points to existing card.png endpoint)
    og_image_url = f"https://jerome7.com/streak/{name}/card.png"
    og_title = f"{flag} {name} — {current} days unbroken"
    og_description = f"Longest: {longest}d | Total: {total} sessions | jerome7.com"

    # Twitter share text
    tweet_text = (
        f"Day {current} \U0001f525 Just finished my Jerome7 session. "
        f"7 minutes. Every day. — jerome7.com #jerome7 #buildinpublic"
    )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{name} — {current} days unbroken | Jerome7</title>

<!-- OG Meta Tags -->
<meta property="og:title" content="{og_title}">
<meta property="og:description" content="{og_description}">
<meta property="og:image" content="{og_image_url}">
<meta property="og:url" content="https://jerome7.com/share/{user_id}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Jerome7">

<!-- Twitter Card Meta Tags -->
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{og_title}">
<meta name="twitter:description" content="{og_description}">
<meta name="twitter:image" content="{og_image_url}">

<style>
  @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700;800&display=swap');
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}

  body {{
    background: #0d1117;
    color: #c9d1d9;
    font-family: 'JetBrains Mono', monospace;
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 100vh;
    padding: 20px;
  }}

  .card {{
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 16px;
    padding: 32px 36px;
    max-width: 420px;
    width: 100%;
  }}

  /* Header */
  .header {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 24px;
  }}
  .brand {{
    color: #E85D04;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 3px;
  }}
  .date {{
    color: #484f58;
    font-size: 11px;
  }}

  /* Identity */
  .identity {{
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 8px;
  }}
  .flag {{
    font-size: 28px;
  }}
  .name {{
    font-size: 20px;
    font-weight: 700;
    color: #f0f6fc;
  }}

  /* Streak number */
  .streak-hero {{
    font-size: 48px;
    font-weight: 800;
    color: #E85D04;
    line-height: 1;
    margin-bottom: 4px;
  }}
  .streak-label {{
    font-size: 13px;
    color: #8b949e;
    margin-bottom: 24px;
  }}

  /* 30-day chain */
  .chain-label {{
    font-size: 9px;
    letter-spacing: 2px;
    color: #484f58;
    margin-bottom: 8px;
  }}
  .chain {{
    display: grid;
    grid-template-columns: repeat(30, 1fr);
    gap: 3px;
    margin-bottom: 24px;
  }}
  .dot {{
    aspect-ratio: 1;
    border-radius: 3px;
    min-width: 0;
  }}
  .dot-filled {{
    background: #E85D04;
  }}
  .dot-empty {{
    background: #21262d;
  }}

  /* Stats */
  .stats {{
    display: flex;
    justify-content: space-between;
    padding-top: 20px;
    border-top: 1px solid #21262d;
    margin-bottom: 24px;
  }}
  .stat {{ text-align: center; }}
  .stat-num {{
    font-size: 20px;
    font-weight: 700;
    color: #f0f6fc;
  }}
  .stat-label {{
    font-size: 9px;
    color: #484f58;
    letter-spacing: 1px;
    margin-top: 2px;
  }}

  /* Branding footer */
  .branding {{
    text-align: center;
    font-size: 11px;
    color: #484f58;
    margin-bottom: 20px;
  }}
  .branding a {{
    color: #E85D04;
    text-decoration: none;
  }}

  /* CTA buttons */
  .actions {{
    display: flex;
    flex-direction: column;
    gap: 8px;
  }}
  .cta-join {{
    display: block;
    text-align: center;
    background: #E85D04;
    color: #fff;
    padding: 12px 20px;
    border-radius: 100px;
    text-decoration: none;
    font-family: inherit;
    font-size: 13px;
    font-weight: 700;
    letter-spacing: 1px;
    transition: background 0.2s;
  }}
  .cta-join:hover {{ background: #ff6b1a; }}

  .cta-twitter {{
    display: block;
    text-align: center;
    background: #000;
    color: #fff;
    padding: 12px 20px;
    border-radius: 100px;
    text-decoration: none;
    font-family: inherit;
    font-size: 13px;
    font-weight: 700;
    letter-spacing: 1px;
    border: 1px solid #30363d;
    transition: all 0.2s;
  }}
  .cta-twitter:hover {{ background: #1a1a1a; border-color: #484f58; }}

  /* Responsive */
  @media (max-width: 480px) {{
    .card {{ padding: 24px 20px; }}
    .streak-hero {{ font-size: 40px; }}
    .chain {{ gap: 2px; }}
  }}
</style>
</head>
<body>
<div class="card">
  <div class="header">
    <div class="brand">JEROME7</div>
    <div class="date">{today_str}</div>
  </div>

  <div class="identity">
    <span class="flag">{flag}</span>
    <span class="name">{name}</span>
  </div>

  <div class="streak-hero">{current}</div>
  <div class="streak-label">days unbroken</div>

  <div class="chain-label">LAST 30 DAYS</div>
  <div class="chain">
    {dots_html}
  </div>

  <div class="stats">
    <div class="stat"><div class="stat-num">{current}</div><div class="stat-label">CURRENT</div></div>
    <div class="stat"><div class="stat-num">{longest}</div><div class="stat-label">LONGEST</div></div>
    <div class="stat"><div class="stat-num">{total}</div><div class="stat-label">TOTAL</div></div>
  </div>

  <div class="branding">
    <a href="https://jerome7.com">jerome7.com</a> &mdash; 7 minutes. Show up.
  </div>

  <div class="actions">
    <a class="cta-join" href="https://jerome7.com">Join Jerome7</a>
    <a class="cta-twitter" href="https://twitter.com/intent/tweet?text={tweet_text.replace(' ', '+').replace('#', '%23')}" target="_blank">\U0001d54f Share on Twitter</a>
  </div>
</div>
</body>
</html>"""
    return HTMLResponse(content=html)
