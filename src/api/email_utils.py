"""Email verification utilities: HMAC token generation, validation, and SMTP sending."""

import hashlib
import hmac
import logging
import os
import smtplib
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger("jerome7")

# ── Configuration ────────────────────────────────────────────────────────────

_SECRET = os.getenv("VERIFY_SECRET", "jerome7-dev-secret-change-in-prod")
SITE_URL = os.getenv("SITE_URL", "https://jerome7.com").rstrip("/")
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", "Jerome7 <hello@jerome7.com>")

TOKEN_EXPIRY_SECONDS = 48 * 3600  # 48 hours


# ── Token generation and verification ────────────────────────────────────────

def generate_verify_token(user_id: str) -> str:
    """Create an HMAC-SHA256 signed token encoding user_id and timestamp."""
    ts = int(time.time())
    payload = f"{user_id}:{ts}"
    sig = hmac.new(
        _SECRET.encode(), payload.encode(), hashlib.sha256
    ).hexdigest()
    # token = base16(timestamp) . user_id . signature
    return f"{ts:x}.{user_id}.{sig}"


def verify_token(token: str) -> str | None:
    """Validate token and return user_id if valid and not expired. None otherwise."""
    try:
        parts = token.split(".", 2)
        if len(parts) != 3:
            return None
        ts_hex, user_id, sig = parts
        ts = int(ts_hex, 16)

        # Check expiry
        if time.time() - ts > TOKEN_EXPIRY_SECONDS:
            return None

        # Verify signature
        payload = f"{user_id}:{ts}"
        expected = hmac.new(
            _SECRET.encode(), payload.encode(), hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(sig, expected):
            return None

        return user_id
    except Exception:
        return None


# ── Email sending ────────────────────────────────────────────────────────────

def _smtp_configured() -> bool:
    return bool(SMTP_HOST and SMTP_USER and SMTP_PASSWORD)


def send_verification_email(email: str, user_id: str, name: str) -> bool:
    """Send a verification email. Returns True on success, False on failure."""
    if not _smtp_configured():
        logger.warning("SMTP not configured -- skipping verification email for %s", email)
        return False

    token = generate_verify_token(user_id)
    verify_url = f"{SITE_URL}/verify?token={token}"

    subject = "Verify your email - Jerome7"
    html_body = _build_email_html(name, verify_url)
    text_body = (
        f"Hey {name},\n\n"
        f"Verify your email to complete your Jerome7 signup:\n\n"
        f"{verify_url}\n\n"
        f"This link expires in 48 hours.\n\n"
        f"-- Jerome7\n"
        f"7 minutes a day. An act of love."
    )

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = SMTP_FROM
    msg["To"] = email
    msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_FROM, [email], msg.as_string())
        logger.info("Verification email sent to %s", email)
        return True
    except Exception as e:
        logger.error("Failed to send verification email to %s: %s", email, e)
        return False


def _build_email_html(name: str, verify_url: str) -> str:
    """Build the branded HTML email body."""
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
<tr><td align="center" style="padding-bottom:32px;">
  <span style="font-size:14px; color:#8b949e; line-height:1.6;">
    Verify your email to complete your Jerome7 signup.<br>
    This link expires in 48 hours.
  </span>
</td></tr>
<tr><td align="center" style="padding-bottom:32px;">
  <a href="{verify_url}" style="display:inline-block; padding:14px 40px; background:#E85D04; color:#fff; border-radius:100px; text-decoration:none; font-family:monospace; font-size:14px; font-weight:700; letter-spacing:1px;">VERIFY YOUR EMAIL</a>
</td></tr>
<tr><td align="center">
  <span style="font-size:12px; color:#484f58; font-family:monospace;">7 minutes a day. An act of love.</span>
</td></tr>
</table>
</td></tr>
</table>
</body>
</html>"""
