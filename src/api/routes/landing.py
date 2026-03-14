"""GET / — jerome7.com landing page. The front door."""

import asyncio

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from src.agents.coach import CoachAgent

router = APIRouter()
coach = CoachAgent()

PHASE_COLORS = {
    "prime": "#7ee787",
    "build": "#E85D04",
    "move": "#f778ba",
    "reset": "#79c0ff",
}


@router.get("/", response_class=HTMLResponse)
def landing():
    # Get today's session for the preview
    try:
        data = asyncio.run(coach.generate_daily())
    except Exception:
        data = None

    # Build session preview blocks
    blocks_html = ""
    if data and "blocks" in data:
        for b in data["blocks"]:
            phase = b.get("phase", "build")
            color = PHASE_COLORS.get(phase, "#E85D04")
            blocks_html += f"""
            <div class="block">
              <span class="block-phase" style="color:{color}">{phase.upper()}</span>
              <span class="block-name">{b['name']}</span>
              <span class="block-time">60s</span>
            </div>"""

    session_title = data.get("session_title", "the foundation") if data else "the foundation"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Jerome7 — 7 minutes. Show up.</title>
<meta name="description" content="7 minutes a day. Same session for everyone. Streak-based accountability. Free forever.">
<meta property="og:title" content="Jerome7 — 7 minutes. Show up.">
<meta property="og:description" content="The daily 7-minute challenge for builders. Bodyweight. No equipment. Streak-powered.">
<meta property="og:type" content="website">
<meta property="og:url" content="https://jerome7.com">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="Jerome7 — 7 minutes. Show up.">
<meta name="twitter:description" content="Same session for everyone. Every day. Free forever.">
<style>
  @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700;800&display=swap');
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}

  body {{
    background: #0d1117;
    color: #c9d1d9;
    font-family: 'JetBrains Mono', monospace;
    line-height: 1.6;
    overflow-x: hidden;
  }}

  /* --- HERO --- */
  .hero {{
    min-height: 100vh;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
    padding: 40px 20px;
  }}

  .brand {{
    font-size: 11px;
    letter-spacing: 4px;
    color: #E85D04;
    margin-bottom: 32px;
  }}

  h1 {{
    font-size: clamp(32px, 8vw, 64px);
    font-weight: 800;
    color: #f0f6fc;
    line-height: 1.1;
    margin-bottom: 16px;
  }}

  h1 span {{ color: #E85D04; }}

  .tagline {{
    font-size: 16px;
    color: #8b949e;
    margin-bottom: 48px;
    max-width: 400px;
  }}

  .cta-row {{
    display: flex;
    gap: 16px;
    flex-wrap: wrap;
    justify-content: center;
  }}

  .btn {{
    padding: 14px 32px;
    border-radius: 100px;
    border: none;
    cursor: pointer;
    font-family: inherit;
    font-size: 14px;
    font-weight: 700;
    letter-spacing: 1px;
    text-decoration: none;
    transition: all 0.2s;
  }}

  .btn-primary {{
    background: #E85D04;
    color: #fff;
  }}
  .btn-primary:hover {{ background: #ff6b1a; transform: translateY(-1px); }}

  .btn-ghost {{
    background: transparent;
    color: #8b949e;
    border: 1px solid #30363d;
  }}
  .btn-ghost:hover {{ border-color: #E85D04; color: #E85D04; }}

  .scroll-hint {{
    position: absolute;
    bottom: 32px;
    color: #484f58;
    font-size: 11px;
    letter-spacing: 2px;
    animation: pulse 2s ease-in-out infinite;
  }}

  @keyframes pulse {{ 0%,100% {{ opacity: 1; }} 50% {{ opacity: 0.4; }} }}

  /* --- SECTIONS --- */
  section {{
    max-width: 640px;
    margin: 0 auto;
    padding: 80px 20px;
  }}

  .section-label {{
    font-size: 10px;
    letter-spacing: 3px;
    color: #E85D04;
    margin-bottom: 24px;
  }}

  h2 {{
    font-size: 24px;
    font-weight: 700;
    color: #f0f6fc;
    margin-bottom: 16px;
  }}

  p {{
    color: #8b949e;
    font-size: 14px;
    margin-bottom: 16px;
  }}

  /* --- HOW IT WORKS --- */
  .steps {{
    display: flex;
    flex-direction: column;
    gap: 24px;
    margin-top: 32px;
  }}

  .step {{
    display: flex;
    gap: 16px;
    align-items: flex-start;
  }}

  .step-num {{
    font-size: 24px;
    font-weight: 800;
    color: #E85D04;
    min-width: 32px;
  }}

  .step-text {{
    font-size: 14px;
    color: #c9d1d9;
  }}

  .step-text strong {{ color: #f0f6fc; }}
  .step-sub {{ font-size: 12px; color: #484f58; margin-top: 4px; }}

  /* --- TODAY'S SESSION --- */
  .session-card {{
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 12px;
    padding: 24px;
    margin-top: 32px;
  }}

  .session-header {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;
  }}

  .session-title {{
    font-size: 16px;
    font-weight: 700;
    color: #f0f6fc;
  }}

  .session-time {{
    font-size: 12px;
    color: #484f58;
  }}

  .block {{
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 8px 0;
    border-bottom: 1px solid #21262d;
  }}

  .block:last-child {{ border-bottom: none; }}

  .block-phase {{
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 1px;
    min-width: 48px;
  }}

  .block-name {{
    font-size: 13px;
    color: #f0f6fc;
    flex: 1;
  }}

  .block-time {{
    font-size: 11px;
    color: #484f58;
  }}

  /* --- AGENTS --- */
  .agents {{
    display: flex;
    flex-direction: column;
    gap: 20px;
    margin-top: 32px;
  }}

  .agent {{
    background: #161b22;
    border: 1px solid #21262d;
    border-radius: 8px;
    padding: 16px 20px;
  }}

  .agent-name {{
    font-size: 13px;
    font-weight: 700;
    color: #f0f6fc;
    margin-bottom: 4px;
  }}

  .agent-desc {{
    font-size: 12px;
    color: #8b949e;
  }}

  /* --- RULES --- */
  .rules {{
    display: flex;
    flex-direction: column;
    gap: 12px;
    margin-top: 24px;
  }}

  .rule {{
    font-size: 13px;
    color: #c9d1d9;
    padding-left: 16px;
    border-left: 2px solid #E85D04;
  }}

  /* --- LIVE FEED --- */
  .feed-row {{
    display: flex; align-items: center; gap: 12px;
    padding: 10px 0; border-bottom: 1px solid #21262d;
  }}
  .feed-flag {{ font-size: 18px; }}
  .feed-name {{ font-size: 13px; color: #f0f6fc; flex: 1; }}
  .feed-streak {{ font-size: 12px; color: #E85D04; font-weight: 700; }}
  .feed-time {{ font-size: 11px; color: #484f58; }}
  .feed-empty {{ font-size: 13px; color: #484f58; padding: 16px 0; }}
  .leaderboard-link {{
    display: inline-block; margin-top: 20px;
    font-size: 12px; color: #E85D04; text-decoration: none;
    letter-spacing: 1px;
  }}
  .leaderboard-link:hover {{ text-decoration: underline; }}

  /* --- FOOTER --- */
  .footer {{
    text-align: center;
    padding: 40px 20px 60px;
    border-top: 1px solid #21262d;
  }}

  .footer-brand {{
    font-size: 11px;
    letter-spacing: 3px;
    color: #E85D04;
    margin-bottom: 8px;
  }}

  .footer-text {{
    font-size: 12px;
    color: #484f58;
  }}

  .footer a {{
    color: #E85D04;
    text-decoration: none;
  }}

  .bottom-cta {{
    display: inline-block;
    margin-top: 32px;
    padding: 14px 40px;
    background: #E85D04;
    color: #fff;
    border-radius: 100px;
    font-family: inherit;
    font-size: 14px;
    font-weight: 700;
    text-decoration: none;
    letter-spacing: 1px;
  }}
  .bottom-cta:hover {{ background: #ff6b1a; }}

  /* --- COMPAT BAR --- */
  .compat-bar {{
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
    justify-content: center;
    margin-top: 32px;
  }}
  .compat-label {{
    font-size: 10px;
    letter-spacing: 2px;
    color: #484f58;
    margin-right: 4px;
  }}
  .compat-badge {{
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 5px 12px;
    border-radius: 100px;
    border: 1px solid #30363d;
    font-size: 11px;
    font-weight: 600;
    color: #c9d1d9;
    letter-spacing: 0.5px;
    background: #161b22;
  }}
  .compat-dot {{ width: 6px; height: 6px; border-radius: 50%; }}
  .dot-claude {{ background: #cc785c; }}
  .dot-gpt {{ background: #10a37f; }}
  .dot-gemini {{ background: #4285f4; }}
  .dot-openclaw {{ background: #7ee787; }}
  .dot-zeroclaw {{ background: #f778ba; }}

  /* --- INSTALL STRIP --- */
  .install-strip {{
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 16px 20px;
    margin-top: 40px;
    display: flex;
    align-items: center;
    gap: 12px;
    flex-wrap: wrap;
  }}
  .install-label {{
    font-size: 10px;
    letter-spacing: 2px;
    color: #E85D04;
    white-space: nowrap;
  }}
  .install-code {{
    font-size: 12px;
    color: #7ee787;
    flex: 1;
    word-break: break-all;
  }}
  .copy-btn {{
    background: transparent;
    border: 1px solid #30363d;
    color: #8b949e;
    font-family: inherit;
    font-size: 11px;
    padding: 4px 10px;
    border-radius: 6px;
    cursor: pointer;
    white-space: nowrap;
  }}
  .copy-btn:hover {{ border-color: #E85D04; color: #E85D04; }}

  /* --- GITHUB STAR --- */
  .star-bar {{
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 12px;
    margin-top: 48px;
    padding: 20px;
    border: 1px solid #21262d;
    border-radius: 8px;
    background: #161b22;
  }}
  .star-text {{
    font-size: 13px;
    color: #8b949e;
  }}
  .star-btn {{
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 8px 20px;
    background: #21262d;
    border: 1px solid #30363d;
    border-radius: 6px;
    color: #f0f6fc;
    font-family: inherit;
    font-size: 12px;
    font-weight: 600;
    text-decoration: none;
    transition: all 0.2s;
  }}
  .star-btn:hover {{ background: #30363d; border-color: #E85D04; }}

  /* --- RESPONSIVE --- */
  @media (max-width: 480px) {{
    .hero {{ padding: 60px 20px; }}
    h1 {{ font-size: 28px; }}
    .tagline {{ font-size: 14px; }}
    section {{ padding: 60px 16px; }}
    .install-code {{ font-size: 10px; }}
  }}
</style>
</head>
<body>

<!-- HERO -->
<div class="hero">
  <div class="brand">JEROME7</div>
  <h1><span>7</span> minutes.<br>Show up.</h1>
  <div class="tagline">Same session for everyone. Every day. Streak-powered accountability for builders. Free forever.</div>
  <div class="cta-row">
    <a href="https://discord.gg/5AZP8DbEJm" class="btn btn-primary">JOIN DISCORD</a>
    <a href="https://github.com/odominguez7/Jerome7" class="btn btn-ghost">⭐ GitHub</a>
  </div>

  <div class="compat-bar">
    <span class="compat-label">WORKS WITH</span>
    <span class="compat-badge"><span class="compat-dot dot-claude"></span>Claude</span>
    <span class="compat-badge"><span class="compat-dot dot-gpt"></span>GPT-4</span>
    <span class="compat-badge"><span class="compat-dot dot-gemini"></span>Gemini</span>
    <span class="compat-badge"><span class="compat-dot dot-openclaw"></span>OpenClaw</span>
    <span class="compat-badge"><span class="compat-dot dot-zeroclaw"></span>ZeroClaw</span>
  </div>

  <div style="max-width:580px;margin:0 auto;padding:0 20px;">
    <div class="install-strip">
      <span class="install-label">OPENCLAW</span>
      <code class="install-code" id="install-cmd">curl -fsSL https://raw.githubusercontent.com/odominguez7/Jerome7/main/integrations/openclaw/SKILL.md -o ~/.openclaw/skills/jerome7.md</code>
      <button class="copy-btn" onclick="copyInstall()">COPY</button>
    </div>
  </div>
</div>

<!-- HOW IT WORKS -->
<section>
  <div class="section-label">HOW IT WORKS</div>
  <h2>One session. Everyone. Every day.</h2>
  <p>Like Wordle, but for your body. Jerome generates one 7-minute session each day. Same moves for everyone on earth. Do it. Log it. Keep the chain.</p>

  <div class="steps">
    <div class="step">
      <div class="step-num">1</div>
      <div>
        <div class="step-text"><strong>/seven7</strong> in Discord</div>
        <div class="step-sub">See today's session. Open the timer.</div>
      </div>
    </div>
    <div class="step">
      <div class="step-num">2</div>
      <div>
        <div class="step-text"><strong>7 blocks. 60 seconds each.</strong></div>
        <div class="step-sub">Prime. Build. Move. Reset. 420 seconds total.</div>
      </div>
    </div>
    <div class="step">
      <div class="step-num">3</div>
      <div>
        <div class="step-text"><strong>/log</strong> when done</div>
        <div class="step-sub">Your streak grows. Share your chain.</div>
      </div>
    </div>
  </div>
</section>

<!-- TODAY'S SESSION -->
<section>
  <div class="section-label">TODAY'S SESSION</div>
  <h2>{session_title}</h2>
  <p>This is what everyone on earth is doing today. Bodyweight. No equipment. Anywhere.</p>

  <div class="session-card">
    <div class="session-header">
      <div class="session-title">{session_title}</div>
      <div class="session-time">7:00</div>
    </div>
    {blocks_html}
  </div>
</section>

<!-- AGENTS -->
<section>
  <div class="section-label">UNDER THE HOOD</div>
  <h2>5 AI agents. One mission.</h2>
  <p>Jerome isn't a workout app. It's a system of agents that learn how you move, when you skip, and who you need beside you.</p>

  <div class="agents">
    <div class="agent">
      <div class="agent-name">Coach</div>
      <div class="agent-desc">Generates today's session. Bodyweight, fun, surprising. Never repeats yesterday.</div>
    </div>
    <div class="agent">
      <div class="agent-name">Nudge</div>
      <div class="agent-desc">Learns when you're about to skip. DMs you before you break the chain. Never shames.</div>
    </div>
    <div class="agent">
      <div class="agent-name">Streak</div>
      <div class="agent-desc">Tracks consistency, not perfection. 3 misses breaks it. 1 never does. Saves for life.</div>
    </div>
    <div class="agent">
      <div class="agent-name">Community</div>
      <div class="agent-desc">Matches you with 3-5 builders at your level. Your pod. Your crew.</div>
    </div>
    <div class="agent">
      <div class="agent-name">Scheduler</div>
      <div class="agent-desc">Finds the window where showing up is easiest. Learns your habits.</div>
    </div>
  </div>
</section>

<!-- STREAK RULES -->
<section>
  <div class="section-label">THE RULES</div>
  <h2>The chain.</h2>
  <p>Simple rules. No ambiguity.</p>

  <div class="rules">
    <div class="rule">Show up = 7 minutes. That's it.</div>
    <div class="rule">Miss 1 day? Chain holds.</div>
    <div class="rule">Miss 2 days? Still holds. Life happens.</div>
    <div class="rule">Miss 3? Chain breaks. Start over.</div>
    <div class="rule">1 save per 30 days. Use it when you need it.</div>
    <div class="rule">Milestones at 7, 14, 30, 50, 100, 200, 365.</div>
    <div class="rule">Longest streak never resets. That's your record.</div>
  </div>
</section>

<!-- LIVE FEED -->
<section>
  <div class="section-label">SHOWING UP NOW</div>
  <h2>Builders worldwide.</h2>
  <p>Every session logged anywhere on earth, live.</p>
  <div id="feed-list"><div class="feed-empty">Loading...</div></div>
  <a href="/leaderboard" class="leaderboard-link">VIEW FULL LEADERBOARD →</a>
</section>

<!-- GITHUB STAR -->
<section>
  <div class="section-label">OPEN SOURCE</div>
  <h2>MCP-native. Agent-ready.</h2>
  <p>Jerome7 exposes 6 MCP tools — works inside Claude Desktop, GPT, Gemini, OpenClaw, ZeroClaw, or any agent runtime that speaks Model Context Protocol.</p>
  <div class="star-bar">
    <span class="star-text">If this moves you, star it.</span>
    <a href="https://github.com/odominguez7/Jerome7" class="star-btn" target="_blank">
      ⭐ Star on GitHub
    </a>
  </div>
</section>

<!-- FOOTER -->
<div class="footer">
  <div class="footer-brand">JEROME7</div>
  <div class="footer-text">Free forever. Open source. Built at MIT.</div>
  <div class="footer-text" style="margin-top: 8px;">
    <a href="https://github.com/odominguez7/Jerome7">GitHub</a> ·
    <a href="https://discord.gg/5AZP8DbEJm">Discord</a>
  </div>
  <a href="https://discord.gg/5AZP8DbEJm" class="bottom-cta">START YOUR CHAIN</a>
</div>

<script>
async function loadFeed() {{
  try {{
    const res = await fetch('/leaderboard/data');
    const data = await res.json();
    const feed = data.feed || [];
    const el = document.getElementById('feed-list');
    if (!feed.length) {{
      el.innerHTML = '<div class="feed-empty">Quiet right now. Be first today.</div>';
      return;
    }}
    el.innerHTML = feed.slice(0, 8).map(e =>
      `<div class="feed-row">
        <span class="feed-flag">${{e.flag}}</span>
        <span class="feed-name">${{e.name}}</span>
        <span class="feed-streak">${{e.streak}}d</span>
        <span class="feed-time">${{e.time_ago}}</span>
      </div>`
    ).join('');
  }} catch(e) {{
    document.getElementById('feed-list').innerHTML =
      '<div class="feed-empty">Be the first to show up today.</div>';
  }}
}}
loadFeed();
setInterval(loadFeed, 30000);

function copyInstall() {{
  const cmd = document.getElementById('install-cmd').textContent;
  navigator.clipboard.writeText(cmd).then(() => {{
    const btn = document.querySelector('.copy-btn');
    btn.textContent = 'COPIED!';
    btn.style.color = '#7ee787';
    btn.style.borderColor = '#7ee787';
    setTimeout(() => {{
      btn.textContent = 'COPY';
      btn.style.color = '';
      btn.style.borderColor = '';
    }}, 2000);
  }});
}}
</script>
</body>
</html>"""
    return HTMLResponse(content=html)
