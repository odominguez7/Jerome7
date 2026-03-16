"""Daily session reminder emails for Jerome7."""

import asyncio
import hashlib
import hmac
import logging
import os
import smtplib
from datetime import datetime, timedelta, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from sqlalchemy.orm import Session

from src.api.email_utils import (
    SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM,
    SITE_URL, _smtp_configured,
)
from src.db.database import SessionLocal
from src.db.models import User, Session as SessionModel, Streak

logger = logging.getLogger("jerome7")

_SECRET = os.getenv("VERIFY_SECRET", "jerome7-dev-secret-change-in-prod")
REMINDER_HOUR_UTC = int(os.getenv("REMINDER_HOUR_UTC", "14"))


# -- Unsubscribe token (no expiry, HMAC-signed user_id) -----------------------

def generate_unsubscribe_token(user_id: str) -> str:
    """Create an HMAC-SHA256 token for unsubscribe links (no expiry)."""
    sig = hmac.new(
        _SECRET.encode(), f"unsub:{user_id}".encode(), hashlib.sha256
    ).hexdigest()
    return f"{user_id}.{sig}"


def verify_unsubscribe_token(token: str) -> str | None:
    """Return user_id if valid, else None."""
    try:
        parts = token.split(".", 1)
        if len(parts) != 2:
            return None
        user_id, sig = parts
        expected = hmac.new(
            _SECRET.encode(), f"unsub:{user_id}".encode(), hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(sig, expected):
            return None
        return user_id
    except Exception:
        return None


# -- Reminder email HTML -------------------------------------------------------

def _build_reminder_html(name: str, streak: int, unsub_url: str) -> str:
    streak_line = ""
    if streak > 0:
        streak_line = (
            f'<tr><td align="center" style="padding-bottom:24px;">'
            f'<span style="font-size:28px; font-weight:800; color:#E85D04; font-family:monospace;">'
            f'{streak}-day streak</span><br>'
            f'<span style="font-size:13px; color:#8b949e; font-family:monospace;">Keep it alive.</span>'
            f'</td></tr>'
        )

    return f"""\
<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"></head>
<body style="margin:0; padding:0; background:#0d1117; font-family:Arial,Helvetica,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#0d1117; padding:40px 20px;">
<tr><td align="center">
<table width="480" cellpadding="0" cellspacing="0" style="background:#161b22; border:1px solid #30363d; border-radius:16px; padding:48px 32px;">
<tr><td align="center" style="padding-bottom:24px;">
  <span style="font-size:10px; letter-spacing:3px; color:#E85D04; font-family:monospace;">JEROME7</span>
</td></tr>
<tr><td align="center" style="padding-bottom:16px;">
  <span style="font-size:22px; font-weight:700; color:#c9d1d9; font-family:monospace;">Hey {name},</span>
</td></tr>
<tr><td align="center" style="padding-bottom:24px;">
  <span style="font-size:14px; color:#8b949e; line-height:1.6;">
    Your 7 minutes are waiting.<br>
    Showing up is the hardest part. The rest is just breathing.
  </span>
</td></tr>
{streak_line}
<tr><td align="center" style="padding-bottom:32px;">
  <a href="{SITE_URL}/timer" style="display:inline-block; padding:14px 40px; background:#E85D04; color:#fff; border-radius:100px; text-decoration:none; font-family:monospace; font-size:14px; font-weight:700; letter-spacing:1px;">START SESSION</a>
</td></tr>
<tr><td align="center" style="padding-bottom:16px;">
  <span style="font-size:12px; color:#484f58; font-family:monospace;">7 minutes a day. An act of love.</span>
</td></tr>
<tr><td align="center">
  <a href="{unsub_url}" style="font-size:11px; color:#484f58; font-family:monospace; text-decoration:underline;">Unsubscribe from reminders</a>
</td></tr>
</table>
</td></tr>
</table>
</body>
</html>"""


def _build_reminder_text(name: str, streak: int, unsub_url: str) -> str:
    streak_line = ""
    if streak > 0:
        streak_line = f"\nYour streak: {streak} days. Keep it alive.\n"
    return (
        f"Hey {name},\n\n"
        f"Your 7 minutes are waiting.\n"
        f"Showing up is the hardest part. The rest is just breathing.\n"
        f"{streak_line}\n"
        f"Start your session: {SITE_URL}/timer\n\n"
        f"-- Jerome7\n"
        f"7 minutes a day. An act of love.\n\n"
        f"Unsubscribe: {unsub_url}"
    )


# -- Core reminder logic -------------------------------------------------------

def _send_one_reminder(email: str, name: str, streak_count: int, unsub_url: str) -> bool:
    """Send a single reminder email via SMTP. Returns True on success."""
    subject = "Your 7 minutes are waiting"
    html = _build_reminder_html(name, streak_count, unsub_url)
    text = _build_reminder_text(name, streak_count, unsub_url)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = SMTP_FROM
    msg["To"] = email
    msg.attach(MIMEText(text, "plain"))
    msg.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_FROM, [email], msg.as_string())
        return True
    except Exception as e:
        logger.error("Failed to send reminder to %s: %s", email, e)
        return False


async def send_daily_reminders() -> int:
    """Find eligible users and send reminder emails. Returns count sent."""
    if not _smtp_configured():
        logger.info("SMTP not configured, skipping reminders")
        return 0

    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    cutoff = now - timedelta(days=14)

    db: Session = SessionLocal()
    sent = 0
    try:
        # Users with verified email, reminders enabled, active in last 14 days
        eligible = (
            db.query(User)
            .filter(
                User.email.isnot(None),
                User.email_verified.is_(True),
                User.email_reminders.isnot(False),
                User.last_active_at >= cutoff,
            )
            .all()
        )

        for user in eligible:
            # Skip if already reminded today
            if user.last_reminder_at and user.last_reminder_at >= today_start:
                continue

            # Skip if they already logged a session today
            session_today = (
                db.query(SessionModel)
                .filter(
                    SessionModel.user_id == user.id,
                    SessionModel.logged_at >= today_start,
                )
                .first()
            )
            if session_today:
                continue

            # Get streak count
            streak_count = 0
            streak = db.query(Streak).filter(Streak.user_id == user.id).first()
            if streak:
                streak_count = streak.current_streak or 0

            unsub_token = generate_unsubscribe_token(user.id)
            unsub_url = f"{SITE_URL}/unsubscribe?token={unsub_token}"

            ok = _send_one_reminder(
                user.email, user.name, streak_count, unsub_url
            )
            if ok:
                user.last_reminder_at = now
                db.commit()
                sent += 1
                logger.info("Reminder sent to %s (%s)", user.name, user.email)

            # Small delay between sends to avoid SMTP rate limits
            await asyncio.sleep(0.5)

    except Exception as e:
        logger.error("Reminder batch failed: %s", e)
    finally:
        db.close()

    return sent


# -- Background loop -----------------------------------------------------------

async def reminder_loop():
    """Run once per day at REMINDER_HOUR_UTC. Intended to be launched as a task."""
    logger.info("Reminder loop started (fires daily at %02d:00 UTC)", REMINDER_HOUR_UTC)
    while True:
        now = datetime.now(timezone.utc)
        # Calculate seconds until next target hour
        target = now.replace(hour=REMINDER_HOUR_UTC, minute=0, second=0, microsecond=0)
        if now >= target:
            target += timedelta(days=1)
        wait_seconds = (target - now).total_seconds()
        logger.info("Next reminder batch in %.0f seconds (%s)", wait_seconds, target.isoformat())
        await asyncio.sleep(wait_seconds)

        logger.info("Starting daily reminder batch")
        count = await send_daily_reminders()
        logger.info("Daily reminder batch complete: %d emails sent", count)
