"""GET /card/{user_id} — shareable session card (SVG image + plain text).

Jerome7's version of Wordle's colored squares.
"""

from datetime import datetime, date, timedelta
from xml.sax.saxutils import escape as xml_escape

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response, PlainTextResponse
from sqlalchemy.orm import Session as DBSession

from src.db.database import get_db
from src.db.models import User, Streak, Session, Seven7Session

router = APIRouter()

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

# Default block names when session data is unavailable
_DEFAULT_BLOCKS = [
    "Jumping Jacks",
    "Push-ups",
    "Mountain Climbers",
    "Plank Hold",
    "High Knees",
    "Squats",
    "Burpees",
]


def _get_flag(country: str | None) -> str:
    if country and country in _CODE_TO_FLAG:
        return _CODE_TO_FLAG[country]
    return "\U0001f310"


def _build_chain(user_id: str, db: DBSession, days: int = 30) -> list[str]:
    today = date.today()
    start = today - timedelta(days=days - 1)
    sessions = db.query(Session).filter(Session.user_id == user_id).all()
    session_dates: set[date] = set()
    for s in sessions:
        if s.logged_at:
            d = s.logged_at.date() if isinstance(s.logged_at, datetime) else s.logged_at
            session_dates.add(d)
    chain = []
    for i in range(days):
        d = start + timedelta(days=i)
        chain.append("filled" if d in session_dates else "empty")
    return chain


def _get_block_names(user_id: str, db: DBSession) -> list[str]:
    """Get block names from the user's most recent Seven7 session."""
    latest = (
        db.query(Seven7Session)
        .filter(Seven7Session.user_id == user_id)
        .order_by(Seven7Session.generated_at.desc())
        .first()
    )
    if latest and latest.blocks:
        blocks = latest.blocks
        if isinstance(blocks, list):
            names = []
            for b in blocks[:7]:
                if isinstance(b, dict):
                    names.append(b.get("name", "Exercise"))
                else:
                    names.append(str(b))
            if names:
                return names
    return _DEFAULT_BLOCKS


def _build_svg(
    name: str,
    current_streak: int,
    block_names: list[str],
    chain: list[str],
    flag: str,
    today_str: str,
) -> str:
    """Generate a 600x800 SVG session card."""
    bg = "#0f1419"
    orange = "#e8713a"
    dim = "#484f58"
    light = "#f0f6fc"
    mid = "#8b949e"
    card_bg = "#161b22"
    dot_empty_color = "#21262d"

    # Build streak chain dots (30 days, positioned in a row)
    dot_size = 14
    dot_gap = 4
    total_chain_width = 30 * dot_size + 29 * dot_gap
    chain_start_x = (600 - total_chain_width) / 2
    chain_y = 590

    dots_svg = ""
    for i, status in enumerate(chain):
        x = chain_start_x + i * (dot_size + dot_gap)
        fill = orange if status == "filled" else dot_empty_color
        dots_svg += f'<rect x="{x:.1f}" y="{chain_y}" width="{dot_size}" height="{dot_size}" rx="3" fill="{fill}"/>'

    # Build exercise block rows
    blocks_svg = ""
    block_start_y = 250
    block_spacing = 42
    square_size = 24
    for i, bname in enumerate(block_names[:7]):
        y = block_start_y + i * block_spacing
        # Orange square
        blocks_svg += f'<rect x="80" y="{y}" width="{square_size}" height="{square_size}" rx="4" fill="{orange}"/>'
        # Block name
        blocks_svg += f'<text x="118" y="{y + 17}" font-family="monospace" font-size="16" fill="{light}">{xml_escape(bname)}</text>'

    # Fire emoji chain for streak
    fire_count = min(current_streak, 10)
    fire_str = "\U0001f525" * fire_count
    if current_streak > 10:
        fire_str += f" +{current_streak - 10}"

    svg = f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 800" width="600" height="800">
  <defs>
    <style>
      @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700;800&amp;display=swap');
    </style>
  </defs>

  <!-- Background -->
  <rect width="600" height="800" fill="{bg}" rx="16"/>
  <rect x="20" y="20" width="560" height="760" fill="{card_bg}" rx="12" stroke="#30363d" stroke-width="1"/>

  <!-- JEROME7 branding -->
  <text x="60" y="70" font-family="'JetBrains Mono', monospace" font-size="14" font-weight="700"
        fill="{orange}" letter-spacing="4">JEROME7</text>

  <!-- Date -->
  <text x="540" y="70" font-family="'JetBrains Mono', monospace" font-size="12"
        fill="{dim}" text-anchor="end">{xml_escape(today_str)}</text>

  <!-- Flag + Name -->
  <text x="60" y="120" font-size="32">{flag}</text>
  <text x="105" y="120" font-family="'JetBrains Mono', monospace" font-size="22" font-weight="700"
        fill="{light}">{xml_escape(name)}</text>

  <!-- Streak number -->
  <text x="60" y="185" font-family="'JetBrains Mono', monospace" font-size="56" font-weight="800"
        fill="{orange}">{current_streak}</text>
  <text x="60" y="210" font-family="'JetBrains Mono', monospace" font-size="14"
        fill="{mid}">days unbroken {fire_str}</text>

  <!-- Separator -->
  <line x1="60" y1="230" x2="540" y2="230" stroke="#21262d" stroke-width="1"/>

  <!-- Exercise blocks -->
  {blocks_svg}

  <!-- Separator -->
  <line x1="60" y1="555" x2="540" y2="555" stroke="#21262d" stroke-width="1"/>

  <!-- Chain label -->
  <text x="60" y="580" font-family="'JetBrains Mono', monospace" font-size="9"
        fill="{dim}" letter-spacing="2">LAST 30 DAYS</text>

  <!-- Chain dots -->
  {dots_svg}

  <!-- Separator -->
  <line x1="60" y1="625" x2="540" y2="625" stroke="#21262d" stroke-width="1"/>

  <!-- Bottom tagline -->
  <text x="300" y="670" font-family="'JetBrains Mono', monospace" font-size="16" font-weight="600"
        fill="{light}" text-anchor="middle">7 minutes. I showed up.</text>

  <!-- Watermark -->
  <text x="300" y="710" font-family="'JetBrains Mono', monospace" font-size="12"
        fill="{dim}" text-anchor="middle">jerome7.com</text>
</svg>"""
    return svg


def _build_text(
    name: str,
    current_streak: int,
    block_names: list[str],
    flag: str,
) -> str:
    """Generate a plain-text shareable card (Wordle-style)."""
    lines = [
        f"JEROME7 \u00b7 Day {current_streak} \U0001f525",
        "\u2501" * 17,
    ]
    for bname in block_names[:7]:
        lines.append(f"\U0001f7e7 {bname}")
    lines.append("\u2501" * 17)
    lines.append(f"{current_streak}-day chain \U0001f517 unbroken")
    lines.append(f"{flag} jerome7.com")
    return "\n".join(lines)


# ── Endpoints ──────────────────────────────────────────────


@router.get("/card/{user_id}")
def session_card_svg(user_id: str, db: DBSession = Depends(get_db)):
    """Return an SVG session card image for sharing."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    streak_row = db.query(Streak).filter(Streak.user_id == user_id).first()
    current = streak_row.current_streak if streak_row else 0

    flag = _get_flag(user.country)
    today_str = datetime.utcnow().strftime("%b %d, %Y")
    block_names = _get_block_names(user_id, db)
    chain = _build_chain(user_id, db, days=30)

    svg = _build_svg(
        name=user.name,
        current_streak=current,
        block_names=block_names,
        chain=chain,
        flag=flag,
        today_str=today_str,
    )
    return Response(content=svg, media_type="image/svg+xml")


@router.get("/card/{user_id}/text")
def session_card_text(user_id: str, db: DBSession = Depends(get_db)):
    """Return a plain-text session card (Wordle-style colored squares)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    streak_row = db.query(Streak).filter(Streak.user_id == user_id).first()
    current = streak_row.current_streak if streak_row else 0

    flag = _get_flag(user.country)
    block_names = _get_block_names(user_id, db)

    text = _build_text(
        name=user.name,
        current_streak=current,
        block_names=block_names,
        flag=flag,
    )
    return PlainTextResponse(content=text)
