"""GET / — jerome7.com landing page. Lean, fast, focused."""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from src.agents.session_types import today_session_type
from src.api.meta import head_meta, nav_html

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def landing():
    session_type = today_session_type()
    type_labels = {
        "breathwork": "Guided Breathwork",
        "meditation": "Focus Meditation",
        "reflection": "Reflection",
        "preparation": "Preparation for the Day",
    }
    today_label = type_labels.get(session_type, session_type.title())

    _meta = head_meta()
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Jerome7 | 7 minutes. Before you ship.</title>
<meta name="description" content="AI-powered 7-minute performance protocol for builders. Breathwork, meditation, focus. Open source.">
{_meta}
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700;800&display=swap" rel="stylesheet">
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    background: #0d1117; color: #c9d1d9;
    font-family: 'JetBrains Mono', monospace;
    line-height: 1.6; overflow-x: hidden;
  }}

  .hero {{
    min-height: 100vh; display: flex; flex-direction: column;
    align-items: center; justify-content: center;
    text-align: center; padding: 80px 20px 40px;
  }}
  h1 {{
    font-size: clamp(32px, 8vw, 64px); font-weight: 800;
    color: #f0f6fc; line-height: 1.1; margin-bottom: 20px;
  }}
  h1 span {{ color: #E85D04; }}
  .tagline {{
    font-size: 15px; color: #8b949e; margin-bottom: 40px; max-width: 480px;
  }}

  .btn {{
    padding: 18px 48px; border-radius: 100px; border: none;
    cursor: pointer; font-family: inherit; font-size: 16px;
    font-weight: 700; letter-spacing: 1px; text-decoration: none;
    transition: all 0.2s; display: inline-block;
  }}
  .btn-primary {{ background: #E85D04; color: #fff; }}
  .btn-primary:hover {{ background: #ff6b1a; transform: translateY(-1px); }}

  .today-badge {{
    display: inline-flex; align-items: center; gap: 8px;
    background: #161b22; border: 1px solid #30363d;
    border-radius: 100px; padding: 8px 20px;
    font-size: 11px; letter-spacing: 1px; color: #8b949e;
    margin-top: 32px;
  }}
  .today-badge .dot {{
    width: 8px; height: 8px; border-radius: 50%;
    background: #3fb950; animation: pulse 2s infinite;
  }}
  @keyframes pulse {{ 0%,100% {{ opacity: 1; }} 50% {{ opacity: 0.4; }} }}

  /* ── PROOF ── */
  .proof {{
    display: flex; gap: 32px; justify-content: center;
    padding: 40px 20px; border-top: 1px solid #161b22;
  }}
  .proof-item {{ text-align: center; }}
  .proof-num {{ font-size: 28px; font-weight: 800; color: #E85D04; }}
  .proof-label {{ font-size: 9px; letter-spacing: 2px; color: #484f58; }}

  /* ── SECTIONS ── */
  section {{
    max-width: 640px; margin: 0 auto; padding: 60px 20px;
  }}
  .section-label {{
    font-size: 10px; letter-spacing: 3px; color: #E85D04; margin-bottom: 16px;
  }}
  h2 {{
    font-size: 22px; font-weight: 700; color: #f0f6fc; margin-bottom: 12px;
  }}
  p {{ color: #8b949e; font-size: 14px; margin-bottom: 16px; }}

  .science-grid {{
    display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-top: 24px;
  }}
  .science-card {{
    background: #161b22; border: 1px solid #21262d;
    border-radius: 10px; padding: 16px;
  }}
  .science-num {{ font-size: 28px; font-weight: 800; color: #E85D04; margin-bottom: 2px; }}
  .science-title {{ font-size: 12px; color: #f0f6fc; font-weight: 700; margin-bottom: 4px; }}
  .science-cite {{ font-size: 8px; color: #30363d; margin-top: 6px; }}

  .quote {{
    max-width: 640px; margin: 0 auto; padding: 40px 20px;
    border-left: 3px solid #E85D04; padding-left: 24px;
  }}
  .quote-text {{
    font-size: 13px; color: #8b949e; line-height: 1.8; font-style: italic;
  }}
  .quote-author {{ font-size: 11px; color: #484f58; margin-top: 12px; }}

  /* ── CTA BOTTOM ── */
  .bottom-cta {{
    text-align: center; padding: 60px 20px;
  }}
  .bottom-cta h2 {{ font-size: 28px; margin-bottom: 24px; }}

  footer {{
    text-align: center; padding: 32px 24px;
    border-top: 1px solid #21262d; color: #484f58; font-size: 12px;
  }}
  footer a {{ color: #484f58; text-decoration: none; margin: 0 8px; }}

  @media (max-width: 480px) {{
    h1 {{ font-size: 28px; }}
    .science-grid {{ grid-template-columns: 1fr; }}
    .proof {{ gap: 20px; }}
    .proof-num {{ font-size: 22px; }}
  }}
</style>
</head>
<body>

{nav_html()}

<!-- HERO -->
<div class="hero">
  <h1><span>7</span> minutes.<br>Before you ship.</h1>
  <div class="tagline">AI-guided breathwork, meditation, and focus for builders. Same session for every builder on Earth, every day.</div>
  <a href="/timer" class="btn btn-primary">START NOW</a>
  <div class="today-badge">
    <span class="dot"></span>
    TODAY: {today_label.upper()}
  </div>
</div>

<!-- SOCIAL PROOF -->
<div class="proof" id="proofBar">
  <div class="proof-item">
    <div class="proof-num" id="proofBuilders">--</div>
    <div class="proof-label">BUILDERS</div>
  </div>
  <div class="proof-item">
    <div class="proof-num" id="proofCountries">--</div>
    <div class="proof-label">COUNTRIES</div>
  </div>
  <div class="proof-item">
    <div class="proof-num" id="proofSessions">--</div>
    <div class="proof-label">SESSIONS</div>
  </div>
</div>

<!-- SCIENCE -->
<section>
  <div class="section-label">THE SCIENCE</div>
  <h2>Not vibes. Neuroscience.</h2>
  <div class="science-grid">
    <div class="science-card">
      <div class="science-num">-25%</div>
      <div class="science-title">Cortisol</div>
      <div class="science-cite">Ma et al., 2017</div>
    </div>
    <div class="science-card">
      <div class="science-num">+14%</div>
      <div class="science-title">Focus</div>
      <div class="science-cite">Zeidan et al., 2010</div>
    </div>
    <div class="science-card">
      <div class="science-num">66</div>
      <div class="science-title">Days to habit</div>
      <div class="science-cite">Lally et al., 2010</div>
    </div>
    <div class="science-card">
      <div class="science-num">-26%</div>
      <div class="science-title">Anxiety</div>
      <div class="science-cite">Garcia-Argibay, 2019</div>
    </div>
  </div>
</section>

<!-- ORIGIN -->
<div class="quote">
  <div class="quote-text">
    "80 lbs overweight. Started with 7 minutes a day.
    That became the Boston Marathon. Then Ironman 70.3. Then MIT.
    Not because I was exceptional. Because I was consistent."
  </div>
  <div class="quote-author">Omar, Founder</div>
</div>

<!-- BOTTOM CTA -->
<div class="bottom-cta">
  <h2>Your 7 minutes are waiting.</h2>
  <a href="/timer" class="btn btn-primary">START NOW</a>
</div>

<!-- FOOTER -->
<footer>
  <div style="margin-bottom:8px">Personally funded. Open source. MIT.</div>
  <div>
    <a href="/globe">Globe</a>
    <a href="/privacy">Privacy</a>
    <a href="/terms">Terms</a>
    <a href="https://github.com/odominguez7/Jerome7" target="_blank" rel="noopener noreferrer">GitHub</a>
  </div>
</footer>

<script>
(async function() {{
  try {{
    const resp = await fetch('/stats');
    const data = await resp.json();
    const b = document.getElementById('proofBuilders');
    const c = document.getElementById('proofCountries');
    const s = document.getElementById('proofSessions');
    if (b) b.textContent = data.total_jeromes || 0;
    if (c) c.textContent = data.countries || 0;
    if (s) s.textContent = data.total_sessions || 0;
  }} catch {{}}
}})();
</script>
</body>
</html>"""
    return HTMLResponse(
        content=html,
        headers={"Cache-Control": "public, max-age=300"},
    )
