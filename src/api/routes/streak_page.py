"""Public streak page — the viral engine."""

import io
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from sqlalchemy.orm import Session as DBSession

from src.db.database import get_db
from src.db.models import User, Streak, PodMember, Pod
from src.agents.streak import StreakAgent

router = APIRouter()
streak_agent = StreakAgent()


@router.get("/streak/{username}/page", response_class=HTMLResponse)
def streak_page(username: str, db: DBSession = Depends(get_db)):
    user = db.query(User).filter(User.name == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    streak = db.query(Streak).filter(Streak.user_id == user.id).first()
    if not streak:
        raise HTTPException(status_code=404, detail="No streak data")

    chain = streak_agent.get_chain(user.id, db)

    # Pod info
    pod_name = None
    membership = db.query(PodMember).filter(
        PodMember.user_id == user.id, PodMember.status == "active"
    ).first()
    if membership:
        pod = db.query(Pod).filter(Pod.id == membership.pod_id).first()
        if pod:
            pod_name = pod.name

    # Start date
    start_date = "today"
    if streak.last_session_date and streak.current_streak > 0:
        start = streak.last_session_date - timedelta(days=streak.current_streak - 1)
        start_date = start.strftime("%B %d, %Y")

    from jinja2 import Environment, FileSystemLoader
    import os
    template_dir = os.path.join(os.path.dirname(__file__), "..", "..", "..", "streak_page", "templates")
    env = Environment(loader=FileSystemLoader(template_dir))
    template = env.get_template("streak.html")

    html = template.render(
        name=user.name,
        username=user.name,
        current_streak=streak.current_streak,
        chain=chain,
        pod_name=pod_name,
        start_date=start_date,
    )
    return HTMLResponse(content=html)


@router.get("/streak/{username}/card.png")
def streak_card(username: str, db: DBSession = Depends(get_db)):
    """Generate a 1200x630 OG image for social sharing."""
    user = db.query(User).filter(User.name == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    streak = db.query(Streak).filter(Streak.user_id == user.id).first()
    if not streak:
        raise HTTPException(status_code=404, detail="No streak data")

    try:
        from PIL import Image, ImageDraw, ImageFont

        img = Image.new("RGB", (1200, 630), color=(15, 28, 46))
        draw = ImageDraw.Draw(img)

        # Use default font (Pillow built-in)
        try:
            font_large = ImageFont.truetype("/System/Library/Fonts/SFMono-Bold.otf", 120)
            font_medium = ImageFont.truetype("/System/Library/Fonts/SFMono-Regular.otf", 36)
            font_small = ImageFont.truetype("/System/Library/Fonts/SFMono-Regular.otf", 24)
        except (IOError, OSError):
            font_large = ImageFont.load_default()
            font_medium = ImageFont.load_default()
            font_small = ImageFont.load_default()

        # Username
        draw.text((60, 40), user.name, fill=(232, 93, 4), font=font_medium)

        # Streak number
        draw.text((60, 180), str(streak.current_streak), fill=(232, 93, 4), font=font_large)
        draw.text((60, 340), "days unbroken", fill=(122, 139, 160), font=font_medium)

        # Chain visualization
        chain = streak_agent.get_chain(user.id, db, days=30)
        x_start = 60
        y_chain = 440
        for i, day in enumerate(chain):
            color = (232, 93, 4) if day == "filled" else (26, 42, 62)
            draw.ellipse(
                [x_start + i * 28, y_chain, x_start + i * 28 + 18, y_chain + 18],
                fill=color,
            )

        # Wordmark
        draw.text((60, 570), "YU SHOW UP", fill=(42, 58, 78), font=font_small)

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        return StreamingResponse(buf, media_type="image/png")

    except ImportError:
        raise HTTPException(status_code=500, detail="Pillow not installed")
