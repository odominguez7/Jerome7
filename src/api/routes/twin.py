"""GET /twin/{user_id} — Digital Twin forward simulation.

Uses real streak data + feedback to project your body and habits
at 30, 90, and 365 days. Powered by Gemini AI.
"""

import asyncio
import json
import os
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy import func
from sqlalchemy.orm import Session as DBSession

from src.db.database import get_db
from src.db.models import User, Streak, Session as SessionModel, SessionFeedback

router = APIRouter()

_TWIN_PROMPT = """You are a sports science AI analyzing real movement data.

Given this person's actual consistency data, generate a realistic forward projection
of their physical state at 30, 90, and 365 days if they continue their current pattern.

Be SPECIFIC and EVIDENCE-BASED. Reference their actual numbers.
Be honest — if consistency is low, say so. If it's high, celebrate it.

Output JSON only:
{
  "current_assessment": "2-3 sentences. Where they are RIGHT NOW based on data.",
  "projections": [
    {
      "days": 30,
      "title": "3-4 words. e.g. 'Habit Locked In'",
      "mobility": 1-100,
      "consistency": 1-100,
      "energy": 1-100,
      "habit_strength": 1-100,
      "narrative": "2-3 sentences. Specific. What changes at 30 days."
    },
    {
      "days": 90,
      "title": "3-4 words",
      "mobility": 1-100,
      "consistency": 1-100,
      "energy": 1-100,
      "habit_strength": 1-100,
      "narrative": "2-3 sentences. Specific."
    },
    {
      "days": 365,
      "title": "3-4 words",
      "mobility": 1-100,
      "consistency": 1-100,
      "energy": 1-100,
      "habit_strength": 1-100,
      "narrative": "2-3 sentences. Specific."
    }
  ],
  "insight": "1 sentence. The most important thing they should know."
}"""


def _build_twin_data(user_id: str, db: DBSession) -> dict:
    """Gather all data needed for the digital twin projection."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    streak = db.query(Streak).filter(Streak.user_id == user_id).first()

    # Total sessions + sessions by time period
    total_sessions = db.query(SessionModel).filter(
        SessionModel.user_id == user_id
    ).count()

    now = datetime.utcnow()
    sessions_7d = db.query(SessionModel).filter(
        SessionModel.user_id == user_id,
        SessionModel.logged_at >= now - timedelta(days=7),
    ).count()
    sessions_30d = db.query(SessionModel).filter(
        SessionModel.user_id == user_id,
        SessionModel.logged_at >= now - timedelta(days=30),
    ).count()

    # Consistency: sessions / days since signup
    days_since_signup = max((now - user.created_at).days, 1) if user.created_at else 1
    consistency_pct = round(min(total_sessions / days_since_signup * 100, 100), 1)

    # Average feedback
    avg_difficulty = db.query(func.avg(SessionFeedback.difficulty_rating)).filter(
        SessionFeedback.user_id == user_id
    ).scalar()
    avg_enjoyment = db.query(func.avg(SessionFeedback.enjoyment_rating)).filter(
        SessionFeedback.user_id == user_id
    ).scalar()

    # Streak breaks
    streak_breaks = streak.streak_broken_count if streak else 0

    return {
        "name": user.name,
        "age_bracket": user.age_bracket.value if user.age_bracket and hasattr(user.age_bracket, "value") else str(user.age_bracket) if user.age_bracket else "unknown",
        "goal": user.goal.value if user.goal and hasattr(user.goal, "value") else str(user.goal) if user.goal else "general fitness",
        "current_streak": streak.current_streak if streak else 0,
        "longest_streak": streak.longest_streak if streak else 0,
        "total_sessions": total_sessions,
        "sessions_last_7d": sessions_7d,
        "sessions_last_30d": sessions_30d,
        "days_since_signup": days_since_signup,
        "consistency_pct": consistency_pct,
        "streak_breaks": streak_breaks,
        "avg_difficulty": round(avg_difficulty, 1) if avg_difficulty else None,
        "avg_enjoyment": round(avg_enjoyment, 1) if avg_enjoyment else None,
    }


def _call_gemini(system_prompt: str, user_content: str) -> str:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None
    from google import genai
    from google.genai import types
    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=user_content,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            response_mime_type="application/json",
        ),
    )
    return response.text


def _default_projection(data: dict) -> dict:
    """Fallback projection when AI is unavailable."""
    cs = data["current_streak"]
    consistency = data["consistency_pct"]
    base_mobility = min(30 + cs * 2, 60)
    base_habit = min(20 + cs * 3, 50)

    return {
        "current_assessment": f"{data['name']} has logged {data['total_sessions']} sessions with a {consistency}% consistency rate. Current streak: {cs} days.",
        "projections": [
            {
                "days": 30, "title": "Foundation Set",
                "mobility": min(base_mobility + 10, 100),
                "consistency": min(consistency + 10, 100),
                "energy": min(40 + cs, 70),
                "habit_strength": min(base_habit + 15, 100),
                "narrative": f"At day 30, movement becomes automatic. {data['name']}'s body starts adapting to daily activation."
            },
            {
                "days": 90, "title": "System Upgraded",
                "mobility": min(base_mobility + 25, 100),
                "consistency": min(consistency + 20, 100),
                "energy": min(50 + cs, 85),
                "habit_strength": min(base_habit + 35, 100),
                "narrative": "Three months in, the nervous system has rewired. Skipping feels wrong. Energy baseline is permanently higher."
            },
            {
                "days": 365, "title": "New Default",
                "mobility": min(base_mobility + 40, 100),
                "consistency": min(consistency + 30, 100),
                "energy": min(60 + cs, 95),
                "habit_strength": min(base_habit + 55, 100),
                "narrative": "One year. Movement is identity, not effort. Mobility, energy, and resilience — all momentum."
            },
        ],
        "insight": "The hardest part is already behind you. Showing up is the skill — and you're building it."
    }


@router.get("/twin/{user_id}")
async def digital_twin(user_id: str, db: DBSession = Depends(get_db)):
    """Digital twin forward simulation — project your body at 30/90/365 days."""
    data = _build_twin_data(user_id, db)

    # Try AI projection
    try:
        user_content = json.dumps(data, indent=2)
        result = await asyncio.wait_for(
            asyncio.to_thread(_call_gemini, _TWIN_PROMPT, user_content),
            timeout=20,
        )
        if result:
            projection = json.loads(result)
        else:
            projection = _default_projection(data)
    except Exception:
        projection = _default_projection(data)

    return _render_twin_page(data, projection)


@router.get("/twin/{user_id}/data")
async def digital_twin_data(user_id: str, db: DBSession = Depends(get_db)):
    """JSON-only digital twin projection — for API consumers and MCP."""
    data = _build_twin_data(user_id, db)

    try:
        user_content = json.dumps(data, indent=2)
        result = await asyncio.wait_for(
            asyncio.to_thread(_call_gemini, _TWIN_PROMPT, user_content),
            timeout=20,
        )
        if result:
            projection = json.loads(result)
        else:
            projection = _default_projection(data)
    except Exception:
        projection = _default_projection(data)

    return {"user": data, "projection": projection}


def _render_twin_page(data: dict, projection: dict) -> HTMLResponse:
    """Render the digital twin visualization page."""
    name = data["name"]
    current_streak = data["current_streak"]
    total_sessions = data["total_sessions"]
    consistency = data["consistency_pct"]

    assessment = projection.get("current_assessment", "")
    insight = projection.get("insight", "")
    projections = projection.get("projections", [])

    # Build projection cards
    cards_html = ""
    for p in projections:
        days = p["days"]
        title = p.get("title", f"Day {days}")
        label = f"{days} DAYS"
        if days == 365:
            label = "1 YEAR"
        elif days == 90:
            label = "90 DAYS"

        # Bar chart for metrics
        metrics = [
            ("MOBILITY", p.get("mobility", 50), "#3fb950"),
            ("CONSISTENCY", p.get("consistency", 50), "#E85D04"),
            ("ENERGY", p.get("energy", 50), "#58a6ff"),
            ("HABIT STRENGTH", p.get("habit_strength", 50), "#d2a8ff"),
        ]

        bars_html = ""
        for metric_name, value, color in metrics:
            bars_html += f"""
            <div class="metric-row">
              <span class="metric-label">{metric_name}</span>
              <div class="metric-bar-bg">
                <div class="metric-bar" style="width:{value}%;background:{color}"></div>
              </div>
              <span class="metric-val" style="color:{color}">{value}</span>
            </div>"""

        narrative = p.get("narrative", "")

        cards_html += f"""
        <div class="projection-card">
          <div class="proj-header">
            <span class="proj-label">{label}</span>
            <span class="proj-title">{title}</span>
          </div>
          {bars_html}
          <div class="proj-narrative">{narrative}</div>
        </div>"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Jerome7 — {name}'s Digital Twin</title>
<meta name="description" content="{name}'s forward simulation — projected body state at 30, 90, 365 days.">
<meta property="og:title" content="Jerome7 Digital Twin — {name}">
<meta property="og:description" content="{total_sessions} sessions logged. {current_streak}-day streak. See the projection.">
<meta property="og:url" content="https://jerome7.com/twin/{data.get('user_id', '')}">
<meta name="twitter:card" content="summary">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700;800&display=swap" rel="stylesheet">
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    background: #0d1117; color: #c9d1d9;
    font-family: 'JetBrains Mono', monospace;
    min-height: 100vh;
  }}
  .container {{ max-width: 720px; margin: 0 auto; padding: 40px 20px; }}

  .nav {{
    display: flex; justify-content: space-between; align-items: center;
    margin-bottom: 60px;
  }}
  .brand {{ font-size: 11px; letter-spacing: 3px; color: #E85D04; text-decoration: none; font-weight: 700; }}
  .nav-links {{ display: flex; gap: 20px; }}
  .nav-links a {{ font-size: 11px; color: #484f58; text-decoration: none; letter-spacing: 1px; }}
  .nav-links a:hover {{ color: #E85D04; }}

  .twin-header {{ text-align: center; margin-bottom: 48px; }}
  .twin-badge {{
    display: inline-flex; align-items: center; gap: 8px;
    background: #161b22; border: 1px solid #E85D04;
    border-radius: 100px; padding: 8px 20px;
    font-size: 10px; letter-spacing: 3px; color: #E85D04;
    margin-bottom: 24px;
  }}
  .twin-pulse {{
    width: 8px; height: 8px; border-radius: 50%;
    background: #E85D04;
    animation: pulse 2s infinite;
  }}
  @keyframes pulse {{
    0%, 100% {{ opacity: 1; }}
    50% {{ opacity: 0.3; }}
  }}
  .twin-name {{
    font-size: 48px; font-weight: 800; color: #f0f6fc;
    line-height: 1.1; letter-spacing: -2px;
  }}
  .twin-sub {{
    font-size: 12px; color: #8b949e; margin-top: 12px; line-height: 1.6;
  }}

  /* Current stats row */
  .now-row {{
    display: grid; grid-template-columns: repeat(3, 1fr);
    gap: 12px; margin-bottom: 48px;
  }}
  @media (max-width: 640px) {{ .now-row {{ grid-template-columns: 1fr; }} }}
  .now-stat {{
    background: #161b22; border: 1px solid #21262d;
    border-radius: 8px; padding: 16px; text-align: center;
  }}
  .now-val {{ font-size: 28px; font-weight: 800; color: #f0f6fc; }}
  .now-val.orange {{ color: #E85D04; }}
  .now-val.green {{ color: #3fb950; }}
  .now-label {{ font-size: 9px; color: #484f58; margin-top: 4px; letter-spacing: 1px; }}

  /* Assessment */
  .assessment {{
    background: #161b22; border: 1px solid #21262d;
    border-radius: 8px; padding: 24px;
    margin-bottom: 48px; font-size: 13px; line-height: 1.8;
    color: #8b949e;
  }}
  .assessment-label {{
    font-size: 10px; letter-spacing: 3px; color: #E85D04;
    margin-bottom: 12px;
  }}

  /* Projection cards */
  .projections {{ display: flex; flex-direction: column; gap: 24px; margin-bottom: 48px; }}
  .projection-card {{
    background: #161b22; border: 1px solid #21262d;
    border-radius: 8px; padding: 24px;
  }}
  .proj-header {{
    display: flex; align-items: center; gap: 12px;
    margin-bottom: 20px;
  }}
  .proj-label {{
    font-size: 10px; letter-spacing: 3px; color: #E85D04;
    background: #0d1117; border: 1px solid #E85D04;
    border-radius: 100px; padding: 4px 12px;
  }}
  .proj-title {{
    font-size: 16px; font-weight: 700; color: #f0f6fc;
  }}

  .metric-row {{
    display: flex; align-items: center; gap: 12px;
    margin-bottom: 8px;
  }}
  .metric-label {{
    font-size: 9px; letter-spacing: 1px; color: #484f58;
    width: 120px; flex-shrink: 0;
  }}
  .metric-bar-bg {{
    flex: 1; height: 6px; background: #21262d;
    border-radius: 3px; overflow: hidden;
  }}
  .metric-bar {{
    height: 100%; border-radius: 3px;
    transition: width 1.5s ease;
  }}
  .metric-val {{
    font-size: 12px; font-weight: 700; width: 32px;
    text-align: right; flex-shrink: 0;
  }}

  .proj-narrative {{
    font-size: 12px; color: #8b949e; margin-top: 16px;
    line-height: 1.7; border-top: 1px solid #21262d;
    padding-top: 16px;
  }}

  /* Insight */
  .insight {{
    text-align: center; padding: 32px;
    background: #161b22; border: 1px solid #E85D04;
    border-radius: 8px; margin-bottom: 48px;
  }}
  .insight-label {{
    font-size: 10px; letter-spacing: 3px; color: #E85D04;
    margin-bottom: 12px;
  }}
  .insight-text {{
    font-size: 14px; color: #f0f6fc; font-weight: 600;
    line-height: 1.6;
  }}

  /* CTA */
  .cta {{ text-align: center; margin-bottom: 40px; }}
  .cta-btn {{
    display: inline-block; padding: 14px 36px;
    background: #E85D04; color: #fff; font-weight: 700;
    font-size: 12px; letter-spacing: 2px; text-decoration: none;
    border-radius: 6px;
  }}
  .cta-btn:hover {{ background: #c24e03; }}
  .cta-sub {{ font-size: 10px; color: #30363d; margin-top: 12px; }}

  .share-row {{
    display: flex; justify-content: center; gap: 16px; margin-top: 16px;
  }}
  .share-link {{
    font-size: 10px; color: #484f58; text-decoration: none;
    letter-spacing: 1px;
  }}
  .share-link:hover {{ color: #E85D04; }}

  .footer {{
    text-align: center; padding: 20px;
    font-size: 10px; color: #21262d;
  }}
  .footer a {{ color: #484f58; text-decoration: none; }}
</style>
</head>
<body>
<div class="container">

  <nav class="nav">
    <a href="/" class="brand">JEROME7</a>
    <div class="nav-links">
      <a href="/timer">TIMER</a>
      <a href="/leaderboard">LEADERBOARD</a>
      <a href="/analytics">ANALYTICS</a>
    </div>
  </nav>

  <div class="twin-header">
    <div class="twin-badge">
      <div class="twin-pulse"></div>
      DIGITAL TWIN
    </div>
    <div class="twin-name">{name}</div>
    <div class="twin-sub">Forward simulation based on {total_sessions} real sessions</div>
  </div>

  <!-- Current state -->
  <div class="now-row">
    <div class="now-stat">
      <div class="now-val orange">{current_streak}</div>
      <div class="now-label">CURRENT STREAK</div>
    </div>
    <div class="now-stat">
      <div class="now-val green">{total_sessions}</div>
      <div class="now-label">TOTAL SESSIONS</div>
    </div>
    <div class="now-stat">
      <div class="now-val">{consistency}%</div>
      <div class="now-label">CONSISTENCY</div>
    </div>
  </div>

  <!-- AI Assessment -->
  <div class="assessment">
    <div class="assessment-label">CURRENT ASSESSMENT</div>
    {assessment}
  </div>

  <!-- Projections -->
  <div class="projections">
    {cards_html}
  </div>

  <!-- Insight -->
  <div class="insight">
    <div class="insight-label">KEY INSIGHT</div>
    <div class="insight-text">{insight}</div>
  </div>

  <!-- CTA -->
  <div class="cta">
    <a href="/timer" class="cta-btn">START TODAY'S SESSION</a>
    <div class="cta-sub">Change the projection. Show up.</div>
    <div class="share-row">
      <a href="https://x.com/intent/tweet?text=My%20Jerome7%20Digital%20Twin%20%E2%80%94%20{current_streak}%20day%20streak.%20See%20my%20projection%3A%20jerome7.com/twin/{data.get('user_id', '')}" target="_blank" class="share-link">SHARE ON X</a>
      <a href="/share/{data.get('user_id', '')}" class="share-link">STREAK CARD</a>
    </div>
  </div>

  <div class="footer">
    <a href="/">jerome7.com</a> · <a href="/live">live</a> · <a href="https://github.com/odominguez7/Jerome7">github</a>
  </div>

</div>
</body>
</html>"""

    return HTMLResponse(content=html)
