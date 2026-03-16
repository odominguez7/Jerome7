"""GET /verify?token= -- HMAC-based email verification."""

import logging

from fastapi import APIRouter, Depends, Query
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from src.api.email_utils import verify_token
from src.db.database import get_db
from src.db.models import User

logger = logging.getLogger("jerome7")

router = APIRouter()


def _verify_page(title: str, message: str, sub: str, color: str, show_start: bool = True) -> str:
    start_btn = ""
    if show_start:
        start_btn = '<a class="btn" href="/timer">START SESSION</a>'
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
  {start_btn}
</div>
</body>
</html>"""


@router.get("/verify", response_class=HTMLResponse)
async def verify_email(token: str = Query(default=""), db: Session = Depends(get_db)):
    """Verify a user's email via HMAC-signed token."""
    if not token:
        return HTMLResponse(
            content=_verify_page(
                "Invalid Link",
                "Missing verification token.",
                "Check your email for the correct link.",
                "#f85149",
            ),
            status_code=400,
        )

    user_id = verify_token(token)
    if user_id is None:
        return HTMLResponse(
            content=_verify_page(
                "Link Expired",
                "This verification link is invalid or expired.",
                "Request a new verification email from your profile.",
                "#f85149",
            ),
            status_code=400,
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return HTMLResponse(
            content=_verify_page(
                "Not Found",
                "User not found.",
                "The account associated with this link no longer exists.",
                "#f85149",
            ),
            status_code=404,
        )

    if user.email_verified:
        jerome_label = f"Jerome#{user.jerome_number}" if user.jerome_number else user.name
        return HTMLResponse(
            content=_verify_page(
                "Already Verified",
                f"Already verified, {jerome_label}.",
                "Your email was already confirmed. You're good.",
                "#3fb950",
            ),
        )

    # Mark verified
    user.email_verified = True
    user.email_verify_token = None
    db.commit()

    jerome_label = f"Jerome#{user.jerome_number}" if user.jerome_number else user.name
    logger.info("Email verified for user %s (%s)", user_id, user.email)

    return HTMLResponse(
        content=_verify_page(
            "Email Verified",
            f"Email verified. Welcome, {jerome_label}.",
            "You're part of something real.",
            "#3fb950",
        ),
    )
