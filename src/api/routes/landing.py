"""GET / — jerome7.com landing page. Wellness-first. Blueprint-aligned."""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from src.agents.session_types import today_session_type
from src.api.meta import head_meta

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
<title>Jerome7 | 7 minutes. Show up. The world gets better.</title>
<meta name="description" content="Daily 7-minute guided wellness for builders. Breathwork, meditation, reflection. Powered by AI agents. Personally funded. Open source.">
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

  /* ── NAV ── */
  .nav {{
    position: fixed; top: 0; left: 0; right: 0; z-index: 100;
    display: flex; align-items: center; justify-content: space-between;
    padding: 12px 24px;
    background: rgba(13,17,23,0.92);
    backdrop-filter: blur(12px);
    border-bottom: 1px solid #21262d;
  }}
  .nav-brand {{
    font-size: 13px; font-weight: 800; color: #E85D04;
    letter-spacing: 2px; text-decoration: none;
  }}
  .nav-links {{ display: flex; gap: 20px; align-items: center; }}
  .nav-links a {{
    font-size: 12px; color: #8b949e; text-decoration: none;
    letter-spacing: 0.5px; transition: color 0.2s;
  }}
  .nav-links a:hover {{ color: #f0f6fc; }}
  .nav-cta {{
    color: #E85D04 !important; font-weight: 700;
    padding: 6px 14px; border: 1px solid #E85D04;
    border-radius: 100px;
  }}
  .nav-cta:hover {{ background: #E85D04; color: #fff !important; }}

  /* ── HERO ── */
  .hero {{
    min-height: 100vh; display: flex; flex-direction: column;
    align-items: center; justify-content: center;
    text-align: center; padding: 80px 20px 40px;
  }}
  .brand-label {{
    font-size: 11px; letter-spacing: 4px; color: #E85D04; margin-bottom: 32px;
  }}
  h1 {{
    font-size: clamp(32px, 8vw, 64px); font-weight: 800;
    color: #f0f6fc; line-height: 1.1; margin-bottom: 16px;
  }}
  h1 span {{ color: #E85D04; }}
  .tagline {{
    font-size: 15px; color: #8b949e; margin-bottom: 12px; max-width: 520px;
  }}
  .tagline-sub {{
    font-size: 13px; color: #484f58; margin-bottom: 48px; max-width: 480px;
  }}
  .cta-row {{ display: flex; gap: 16px; flex-wrap: wrap; justify-content: center; }}

  .btn {{
    padding: 14px 32px; border-radius: 100px; border: none;
    cursor: pointer; font-family: inherit; font-size: 14px;
    font-weight: 700; letter-spacing: 1px; text-decoration: none;
    transition: all 0.2s;
  }}
  .btn-primary {{ background: #E85D04; color: #fff; padding: 18px 48px; font-size: 16px; }}
  .btn-primary:hover {{ background: #ff6b1a; transform: translateY(-1px); }}
  .btn-ghost {{
    background: transparent; color: #E85D04;
    border: 1px solid #E85D04;
  }}
  .btn-ghost:hover {{ background: rgba(232,93,4,0.1); }}

  .today-badge {{
    display: inline-flex; align-items: center; gap: 8px;
    background: #161b22; border: 1px solid #30363d;
    border-radius: 100px; padding: 8px 20px;
    font-size: 11px; letter-spacing: 1px; color: #8b949e;
    margin-top: 40px;
  }}
  .today-badge .dot {{
    width: 8px; height: 8px; border-radius: 50%;
    background: #3fb950; animation: pulse 2s infinite;
  }}
  @keyframes pulse {{ 0%,100% {{ opacity: 1; }} 50% {{ opacity: 0.4; }} }}

  .cli-strip {{
    background: #161b22; border: 1px solid #30363d;
    border-radius: 8px; padding: 14px 20px;
    margin-top: 24px; display: inline-flex;
    align-items: center; gap: 12px;
  }}
  .cli-strip code {{ font-size: 13px; color: #7ee787; }}
  .copy-btn {{
    background: transparent; border: 1px solid #30363d;
    color: #8b949e; font-family: inherit; font-size: 11px;
    padding: 4px 10px; border-radius: 6px; cursor: pointer;
  }}
  .copy-btn:hover {{ border-color: #E85D04; color: #E85D04; }}

  /* ── SECTIONS ── */
  section {{
    max-width: 640px; margin: 0 auto; padding: 80px 20px;
  }}
  .section-label {{
    font-size: 10px; letter-spacing: 3px; color: #E85D04; margin-bottom: 24px;
  }}
  h2 {{
    font-size: 24px; font-weight: 700; color: #f0f6fc; margin-bottom: 16px;
  }}
  p {{ color: #8b949e; font-size: 14px; margin-bottom: 16px; }}

  /* ── QUOTE ── */
  .quote {{
    max-width: 640px; margin: 0 auto; padding: 60px 20px;
    border-left: 3px solid #E85D04; padding-left: 24px;
  }}
  .quote-text {{
    font-size: 14px; color: #c9d1d9; line-height: 1.8;
    font-style: italic;
  }}
  .quote-author {{
    font-size: 12px; color: #484f58; margin-top: 16px;
  }}

  /* ── HOW IT WORKS ── */
  .steps {{ display: flex; flex-direction: column; gap: 24px; margin-top: 32px; }}
  .step {{ display: flex; gap: 16px; align-items: flex-start; }}
  .step-num {{ font-size: 24px; font-weight: 800; color: #E85D04; min-width: 32px; }}
  .step-text {{ font-size: 14px; color: #c9d1d9; }}
  .step-text strong {{ color: #f0f6fc; }}
  .step-sub {{ font-size: 12px; color: #484f58; margin-top: 4px; }}

  /* ── SESSION TYPES ── */
  .types {{ display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-top: 32px; }}
  .type-card {{
    background: #161b22; border: 1px solid #21262d;
    border-radius: 8px; padding: 16px 20px;
  }}
  .type-label {{ font-size: 9px; letter-spacing: 2px; margin-bottom: 8px; font-weight: 700; }}
  .type-name {{ font-size: 14px; font-weight: 700; color: #f0f6fc; margin-bottom: 4px; }}
  .type-desc {{ font-size: 11px; color: #484f58; }}

  /* ── AGENTS ── */
  .agents {{ display: flex; flex-direction: column; gap: 12px; margin-top: 32px; }}
  .agent {{
    background: #161b22; border: 1px solid #21262d;
    border-radius: 8px; padding: 16px 20px;
    display: flex; gap: 16px; align-items: flex-start;
  }}
  .agent-icon {{ font-size: 11px; font-weight: 800; color: #E85D04; min-width: 80px; }}
  .agent-desc {{ font-size: 12px; color: #8b949e; }}

  /* ── JEROME# ── */
  .identity-block {{
    background: #161b22; border: 1px solid #30363d;
    border-radius: 12px; padding: 24px;
    margin-top: 32px; font-size: 13px; color: #c9d1d9;
    line-height: 2;
  }}
  .identity-block .highlight {{ color: #E85D04; font-weight: 700; }}

  /* ── SCIENCE ── */
  .science-stats {{
    display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-top: 24px;
  }}
  .science-stat {{
    background: #161b22; border: 1px solid #21262d;
    border-radius: 8px; padding: 16px; text-align: center;
  }}
  .science-num {{ font-size: 24px; font-weight: 800; color: #3fb950; }}
  .science-label {{ font-size: 10px; color: #484f58; letter-spacing: 1px; margin-top: 4px; }}

  /* ── FOOTER ── */
  .footer {{
    text-align: center; padding: 40px 20px 60px;
    border-top: 1px solid #21262d;
  }}
  .footer-brand {{ font-size: 11px; letter-spacing: 3px; color: #E85D04; margin-bottom: 8px; }}
  .footer-text {{ font-size: 12px; color: #484f58; }}
  .footer a {{ color: #E85D04; text-decoration: none; }}
  .bottom-cta {{
    display: inline-block; margin-top: 32px;
    padding: 14px 40px; background: #E85D04; color: #fff;
    border-radius: 100px; font-family: inherit; font-size: 14px;
    font-weight: 700; text-decoration: none; letter-spacing: 1px;
  }}
  .bottom-cta:hover {{ background: #ff6b1a; }}

  /* ── STAR CTA ── */
  .star-bar {{
    display: flex; align-items: center; justify-content: center;
    gap: 12px; margin-top: 48px; padding: 20px;
    border: 1px solid #21262d; border-radius: 8px; background: #161b22;
  }}
  .star-text {{ font-size: 13px; color: #8b949e; }}
  .star-btn {{
    display: inline-flex; align-items: center; gap: 6px;
    padding: 8px 20px; background: #21262d; border: 1px solid #30363d;
    border-radius: 6px; color: #f0f6fc; font-family: inherit;
    font-size: 12px; font-weight: 600; text-decoration: none;
    transition: all 0.2s;
  }}
  .star-btn:hover {{ background: #30363d; border-color: #E85D04; }}

  @media (max-width: 480px) {{
    .hero {{ padding: 80px 20px 60px; }}
    h1 {{ font-size: 28px; }}
    section {{ padding: 60px 16px; }}
    .nav-links {{ gap: 12px; }}
    .nav-links a {{ font-size: 11px; }}
    .types {{ grid-template-columns: 1fr; }}
    .science-stats {{ grid-template-columns: 1fr; }}
  }}
</style>
</head>
<body>

<!-- NAV -->
<nav class="nav">
  <a href="/" class="nav-brand">JEROME7</a>
  <div class="nav-links">
    <a href="/globe">Globe</a>
    <a href="https://discord.gg/5AZP8DbEJm">Discord</a>
    <a href="https://github.com/odominguez7/Jerome7">GitHub</a>
    <a href="/timer" class="nav-cta">START</a>
  </div>
</nav>

<!-- HERO -->
<div class="hero">
  <div class="brand-label">JEROME7</div>
  <h1><span>7</span> minutes.<br>Show up.<br>The world gets better.</h1>
  <div class="tagline">Daily guided breathwork, meditation, and reflection for builders, coders, and dreamers.</div>
  <div class="tagline-sub">No exercise. No equipment. Just earphones and a place to sit.</div>

  <div class="cta-row">
    <a href="/timer" class="btn btn-primary">START YOUR 7 MINUTES</a>
    <a href="/globe" class="btn btn-ghost">THE GLOBE</a>
  </div>

  <div class="today-badge">
    <span class="dot"></span>
    TODAY: {today_label.upper()}
  </div>

  <div class="cli-strip">
    <code id="cli-cmd">npx jerome7 --wellness</code>
    <button class="copy-btn" onclick="copyCli()">COPY</button>
  </div>
</div>

<!-- QUOTE -->
<div class="quote">
  <div class="quote-text">
    "I was 80 lbs overweight. Couldn't run a mile. Started with 7 minutes a day.
    That became the Boston Marathon. Then Ironman 70.3. Then MIT.
    Not because I was exceptional. Because I was consistent."
  </div>
  <div class="quote-author">— Omar, Jerome7 (Founder)</div>
</div>

<!-- WHAT IS JEROME7 -->
<section>
  <div class="section-label">WHAT IS JEROME7</div>
  <h2>A daily 7-minute guided session.</h2>
  <p>Breathwork, meditation, reflection, or preparation, powered by AI agents that learn your patterns and match you with accountability partners worldwide.</p>
  <p>The activity changes every 24 hours. Same session for every builder on Earth. Like Wordle, but for your mind.</p>
</section>

<!-- HOW IT WORKS -->
<section>
  <div class="section-label">HOW IT WORKS</div>
  <h2>One session. Everyone. Every day.</h2>

  <div class="steps">
    <div class="step">
      <div class="step-num">1</div>
      <div>
        <div class="step-text"><strong>SHOW UP</strong></div>
        <div class="step-sub">Hit start. 7 minutes of guided audio. Same session for everyone on earth.</div>
      </div>
    </div>
    <div class="step">
      <div class="step-num">2</div>
      <div>
        <div class="step-text"><strong>BUILD YOUR CHAIN</strong></div>
        <div class="step-sub">Complete sessions daily. Miss 3 and it breaks. 1 save per 30 days.</div>
      </div>
    </div>
    <div class="step">
      <div class="step-num">3</div>
      <div>
        <div class="step-text"><strong>NEVER WALK ALONE</strong></div>
        <div class="step-sub">5 AI agents watch your back. Your pod has your six.</div>
      </div>
    </div>
  </div>
</section>

<!-- THE 4 SESSION TYPES -->
<section>
  <div class="section-label">ROTATING DAILY</div>
  <h2>4 session types. One each day.</h2>
  <p>The session rotates automatically. You don't choose. You show up.</p>

  <div class="types">
    <div class="type-card">
      <div class="type-label" style="color:#4ecdc4">DAY A</div>
      <div class="type-name">Breathwork</div>
      <div class="type-desc">Box breathing. 4-4-4-4 count. Calm your nervous system.</div>
    </div>
    <div class="type-card">
      <div class="type-label" style="color:#79c0ff">DAY B</div>
      <div class="type-name">Meditation</div>
      <div class="type-desc">Focus meditation. Breath awareness. Gentle redirects.</div>
    </div>
    <div class="type-card">
      <div class="type-label" style="color:#b392f0">DAY C</div>
      <div class="type-name">Reflection</div>
      <div class="type-desc">Journaling prompt. Silent reflection. Synthesis.</div>
    </div>
    <div class="type-card">
      <div class="type-label" style="color:#e8713a">DAY D</div>
      <div class="type-name">Preparation</div>
      <div class="type-desc">Visualization. 3 priorities. Power statement.</div>
    </div>
  </div>
</section>

<!-- YOUR JEROME# -->
<section>
  <div class="section-label">YOUR IDENTITY</div>
  <h2>Every user is Jerome#.</h2>
  <p>Your number. Your identity. First come, first served.</p>

  <div class="identity-block">
    <span class="highlight">Jerome7</span>  &rarr; Omar (Founder)<br>
    <span class="highlight">Jerome8</span>  &rarr; You? &rarr; <a href="/timer" style="color:#E85D04">jerome7.com/timer</a><br>
    <span class="highlight">Jerome9</span>  &rarr; The next builder who shows up<br>
    <span style="color:#484f58">...</span><br>
    <span class="highlight">Jerome42</span> &rarr; Someone, somewhere, showing up today
  </div>
</section>

<!-- THE 5 AI AGENTS -->
<section>
  <div class="section-label">UNDER THE HOOD</div>
  <h2>5 AI agents. One mission.</h2>
  <p>Jerome7 isn't a meditation app. It's a coordination system: agents that learn your patterns, predict burnout, and match you with accountability partners.</p>

  <div class="agents">
    <div class="agent">
      <div class="agent-icon">COACH</div>
      <div class="agent-desc">Generates your daily session via Gemini 2.5 Flash. Reads your feedback. Adjusts tomorrow.</div>
    </div>
    <div class="agent">
      <div class="agent-icon">NUDGE</div>
      <div class="agent-desc">Learns your skip patterns. Fires a reminder <em>before</em> you ghost. Never shames.</div>
    </div>
    <div class="agent">
      <div class="agent-icon">STREAK</div>
      <div class="agent-desc">3-miss rule. Miss 3 days, chain breaks. 1 save per 30 days.</div>
    </div>
    <div class="agent">
      <div class="agent-icon">COMMUNITY</div>
      <div class="agent-desc">Matches pods of 3-5 builders by timezone + engagement level.</div>
    </div>
    <div class="agent">
      <div class="agent-icon">SCHEDULER</div>
      <div class="agent-desc">Finds your optimal session window from your history.</div>
    </div>
  </div>

  <p style="margin-top:24px;font-size:12px;color:#484f58">
    Every agent communicates via <a href="https://developers.googleblog.com/en/a2a-a-new-era-of-agent-interoperability/" style="color:#79c0ff;text-decoration:none">A2A protocol</a>.
    External AI agents can join — <a href="/.well-known/agent.json" style="color:#79c0ff;text-decoration:none">see our AgentCard</a>.
  </p>
</section>

<!-- SCIENCE -->
<section>
  <div class="section-label">BACKED BY SCIENCE</div>
  <h2>7 minutes is enough.</h2>
  <p><a href="https://pmc.ncbi.nlm.nih.gov/articles/PMC10917090/" style="color:#79c0ff;text-decoration:none">Peking University research (2023)</a> confirms 7-minute breathing reduces stress, increases serenity, and decreases anxiety.</p>

  <div class="science-stats">
    <div class="science-stat">
      <div class="science-num">p&lt;.001</div>
      <div class="science-label">STRESS REDUCTION</div>
    </div>
    <div class="science-stat">
      <div class="science-num">p&lt;.001</div>
      <div class="science-label">INCREASED SERENITY</div>
    </div>
    <div class="science-stat">
      <div class="science-num">p&lt;.001</div>
      <div class="science-label">DECREASED ANXIETY</div>
    </div>
    <div class="science-stat">
      <div class="science-num">7 min</div>
      <div class="science-label">IS ALL IT TAKES</div>
    </div>
  </div>
</section>

<!-- THE GLOBE -->
<section>
  <div class="section-label">THE GLOBE</div>
  <h2>Every dot is a builder who showed up.</h2>
  <p><a href="/globe" style="color:#E85D04;text-decoration:none;font-size:16px;font-weight:700">See the world light up &rarr;</a></p>
</section>

<!-- OPEN SOURCE -->
<section>
  <div class="section-label">OPEN SOURCE</div>
  <h2>MCP-native. Agent-ready.</h2>
  <p>Jerome7 exposes MCP tools — works inside Claude Desktop, GPT, Gemini, or any agent runtime that speaks Model Context Protocol.</p>
  <div class="star-bar">
    <span class="star-text">If this moves you, star it.</span>
    <a href="https://github.com/odominguez7/Jerome7" class="star-btn" target="_blank">
      Star on GitHub
    </a>
  </div>
</section>

<!-- EMAIL CAPTURE -->
<section style="text-align:center;padding:48px 0;">
  <h2 style="font-size:1.3rem;color:#E85D04;margin-bottom:8px;">Get reminded daily</h2>
  <p style="color:#484f58;font-size:0.8rem;margin-bottom:20px;">One email. 7 minutes. No spam. Unsubscribe anytime.</p>
  <form id="emailForm" onsubmit="return submitEmail(event)" style="display:flex;gap:8px;max-width:420px;margin:0 auto;">
    <input type="email" id="emailInput" placeholder="your@email.com" required
      style="flex:1;padding:12px 16px;background:#161b22;border:1px solid #30363d;border-radius:8px;color:#c9d1d9;font-family:inherit;font-size:0.85rem;outline:none;">
    <button type="submit" id="emailBtn"
      style="padding:12px 20px;background:#E85D04;color:#fff;border:none;border-radius:8px;font-family:inherit;font-weight:700;font-size:0.85rem;cursor:pointer;white-space:nowrap;">
      REMIND ME
    </button>
  </form>
  <div id="emailMsg" style="color:#7ee787;font-size:0.8rem;margin-top:12px;display:none;"></div>
</section>

<!-- FOOTER -->
<div class="footer">
  <div class="footer-brand">JEROME7</div>
  <div class="footer-text">Personally funded. Open source. No paywall.</div>
  <div class="footer-text" style="margin-top: 8px;">
    <a href="/timer">Session</a> &middot;
    <a href="/globe">Globe</a> &middot;
    <a href="https://github.com/odominguez7/Jerome7">GitHub</a> &middot;
    <a href="https://discord.gg/5AZP8DbEJm">Discord</a>
  </div>
  <a href="/timer" class="bottom-cta">START YOUR 7 MINUTES</a>
  <div class="footer-text" style="margin-top:24px;color:#30363d">
    Built by <a href="https://github.com/odominguez7" style="color:#484f58">Omar</a> &middot; Apache 2.0 &middot; <em>It's on YU.</em>
  </div>
</div>

<script>
async function submitEmail(e) {{
  e.preventDefault();
  const email = document.getElementById('emailInput').value.trim();
  const btn = document.getElementById('emailBtn');
  const msg = document.getElementById('emailMsg');
  btn.disabled = true; btn.textContent = '...';
  try {{
    const resp = await fetch('/subscribe', {{
      method: 'POST',
      headers: {{ 'Content-Type': 'application/json' }},
      body: JSON.stringify({{ email: email }}),
    }});
    const data = await resp.json();
    if (resp.ok) {{
      msg.textContent = data.message || 'You\\'re in. See you tomorrow.';
      msg.style.color = '#7ee787';
      msg.style.display = 'block';
      document.getElementById('emailInput').value = '';
    }} else {{
      msg.textContent = data.detail || 'Something went wrong.';
      msg.style.color = '#f85149';
      msg.style.display = 'block';
    }}
  }} catch(err) {{
    msg.textContent = 'Network error. Try again.';
    msg.style.color = '#f85149';
    msg.style.display = 'block';
  }}
  btn.disabled = false; btn.textContent = 'REMIND ME';
  return false;
}}

function copyCli() {{
  navigator.clipboard.writeText('npx jerome7 --wellness').then(() => {{
    const btn = document.querySelector('.copy-btn');
    btn.textContent = 'COPIED!';
    btn.style.color = '#7ee787'; btn.style.borderColor = '#7ee787';
    setTimeout(() => {{ btn.textContent = 'COPY'; btn.style.color = ''; btn.style.borderColor = ''; }}, 2000);
  }});
}}
</script>
<footer style="text-align:center;padding:32px 0 16px;font-size:0.7rem;color:#30363d;">
  <a href="/privacy" style="color:#484f58;text-decoration:none;">Privacy</a>
  <span style="color:#21262d;margin:0 8px;">|</span>
  <a href="/terms" style="color:#484f58;text-decoration:none;">Terms</a>
  <span style="color:#21262d;margin:0 8px;">|</span>
  <span style="color:#484f58;">Apache 2.0</span>
</footer>
</body>
</html>"""
    return HTMLResponse(
        content=html,
        headers={"Cache-Control": "public, max-age=3600"},
    )
