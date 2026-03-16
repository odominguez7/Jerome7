"""GET /unsubscribe?token= -- opt out of reminder emails."""

import logging

from fastapi import APIRouter, Depends, Query
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from src.api.reminders import verify_unsubscribe_token
from src.db.database import get_db
from src.db.models import User

logger = logging.getLogger("jerome7")

router = APIRouter()


def _unsub_page(title: str, message: str, sub: str, color: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="robots" content="noindex">
<title>Jerome7 | {title}</title>
<link rel="icon" type="image/svg+xml" href="/static/favicon.svg">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700;800&display=swap" rel="stylesheet">
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    background: #0d1117; color: #c9d1d9;
    font-family: 'JetBrains Mono', monospace;
    min-height: 100vh; display: flex; align-items: center; justify-content: center;
    padding: 20px;
  }}
  .card {{
    max-width: 480px; width: 100%; text-align: center;
    background: #161b22; border: 1px solid #30363d;
    border-radius: 16px; padding: 48px 32px;
  }}
  .brand {{ font-size: 10px; letter-spacing: 3px; color: #E85D04; margin-bottom: 24px; }}
  .message {{ font-size: 18px; font-weight: 700; color: {color}; margin-bottom: 16px; line-height: 1.4; }}
  .sub {{ font-size: 13px; color: #8b949e; margin-bottom: 32px; }}
  a.btn {{
    display: inline-block; padding: 14px 40px;
    background: #E85D04; color: #fff; border-radius: 100px;
    text-decoration: none; font-family: inherit;
    font-size: 14px; font-weight: 700; letter-spacing: 1px;
  }}
  a.btn:hover {{ background: #ff6b1a; }}
</style>
</head>
<body>
<div class="card">
  <div class="brand">JEROME7</div>
  <div class="message">{message}</div>
  <div class="sub">{sub}</div>
  <a class="btn" href="/timer">START SESSION</a>
</div>
</body>
</html>"""


@router.get("/unsubscribe", response_class=HTMLResponse)
async def unsubscribe(token: str = Query(default=""), db: Session = Depends(get_db)):
    """Unsubscribe a user from reminder emails via HMAC-signed token."""
    if not token:
        return HTMLResponse(
            content=_unsub_page(
                "Invalid Link",
                "Missing unsubscribe token.",
                "Check your email for the correct link.",
                "#f85149",
            ),
            status_code=400,
        )

    user_id = verify_unsubscribe_token(token)
    if user_id is None:
        return HTMLResponse(
            content=_unsub_page(
                "Invalid Link",
                "This unsubscribe link is invalid.",
                "If you keep getting emails, reply to one and we will remove you.",
                "#f85149",
            ),
            status_code=400,
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return HTMLResponse(
            content=_unsub_page(
                "Not Found",
                "User not found.",
                "The account associated with this link no longer exists.",
                "#f85149",
            ),
            status_code=404,
        )

    if user.email_reminders is False:
        return HTMLResponse(
            content=_unsub_page(
                "Already Unsubscribed",
                "You're already unsubscribed.",
                "You won't receive any more reminder emails from us.",
                "#8b949e",
            ),
        )

    user.email_reminders = False
    db.commit()
    logger.info("User %s (%s) unsubscribed from reminders", user_id, user.email)

    return HTMLResponse(
        content=_unsub_page(
            "Unsubscribed",
            "You've been unsubscribed.",
            "No more reminder emails. Your 7 minutes will still be here whenever you're ready.",
            "#3fb950",
        ),
    )
