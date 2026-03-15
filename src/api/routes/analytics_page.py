"""GET /analytics — visual dashboard. Real-time charts. YC-ready."""

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session as DBSession

from src.db.database import get_db
from src.api.routes.analytics import analytics_overview, analytics_retention

router = APIRouter()


@router.get("/analytics", response_class=HTMLResponse)
def analytics_dashboard(db: DBSession = Depends(get_db)):
    """Live analytics dashboard with charts."""
    data = analytics_overview(db)
    retention = analytics_retention(db)

    total_users = data.get("total_users", 0)
    total_sessions = data.get("total_sessions", 0)
    active_streaks = data.get("active_streaks", 0)
    sessions_24h = data.get("sessions", {}).get("last_24h", 0)
    sessions_7d = data.get("sessions", {}).get("last_7d", 0)
    sessions_30d = data.get("sessions", {}).get("last_30d", 0)
    avg_diff = data.get("avg_difficulty_30d") or 0
    demo = data.get("demographics", {})
    streak_dist = data.get("streak_distribution", {})

    countries = demo.get("countries", {})
    sources = demo.get("sources", {})
    age_brackets = demo.get("age_brackets", {})
    goals = demo.get("goals", {})

    day1 = retention.get("day1_retention_pct", 0)
    day7 = retention.get("day7_retention_pct", 0)
    day30 = retention.get("day30_retention_pct", 0)

    # Country flag map
    _FLAG = {
        "US": "🇺🇸", "CA": "🇨🇦", "MX": "🇲🇽", "BR": "🇧🇷", "AR": "🇦🇷",
        "GB": "🇬🇧", "FR": "🇫🇷", "DE": "🇩🇪", "ES": "🇪🇸", "IT": "🇮🇹",
        "NL": "🇳🇱", "SE": "🇸🇪", "NO": "🇳🇴", "CH": "🇨🇭", "PT": "🇵🇹",
        "PL": "🇵🇱", "TR": "🇹🇷", "RU": "🇷🇺", "UA": "🇺🇦",
        "JP": "🇯🇵", "KR": "🇰🇷", "CN": "🇨🇳", "IN": "🇮🇳", "SG": "🇸🇬",
        "AE": "🇦🇪", "SA": "🇸🇦", "ID": "🇮🇩", "TH": "🇹🇭", "PH": "🇵🇭",
        "AU": "🇦🇺", "NZ": "🇳🇿", "NG": "🇳🇬", "KE": "🇰🇪", "ZA": "🇿🇦",
        "EG": "🇪🇬", "GH": "🇬🇭", "CO": "🇨🇴", "PE": "🇵🇪", "CL": "🇨🇱",
    }

    # Build country rows
    country_rows = ""
    sorted_countries = sorted(countries.items(), key=lambda x: x[1], reverse=True)
    country_total = sum(countries.values()) or 1
    for code, count in sorted_countries[:12]:
        flag = _FLAG.get(code, "🌍")
        pct = round(count / country_total * 100)
        country_rows += f"""
        <div class="bar-row">
          <span class="bar-label">{flag} {code}</span>
          <div class="bar-track"><div class="bar-fill" style="width:{pct}%"></div></div>
          <span class="bar-val">{count}</span>
        </div>"""

    # Source rows
    source_rows = ""
    source_icons = {"discord": "💬", "openclaw": "🦞", "mcp": "🔧", "web": "🌐", "api": "⚙️"}
    for src, count in sorted(sources.items(), key=lambda x: x[1], reverse=True):
        icon = source_icons.get(src, "•")
        pct = round(count / (sum(sources.values()) or 1) * 100)
        source_rows += f"""
        <div class="bar-row">
          <span class="bar-label">{icon} {src}</span>
          <div class="bar-track"><div class="bar-fill" style="width:{pct}%"></div></div>
          <span class="bar-val">{count}</span>
        </div>"""

    # Goal rows
    goal_labels = {
        "build_strength": "Build Strength 💪",
        "move_more": "Move More 🚶",
        "destress": "Destress 🧘",
        "just_try": "Just Try 👀",
    }
    goal_rows = ""
    for g, count in sorted(goals.items(), key=lambda x: x[1], reverse=True):
        pct = round(count / (sum(goals.values()) or 1) * 100)
        goal_rows += f"""
        <div class="bar-row">
          <span class="bar-label">{goal_labels.get(g, g)}</span>
          <div class="bar-track"><div class="bar-fill bar-fill-green" style="width:{pct}%"></div></div>
          <span class="bar-val">{count}</span>
        </div>"""

    # Age bracket rows
    age_rows = ""
    for bracket, count in sorted(age_brackets.items()):
        pct = round(count / (sum(age_brackets.values()) or 1) * 100)
        age_rows += f"""
        <div class="bar-row">
          <span class="bar-label">{bracket}</span>
          <div class="bar-track"><div class="bar-fill bar-fill-purple" style="width:{pct}%"></div></div>
          <span class="bar-val">{count}</span>
        </div>"""

    # Streak distribution chart
    streak_labels = ["1-3", "4-7", "8-14", "15-30", "31+"]
    streak_max = max(streak_dist.values()) if streak_dist else 1
    streak_bars = ""
    for label in streak_labels:
        val = streak_dist.get(label, 0)
        h = max(4, round(val / max(streak_max, 1) * 80))
        streak_bars += f"""
        <div class="col-bar-wrap">
          <span class="col-val">{val}</span>
          <div class="col-bar" style="height:{h}px"></div>
          <span class="col-label">{label}</span>
        </div>"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Jerome7 — Analytics</title>
<meta name="description" content="Live analytics. Who's showing up. Where. Why.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700;800&display=swap" rel="stylesheet">
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    background: #0d1117; color: #c9d1d9;
    font-family: 'JetBrains Mono', monospace;
    min-height: 100vh; padding: 40px 20px;
  }}
  .container {{ max-width: 900px; margin: 0 auto; }}

  /* Nav */
  .nav {{
    display: flex; justify-content: space-between; align-items: center;
    margin-bottom: 48px;
  }}
  .brand {{ font-size: 11px; letter-spacing: 3px; color: #E85D04; text-decoration: none; font-weight: 700; }}
  .nav-links {{ display: flex; gap: 20px; }}
  .nav-links a {{ font-size: 11px; color: #484f58; text-decoration: none; letter-spacing: 1px; }}
  .nav-links a:hover {{ color: #E85D04; }}

  /* Header */
  .page-header {{ margin-bottom: 48px; }}
  .page-header h1 {{ font-size: 32px; font-weight: 800; color: #f0f6fc; margin-bottom: 8px; }}
  .page-header p {{ font-size: 13px; color: #8b949e; }}
  .live-badge {{
    display: inline-flex; align-items: center; gap: 6px;
    background: #161b22; border: 1px solid #21262d;
    border-radius: 100px; padding: 4px 12px;
    font-size: 10px; letter-spacing: 1px; color: #3fb950;
    margin-top: 12px;
  }}
  .live-dot {{
    width: 6px; height: 6px; border-radius: 50%;
    background: #3fb950;
    animation: pulse 2s infinite;
  }}
  @keyframes pulse {{
    0%, 100% {{ opacity: 1; }}
    50% {{ opacity: 0.4; }}
  }}

  /* KPI Grid */
  .kpi-grid {{
    display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
    gap: 16px; margin-bottom: 48px;
  }}
  .kpi {{
    background: #161b22; border: 1px solid #21262d;
    border-radius: 8px; padding: 20px 16px;
  }}
  .kpi-val {{
    font-size: 36px; font-weight: 800; color: #f0f6fc;
    line-height: 1;
  }}
  .kpi-val.orange {{ color: #E85D04; }}
  .kpi-val.green {{ color: #3fb950; }}
  .kpi-val.blue {{ color: #58a6ff; }}
  .kpi-label {{ font-size: 10px; color: #484f58; margin-top: 8px; letter-spacing: 1px; }}

  /* Section */
  .section {{ margin-bottom: 48px; }}
  .section-label {{
    font-size: 10px; letter-spacing: 3px; color: #E85D04;
    margin-bottom: 20px; text-transform: uppercase;
  }}

  /* Two col */
  .two-col {{ display: grid; grid-template-columns: 1fr 1fr; gap: 24px; margin-bottom: 48px; }}
  @media (max-width: 640px) {{ .two-col {{ grid-template-columns: 1fr; }} }}

  .panel {{
    background: #161b22; border: 1px solid #21262d;
    border-radius: 8px; padding: 20px;
  }}
  .panel-title {{ font-size: 10px; letter-spacing: 2px; color: #E85D04; margin-bottom: 16px; }}

  /* Bar chart */
  .bar-row {{
    display: flex; align-items: center; gap: 10px;
    margin-bottom: 10px;
  }}
  .bar-label {{ font-size: 11px; color: #8b949e; min-width: 110px; }}
  .bar-track {{
    flex: 1; height: 6px; background: #21262d; border-radius: 3px; overflow: hidden;
  }}
  .bar-fill {{
    height: 100%; background: #E85D04; border-radius: 3px;
    transition: width 0.8s ease;
  }}
  .bar-fill-green {{ background: #3fb950; }}
  .bar-fill-purple {{ background: #bc8cff; }}
  .bar-val {{ font-size: 11px; color: #484f58; min-width: 24px; text-align: right; }}

  /* Column bar chart */
  .col-chart {{
    display: flex; align-items: flex-end; gap: 12px;
    height: 120px; padding: 0 8px;
  }}
  .col-bar-wrap {{
    display: flex; flex-direction: column; align-items: center; gap: 4px; flex: 1;
  }}
  .col-bar {{
    width: 100%; background: #E85D04; border-radius: 3px 3px 0 0;
    min-height: 4px;
  }}
  .col-label {{ font-size: 9px; color: #484f58; }}
  .col-val {{ font-size: 10px; color: #8b949e; }}

  /* Retention */
  .retention-grid {{
    display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px;
  }}
  .ret-card {{
    background: #161b22; border: 1px solid #21262d;
    border-radius: 8px; padding: 20px; text-align: center;
  }}
  .ret-val {{ font-size: 28px; font-weight: 800; color: #3fb950; }}
  .ret-label {{ font-size: 10px; color: #484f58; margin-top: 6px; letter-spacing: 1px; }}

  /* Difficulty meter */
  .diff-meter {{
    display: flex; align-items: center; gap: 12px; margin-top: 8px;
  }}
  .diff-bar-track {{
    flex: 1; height: 8px; background: #21262d; border-radius: 4px; overflow: hidden;
  }}
  .diff-bar-fill {{
    height: 100%; border-radius: 4px;
    background: linear-gradient(90deg, #3fb950, #E85D04, #f85149);
  }}
  .diff-num {{ font-size: 24px; font-weight: 800; color: #f0f6fc; }}

  .footer {{
    border-top: 1px solid #21262d; padding-top: 24px; margin-top: 48px;
    display: flex; justify-content: space-between; align-items: center;
  }}
  .footer a {{ font-size: 11px; color: #484f58; text-decoration: none; }}
  .footer a:hover {{ color: #E85D04; }}
  .auto-refresh {{ font-size: 10px; color: #30363d; }}
</style>
</head>
<body>
<div class="container">

  <nav class="nav">
    <a href="/" class="brand">JEROME7</a>
    <div class="nav-links">
      <a href="/timer">TIMER</a>
      <a href="/leaderboard">LEADERBOARD</a>
      <a href="/agents">AGENTS</a>
      <a href="https://discord.gg/5AZP8DbEJm">DISCORD</a>
      <a href="https://github.com/odominguez7/Jerome7">GITHUB</a>
    </div>
  </nav>

  <div class="page-header">
    <h1>Who's showing up.</h1>
    <p>Real-time data from builders worldwide. Updated on every request.</p>
    <div class="live-badge">
      <div class="live-dot"></div>
      LIVE
    </div>
  </div>

  <!-- KPIs -->
  <div class="kpi-grid">
    <div class="kpi">
      <div class="kpi-val orange">{total_users}</div>
      <div class="kpi-label">TOTAL BUILDERS</div>
    </div>
    <div class="kpi">
      <div class="kpi-val green">{total_sessions}</div>
      <div class="kpi-label">SESSIONS LOGGED</div>
    </div>
    <div class="kpi">
      <div class="kpi-val blue">{active_streaks}</div>
      <div class="kpi-label">ACTIVE STREAKS</div>
    </div>
    <div class="kpi">
      <div class="kpi-val">{sessions_24h}</div>
      <div class="kpi-label">SHOWED UP TODAY</div>
    </div>
    <div class="kpi">
      <div class="kpi-val">{sessions_7d}</div>
      <div class="kpi-label">THIS WEEK</div>
    </div>
    <div class="kpi">
      <div class="kpi-val">{sessions_30d}</div>
      <div class="kpi-label">THIS MONTH</div>
    </div>
  </div>

  <!-- Retention -->
  <div class="section">
    <div class="section-label">RETENTION</div>
    <div class="retention-grid">
      <div class="ret-card">
        <div class="ret-val">{day1}%</div>
        <div class="ret-label">DAY 1</div>
      </div>
      <div class="ret-card">
        <div class="ret-val">{day7}%</div>
        <div class="ret-label">DAY 7</div>
      </div>
      <div class="ret-card">
        <div class="ret-val">{day30}%</div>
        <div class="ret-label">DAY 30</div>
      </div>
    </div>
  </div>

  <!-- Streak distribution -->
  <div class="section">
    <div class="section-label">STREAK DISTRIBUTION</div>
    <div class="panel">
      <div class="col-chart">
        {streak_bars}
      </div>
    </div>
  </div>

  <!-- Two col: countries + sources -->
  <div class="two-col">
    <div class="panel">
      <div class="panel-title">BY COUNTRY</div>
      {country_rows if country_rows else '<div style="color:#484f58;font-size:12px">No data yet</div>'}
    </div>
    <div class="panel">
      <div class="panel-title">BY SOURCE</div>
      {source_rows if source_rows else '<div style="color:#484f58;font-size:12px">No data yet</div>'}
    </div>
  </div>

  <!-- Two col: goals + age -->
  <div class="two-col">
    <div class="panel">
      <div class="panel-title">BY GOAL</div>
      {goal_rows if goal_rows else '<div style="color:#484f58;font-size:12px">No data yet</div>'}
    </div>
    <div class="panel">
      <div class="panel-title">BY AGE BRACKET</div>
      {age_rows if age_rows else '<div style="color:#484f58;font-size:12px">No data yet</div>'}
    </div>
  </div>

  <!-- Avg difficulty -->
  <div class="section">
    <div class="section-label">AVG SESSION DIFFICULTY (30d)</div>
    <div class="panel">
      <div class="diff-meter">
        <div class="diff-num">{round(avg_diff, 1) if avg_diff else "—"}</div>
        <div class="diff-bar-track">
          <div class="diff-bar-fill" style="width:{round(avg_diff / 5 * 100) if avg_diff else 0}%"></div>
        </div>
        <span style="font-size:11px;color:#484f58">/ 5.0</span>
      </div>
      <div style="font-size:11px;color:#484f58;margin-top:12px">1 = easy · 3 = good · 5 = hard. Gemini adapts next session.</div>
    </div>
  </div>

  <div class="footer">
    <a href="/">← jerome7.com</a>
    <div class="auto-refresh">auto-refreshes every 60s</div>
    <a href="/analytics/overview">raw JSON →</a>
  </div>

</div>
<script>setTimeout(() => location.reload(), 60000);</script>
</body>
</html>"""
    return HTMLResponse(content=html)
