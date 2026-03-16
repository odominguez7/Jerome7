"""GET /timer — The unified 7-minute wellness session.

Combines onboarding, audio-guided wellness, and session completion into one flow.
Session type rotates daily: breathwork → meditation → reflection → preparation.
"""

import json
import os
from datetime import datetime, timezone
from html import escape as html_escape

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from src.agents.coach import CoachAgent
from src.agents.session_types import today_session_type, FALLBACK_SESSIONS
from src.api.meta import head_meta

router = APIRouter()
coach = CoachAgent()

_cache: dict = {"date": None, "session": None}


@router.get("/timer", response_class=HTMLResponse)
async def timer_page():
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    session_type = today_session_type()

    if _cache["date"] == today and _cache["session"]:
        data = _cache["session"]
    else:
        try:
            data = await coach.generate_wellness(session_type)
        except Exception:
            data = FALLBACK_SESSIONS.get(session_type, FALLBACK_SESSIONS["breathwork"])
        _cache["date"] = today
        _cache["session"] = data

    # Sanitize AI-generated content to prevent XSS
    blocks_raw = data.get("blocks", [])
    if not isinstance(blocks_raw, list):
        blocks_raw = []
    sanitized_blocks = []
    for b in blocks_raw:
        if not isinstance(b, dict):
            continue
        b["name"] = html_escape(str(b.get("name", "")))
        b["instruction"] = html_escape(str(b.get("instruction", "")))
        sanitized_blocks.append(b)
    blocks_raw = sanitized_blocks
    blocks_json = json.dumps(blocks_raw)
    title = html_escape(data.get("session_title", session_type.title()))
    closing = html_escape(data.get("closing", "You showed up. That's the win."))
    closing_js = json.dumps(closing)  # properly escaped for JS embedding

    type_labels = {
        "breathwork": "Guided Breathwork",
        "meditation": "Focus Meditation",
        "reflection": "Reflection",
        "preparation": "Preparation for the Day",
    }
    type_label = type_labels.get(session_type, session_type.title())

    type_descriptions = {
        "breathwork": "Box breathing. 4-count cycles. Calm your nervous system.",
        "meditation": "Breath awareness. Gentle focus. Developing calmness.",
        "reflection": "Journaling prompt. Silent reflection. Carry one thing forward.",
        "preparation": "Visualization. 3 priorities. Launch into the day.",
    }
    type_desc = type_descriptions.get(session_type, "7 minutes of guided wellness.")
    ai_available = "true" if os.getenv("ELEVENLABS_API_KEY", "") else "false"

    _meta = head_meta(
        title=f"Jerome7 | {type_label}",
        description=f"Today's 7-minute guided {session_type} session. Same for every builder on earth.",
        url="https://jerome7.com/timer",
    )
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Jerome7 | {type_label}</title>
<meta name="description" content="Today's 7-minute guided {session_type} session. Same for every builder on earth.">
{_meta}
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
  .container {{ max-width: 560px; width: 100%; text-align: center; }}

  /* ── NAV ── */
  .nav {{
    position: fixed; top: 0; left: 0; right: 0; z-index: 100;
    display: flex; justify-content: space-between; align-items: center;
    padding: 12px 24px; background: rgba(13,17,23,0.92);
    backdrop-filter: blur(12px); border-bottom: 1px solid #21262d;
  }}
  .nav-brand {{
    font-size: 13px; font-weight: 800; color: #E85D04;
    letter-spacing: 2px; text-decoration: none;
  }}
  .nav-links {{ display: flex; gap: 20px; }}
  .nav-links a {{
    font-size: 12px; color: #8b949e; text-decoration: none;
    letter-spacing: 0.5px;
  }}
  .nav-links a:hover {{ color: #f0f6fc; }}

  /* ── ONBOARDING MODAL ── */
  .modal-overlay {{
    position: fixed; inset: 0; z-index: 200;
    background: rgba(0,0,0,0.85);
    display: flex; align-items: center; justify-content: center;
    padding: 20px;
  }}
  .modal {{
    background: #161b22; border: 1px solid #30363d;
    border-radius: 16px; padding: 40px; max-width: 420px;
    width: 100%; text-align: center;
  }}
  .modal-brand {{ font-size: 10px; letter-spacing: 3px; color: #E85D04; margin-bottom: 16px; }}
  .modal h2 {{ font-size: 22px; font-weight: 800; color: #f0f6fc; margin-bottom: 8px; }}
  .modal .subtitle {{ font-size: 12px; color: #484f58; margin-bottom: 32px; }}
  .modal label {{
    display: block; text-align: left; font-size: 10px;
    letter-spacing: 2px; color: #8b949e; margin-bottom: 6px; margin-top: 16px;
  }}
  .modal input, .modal select {{
    width: 100%; padding: 12px 16px; background: #0d1117;
    border: 1px solid #30363d; border-radius: 8px;
    color: #f0f6fc; font-family: inherit; font-size: 14px;
    outline: none;
  }}
  .modal input:focus, .modal select:focus {{ border-color: #E85D04; }}
  .modal select {{
    appearance: none; cursor: pointer;
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='8'%3E%3Cpath d='M1 1l5 5 5-5' stroke='%238b949e' fill='none' stroke-width='2'/%3E%3C/svg%3E");
    background-repeat: no-repeat;
    background-position: right 12px center;
    padding-right: 36px;
  }}
  .modal-btn {{
    width: 100%; margin-top: 24px; padding: 14px;
    background: #E85D04; color: #fff; border: none;
    border-radius: 100px; font-family: inherit;
    font-size: 14px; font-weight: 700; letter-spacing: 1px;
    cursor: pointer;
  }}
  .modal-btn:hover {{ background: #ff6b1a; }}
  .modal-btn:disabled {{ background: #21262d; color: #484f58; cursor: default; }}
  .modal-skip {{
    display: block; margin-top: 16px; font-size: 11px;
    color: #484f58; cursor: pointer; background: none;
    border: none; font-family: inherit; letter-spacing: 1px;
  }}
  .modal-skip:hover {{ color: #8b949e; }}
  .hidden {{ display: none !important; }}

  /* ── PRE-START ── */
  .session-badge {{
    display: inline-flex; align-items: center; gap: 8px;
    background: #161b22; border: 1px solid #30363d;
    border-radius: 100px; padding: 8px 20px;
    font-size: 10px; letter-spacing: 2px; color: #8b949e;
    margin-bottom: 24px;
  }}
  .session-badge .pulse {{
    width: 8px; height: 8px; border-radius: 50%;
    background: #3fb950; animation: pulse 2s infinite;
  }}
  @keyframes pulse {{ 0%,100% {{ opacity: 1; }} 50% {{ opacity: 0.4; }} }}

  .session-type {{
    font-size: 10px; letter-spacing: 3px; color: var(--type-color);
    margin-bottom: 12px;
  }}
  .session-title {{
    font-size: 32px; font-weight: 800; color: #f0f6fc;
    margin-bottom: 12px; line-height: 1.2;
  }}
  .session-desc {{
    font-size: 14px; color: #8b949e; margin-bottom: 40px;
    max-width: 400px; margin-left: auto; margin-right: auto; line-height: 1.6;
  }}

  /* ── BLOCKS PREVIEW ── */
  .blocks-preview {{
    background: #161b22; border: 1px solid #21262d;
    border-radius: 12px; padding: 20px;
    margin-bottom: 40px; text-align: left;
  }}
  .blocks-preview .block-row {{
    display: flex; align-items: center; gap: 12px;
    padding: 8px 0; border-bottom: 1px solid rgba(255,255,255,0.04);
  }}
  .blocks-preview .block-row:last-child {{ border-bottom: none; }}
  .block-num {{ font-size: 10px; color: #484f58; min-width: 20px; }}
  .block-name-prev {{ font-size: 13px; color: #f0f6fc; flex: 1; }}
  .block-dur {{ font-size: 11px; color: #484f58; }}

  /* ── START BUTTON ── */
  .start-btn {{
    display: inline-block; padding: 18px 56px;
    background: #E85D04; color: #fff; border: none;
    border-radius: 100px; font-family: inherit;
    font-size: 16px; font-weight: 700; letter-spacing: 1px;
    cursor: pointer; transition: all 0.2s;
  }}
  .start-btn:hover {{ background: #ff6b1a; transform: translateY(-1px); }}

  .voice-note {{
    font-size: 10px; color: #30363d; margin-top: 16px; letter-spacing: 1px;
  }}

  /* ── COMMUNITY STATS ── */
  .community-bar {{
    display: flex; justify-content: center; gap: 24px;
    margin-bottom: 24px;
  }}
  .community-stat {{
    text-align: center;
  }}
  .community-num {{
    font-size: 20px; font-weight: 800; color: #E85D04;
  }}
  .community-label {{
    font-size: 9px; letter-spacing: 2px; color: #484f58;
  }}

  /* ── AMBIENT AUDIO TOGGLE ── */
  .ambient-toggle {{
    position: fixed; bottom: 20px; left: 20px; z-index: 50;
    display: flex; align-items: center; gap: 8px;
    background: #161b22; border: 1px solid #21262d;
    border-radius: 100px; padding: 6px 14px;
    font-size: 10px; color: #484f58; cursor: pointer;
    letter-spacing: 1px; border: none; font-family: inherit;
  }}
  .ambient-toggle:hover {{ color: #8b949e; }}
  .ambient-dot {{
    width: 6px; height: 6px; border-radius: 50%;
    background: #3fb950; transition: background 0.2s;
  }}
  .ambient-dot.off {{ background: #484f58; }}

  /* ── ACTIVE SESSION ── */
  .phase-label {{
    font-size: 10px; letter-spacing: 3px; margin-bottom: 12px;
    transition: color 0.4s;
  }}
  .active-name {{
    font-size: 36px; font-weight: 800; color: #f0f6fc;
    margin-bottom: 12px; line-height: 1.2;
  }}
  .active-instruction {{
    font-size: 14px; color: #8b949e; margin-bottom: 40px;
    max-width: 420px; margin-left: auto; margin-right: auto; line-height: 1.6;
  }}
  .timer {{
    font-size: 96px; font-weight: 800; color: #f0f6fc;
    letter-spacing: -2px; margin-bottom: 8px;
    font-variant-numeric: tabular-nums;
  }}
  .timer-label {{
    font-size: 10px; color: #484f58; letter-spacing: 2px; margin-bottom: 32px;
  }}

  /* Progress */
  .progress-bar {{
    width: 100%; height: 4px; background: #21262d;
    border-radius: 2px; overflow: hidden; margin-bottom: 12px;
  }}
  .progress-fill {{
    height: 100%; border-radius: 2px;
    transition: width 1s linear, background-color 0.4s;
    width: 0%;
  }}
  .dots {{ display: flex; gap: 6px; justify-content: center; margin-bottom: 32px; }}
  .dot {{
    width: 8px; height: 8px; border-radius: 50%;
    background: #21262d; transition: all 0.3s;
  }}
  .dot.active {{ background: #E85D04; transform: scale(1.3); }}
  .dot.done {{ background: #484f58; }}

  /* ── COMPLETE ── */
  .complete {{ text-align: center; }}
  .complete-check {{ font-size: 64px; margin-bottom: 16px; color: #3fb950; }}
  .complete-title {{ font-size: 24px; font-weight: 800; color: #f0f6fc; margin-bottom: 8px; }}
  .complete-text {{ font-size: 14px; color: #8b949e; margin-bottom: 32px; line-height: 1.6; }}
  .share-row {{
    display: flex; gap: 12px; justify-content: center; flex-wrap: wrap;
    margin-bottom: 16px;
  }}
  .share-btn {{
    padding: 10px 20px; border-radius: 8px; border: 1px solid #30363d;
    background: #161b22; color: #c9d1d9; cursor: pointer;
    font-family: inherit; font-size: 12px; font-weight: 600;
    transition: all 0.2s;
  }}
  .share-btn:hover {{ border-color: #E85D04; color: #E85D04; }}
  .share-btn.primary {{ background: #E85D04; color: #fff; border-color: #E85D04; }}
  .complete-links {{
    margin-top: 24px; font-size: 11px; color: #484f58;
  }}
  .complete-links a {{ color: #E85D04; text-decoration: none; margin: 0 8px; }}
  .toast {{
    display: none; color: #7ee787; font-size: 11px;
    margin-top: 8px; letter-spacing: 1px;
  }}

  /* ── PAUSE BUTTON ── */
  .pause-btn {{
    display: none; padding: 10px 32px;
    background: transparent; color: #8b949e;
    border: 1px solid #30363d; border-radius: 100px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px; font-weight: 600; letter-spacing: 2px;
    cursor: pointer; transition: all 0.2s; margin-bottom: 16px;
  }}
  .pause-btn:hover {{ border-color: #E85D04; color: #E85D04; }}
  .pause-btn.visible {{ display: inline-block; }}
  .paused-label {{
    display: none; font-size: 12px; letter-spacing: 3px;
    color: #E85D04; margin-bottom: 8px; animation: pulse 1.5s infinite;
  }}
  .paused-label.show {{ display: block; }}

  /* ── BREATH CIRCLE ── */
  .breath-circle {{
    width: 180px; height: 180px; border-radius: 50%;
    border: 2px solid; opacity: 0.15;
    margin: 0 auto 12px;
    transition: transform 1s ease-in-out, opacity 0.5s;
    display: none;
  }}
  .breath-circle.active {{ display: block; }}
  .breath-circle.inhale {{ transform: scale(1.3); opacity: 0.3; }}
  .breath-circle.exhale {{ transform: scale(0.8); opacity: 0.1; }}
  .breath-circle.hold {{ transform: scale(1.3); opacity: 0.25; }}

  /* ── BLOCK TRANSITION ── */
  .block-transition {{ transition: opacity 0.3s ease; }}
  .block-transition.fade {{ opacity: 0; }}

  /* ── BLOCK TIMER (small) ── */
  .block-timer {{
    font-size: 14px; color: #484f58; letter-spacing: 1px;
    margin-bottom: 8px; font-variant-numeric: tabular-nums;
  }}

  @media (max-width: 480px) {{
    .timer {{ font-size: 64px; }}
    .session-title {{ font-size: 24px; }}
    .active-name {{ font-size: 24px; }}
    .breath-circle {{ width: 140px; height: 140px; }}
  }}
</style>
</head>
<body>

<!-- NAV -->
<nav class="nav">
  <a href="/" class="nav-brand">JEROME7</a>
</nav>

<!-- ONBOARDING MODAL -->
<div class="modal-overlay hidden" id="onboarding">
  <div class="modal">
    <div class="modal-brand">JEROME7</div>
    <h2 id="onboard-greeting">Welcome, builder.</h2>
    <div class="subtitle">Claim your Jerome# identity. 30 seconds.</div>

    <label>YOUR NAME</label>
    <input type="text" id="ob-name" placeholder="What should we call you?" maxlength="50" autocomplete="off">

    <label>PRIMARY GOAL</label>
    <select id="ob-goal">
      <option value="">Choose...</option>
      <option value="stress_relief">Stress relief</option>
      <option value="focus">Better focus</option>
      <option value="consistency">Build consistency</option>
      <option value="community">Find community</option>
    </select>

    <div style="position:absolute;left:-9999px;top:-9999px;opacity:0;height:0;width:0;overflow:hidden" aria-hidden="true">
      <input type="text" name="website" id="hp-field" tabindex="-1" autocomplete="off">
    </div>

    <button class="modal-btn" id="ob-submit" onclick="submitOnboarding()">CLAIM MY JEROME#</button>
    <button class="modal-skip" onclick="skipOnboarding()">skip for now</button>
  </div>
</div>

<div class="container">

  <!-- PRE-START -->
  <div id="preStart">
    <div class="session-badge">
      <span class="pulse"></span>
      LIVE SESSION
    </div>

    <!-- Community stats -->
    <div class="community-bar" id="communityBar">
      <div class="community-stat">
        <div class="community-num" id="statJeromes">--</div>
        <div class="community-label">JEROMES</div>
      </div>
      <div class="community-stat">
        <div class="community-num" id="statToday">--</div>
        <div class="community-label">TODAY</div>
      </div>
      <div class="community-stat">
        <div class="community-num" id="statCountries">--</div>
        <div class="community-label">COUNTRIES</div>
      </div>
    </div>

    <div class="session-type" id="sessionType" style="--type-color:#4ecdc4">{session_type.upper()}</div>
    <div class="session-title">{title}</div>
    <div class="session-desc">{type_desc}</div>

    <div class="blocks-preview" id="blocksPreview"></div>

    <!-- Voice mode toggle -->
    <div id="voiceToggle" class="voice-toggle" style="display:inline-flex;background:#161b22;border:1px solid #21262d;border-radius:100px;margin-bottom:20px;overflow:hidden">
      <button id="btnAiVoice" style="padding:8px 20px;font-size:10px;letter-spacing:2px;background:#E85D04;border:none;color:#fff;cursor:pointer;font-family:inherit;font-weight:600;border-radius:100px 0 0 100px" onclick="selectVoice('ai')">AI VOICE</button>
      <button id="btnBrowserVoice" style="padding:8px 20px;font-size:10px;letter-spacing:2px;background:none;border:none;color:#484f58;cursor:pointer;font-family:inherit;font-weight:600;border-radius:0 100px 100px 0" onclick="selectVoice('browser')">BROWSER</button>
    </div>

    <!-- AI voice status -->
    <div id="aiStatus" class="voice-note" style="color:#484f58;margin-bottom:16px"></div>

    <button class="start-btn" id="startBtn" onclick="beginSession()">BEGIN SESSION</button>
    <div class="voice-note" id="voiceNote">Voice-guided with ambient 432Hz audio. Use earphones.</div>
  </div>

  <!-- ACTIVE SESSION -->
  <div id="activeSession" class="hidden">
    <div class="breath-circle" id="breathCircle"></div>
    <div class="breath-cue" id="breathCue" style="font-size:11px;letter-spacing:3px;color:#484f58;margin-bottom:16px;height:20px"></div>
    <div class="phase-label" id="phaseLabel" style="color:#4ecdc4">{session_type.upper()}</div>
    <div class="active-name block-transition" id="blockName">...</div>
    <div class="active-instruction block-transition" id="blockInstruction">...</div>
    <div class="timer" id="timer">7:00</div>
    <div class="block-timer" id="blockTimer">BLOCK 1/7 - 1:00</div>
    <div class="paused-label" id="pausedLabel">PAUSED</div>
    <div class="timer-label">REMAINING</div>
    <button class="pause-btn" id="pauseBtn" onclick="togglePause()">PAUSE</button>
    <div class="progress-bar"><div class="progress-fill" id="progress"></div></div>
    <div class="dots" id="dots"></div>
  </div>

  <!-- COMPLETE -->
  <div id="complete" class="hidden">
    <div class="complete-check">&#10003;</div>
    <div class="complete-title">SESSION COMPLETE</div>
    <div class="complete-text" id="closingText">{closing}</div>
    <div id="streakStatus" style="font-size:12px;color:#E85D04;font-weight:600;margin-bottom:24px"></div>

    <!-- CTA: email capture OR share (toggled by JS) -->
    <div id="ctaEmail" class="hidden" style="margin-bottom:24px">
      <p style="color:#8b949e;font-size:13px;margin-bottom:12px">Get session reminders &amp; verify your Jerome#</p>
      <div style="display:flex;gap:8px;justify-content:center;max-width:360px;margin:0 auto">
        <input type="email" id="email-input" placeholder="your@email.com"
               style="flex:1;padding:10px 14px;background:#161b22;border:1px solid #30363d;border-radius:8px;color:#e6edf3;font-family:'JetBrains Mono',monospace;font-size:14px;outline:none">
        <button onclick="submitEmail()"
                style="padding:10px 20px;background:#E85D04;border:none;border-radius:8px;color:white;font-family:'JetBrains Mono',monospace;cursor:pointer;font-size:14px">Verify</button>
      </div>
      <div id="email-status" style="margin-top:8px;font-size:13px"></div>
    </div>
    <div id="ctaShare" class="hidden" style="margin-bottom:24px">
      <button class="share-btn primary" onclick="shareSession()">Share</button>
    </div>
    <div class="toast" id="toast">copied to clipboard</div>

    <div class="complete-links" style="color:#30363d">
      <a href="/">Home</a>
      <a href="/globe">Globe</a>
      <a href="/timer">Replay</a>
    </div>
  </div>

</div>

<!-- Ambient audio toggle -->
<button class="ambient-toggle" id="ambientToggle" onclick="toggleAmbient()">
  <span class="ambient-dot" id="ambientDot"></span>
  432Hz
</button>

<script>
// ── Config ──
const pageLoadTime = Date.now();
const blocks = {blocks_json};
const sessionType = '{session_type}';
const closingText = {closing_js};
const aiAvailable = {ai_available};
const TOTAL = blocks.reduce((s, b) => s + (b.duration_seconds || 60), 0);

const TYPE_COLORS = {{
  breathwork: '#4ecdc4',
  meditation: '#79c0ff',
  reflection: '#b392f0',
  preparation: '#e8713a',
}};
const typeColor = TYPE_COLORS[sessionType] || '#E85D04';

// ── State ──
let currentBlock = 0;
let remaining = 0;
let totalElapsed = 0;
let interval = null;
let userName = '';
let jeromeNumber = null;
let communityData = {{ total_jeromes: 0, sessions_today: 0, countries: 0 }};
let isPaused = false;
let sessionStarted = false;
let sessionFinished = false;
let totalRemaining = 0;
let breathTimeout = null;

// ── Clipboard helper (fallback for iOS/older browsers) ──
async function copyToClipboard(text) {{
  try {{
    await navigator.clipboard.writeText(text);
    return true;
  }} catch {{
    const ta = document.createElement('textarea');
    ta.value = text;
    ta.style.position = 'fixed';
    ta.style.left = '-9999px';
    document.body.appendChild(ta);
    ta.select();
    document.execCommand('copy');
    document.body.removeChild(ta);
    return true;
  }}
}}

// ── ElevenLabs AI Voice ──
let voiceMode = aiAvailable ? 'ai' : 'browser';
let aiAudio = null;
let aiReady = false;
let aiGenerating = false;

function selectVoice(mode) {{
  if (mode === 'ai' && !aiAvailable) return;
  voiceMode = mode;
  const btnAi = document.getElementById('btnAiVoice');
  const btnBrowser = document.getElementById('btnBrowserVoice');
  btnAi.style.background = mode === 'ai' ? '#E85D04' : 'none';
  btnAi.style.color = mode === 'ai' ? '#fff' : '#484f58';
  btnBrowser.style.background = mode === 'browser' ? '#E85D04' : 'none';
  btnBrowser.style.color = mode === 'browser' ? '#fff' : '#484f58';
  document.getElementById('voiceNote').textContent = mode === 'ai'
    ? 'AI-narrated by ElevenLabs. Use earphones.'
    : 'Browser voice with ambient 432Hz audio. Use earphones.';
}}

async function prepareAiVoice() {{
  if (!aiAvailable || aiReady || aiGenerating) return;
  aiGenerating = true;
  const status = document.getElementById('aiStatus');
  status.textContent = 'Generating AI voice...';

  try {{
    const resp = await fetch('/voice/wellness/generate', {{ method: 'POST' }});
    const data = await resp.json();
    if (resp.ok) {{
      aiAudio = new Audio('/voice/wellness/audio');
      aiAudio.preload = 'auto';
      aiAudio.addEventListener('canplaythrough', () => {{
        aiReady = true;
        status.textContent = 'AI voice ready.';
      }}, {{ once: true }});
      aiAudio.addEventListener('error', () => {{
        status.textContent = 'Audio load failed. Using browser voice.';
        voiceMode = 'browser';
      }});
      // Timeout fallback
      setTimeout(() => {{
        if (!aiReady) {{
          status.textContent = 'AI voice ready.';
          aiReady = true;
        }}
      }}, 5000);
    }} else {{
      status.textContent = (data.error || 'AI voice unavailable') + '. Using browser voice.';
      voiceMode = 'browser';
    }}
  }} catch(e) {{
    status.textContent = 'Network error. Using browser voice.';
    voiceMode = 'browser';
  }}
  aiGenerating = false;
}}

function initVoiceToggle() {{
  if (!aiAvailable) {{
    document.getElementById('btnAiVoice').disabled = true;
    document.getElementById('btnAiVoice').style.opacity = '0.3';
    document.getElementById('btnAiVoice').style.cursor = 'not-allowed';
    voiceMode = 'browser';
    selectVoice('browser');
  }} else {{
    // Auto-generate AI voice in background
    prepareAiVoice();
  }}
}}

// ── Ambient 432Hz Audio (Web Audio API) ──
let ambientCtx = null;
let ambientOsc = null;
let ambientGain = null;
let ambientOn = true;

function initAmbient() {{
  try {{
    ambientCtx = new (window.AudioContext || window.webkitAudioContext)();
    ambientGain = ambientCtx.createGain();
    ambientGain.gain.value = 0;
    ambientGain.connect(ambientCtx.destination);

    // Primary tone: 432Hz (relaxation frequency)
    ambientOsc = ambientCtx.createOscillator();
    ambientOsc.type = 'sine';
    ambientOsc.frequency.value = 432;
    ambientOsc.connect(ambientGain);
    ambientOsc.start();

    // Second tone: 438Hz (6Hz binaural beat = theta waves / meditation)
    const osc2 = ambientCtx.createOscillator();
    osc2.type = 'sine';
    osc2.frequency.value = 438;
    osc2.connect(ambientGain);
    osc2.start();
  }} catch(e) {{ /* Web Audio not supported */ }}
}}

function startAmbient() {{
  if (!ambientCtx || !ambientOn) return;
  if (ambientCtx.state === 'suspended') ambientCtx.resume();
  ambientGain.gain.linearRampToValueAtTime(0.06, ambientCtx.currentTime + 3);
}}

function stopAmbient() {{
  if (!ambientCtx || !ambientGain) return;
  ambientGain.gain.linearRampToValueAtTime(0, ambientCtx.currentTime + 2);
}}

function toggleAmbient() {{
  ambientOn = !ambientOn;
  const dot = document.getElementById('ambientDot');
  if (ambientOn) {{
    dot.classList.remove('off');
    if (totalElapsed > 0) startAmbient();
  }} else {{
    dot.classList.add('off');
    stopAmbient();
  }}
}}

// ── Community Stats ──
async function loadCommunityStats() {{
  try {{
    const resp = await fetch('/stats');
    const data = await resp.json();
    communityData = data;
    document.getElementById('statJeromes').textContent = data.total_jeromes || 0;
    document.getElementById('statToday').textContent = data.sessions_today || 0;
    document.getElementById('statCountries').textContent = data.countries || 0;
  }} catch(e) {{
    // Silently fail
  }}
}}

// ── Onboarding ──
function checkOnboarding() {{
  const stored = localStorage.getItem('jerome7_user');
  if (stored) {{
    const user = JSON.parse(stored);
    userName = user.name || '';
    jeromeNumber = user.jeromeNumber || null;
    return;
  }}
  document.getElementById('onboarding').classList.remove('hidden');
}}

async function submitOnboarding() {{
  const name = document.getElementById('ob-name').value.trim();
  if (!name) {{ document.getElementById('ob-name').style.borderColor = '#f85149'; return; }}

  const goal = document.getElementById('ob-goal').value;

  const btn = document.getElementById('ob-submit');
  btn.disabled = true; btn.textContent = 'CLAIMING...';

  try {{
    const resp = await fetch('/pledge', {{
      method: 'POST',
      headers: {{ 'Content-Type': 'application/json' }},
      body: JSON.stringify({{ name: name, goal: goal || 'just_try', timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC', source: 'web', website: document.getElementById('hp-field').value, elapsed: Date.now() - pageLoadTime, fp: navigator.language + '|' + screen.width + 'x' + screen.height + '|' + new Date().getTimezoneOffset() }}),
    }});
    const data = await resp.json();

    const userData = {{
      name: name,
      userId: data.user_id,
      jeromeNumber: data.jerome_number,
      authToken: data.auth_token,
      goal: goal,
    }};
    localStorage.setItem('jerome7_user', JSON.stringify(userData));
    userName = name;
    jeromeNumber = data.jerome_number;

    document.getElementById('onboard-greeting').textContent =
      'You are Jerome' + (data.jerome_number || '?') + '!';
    btn.textContent = 'LET\\'S GO';
    btn.disabled = false;
    btn.onclick = () => document.getElementById('onboarding').classList.add('hidden');
  }} catch(e) {{
    localStorage.setItem('jerome7_user', JSON.stringify({{ name: name, goal: goal }}));
    userName = name;
    document.getElementById('onboarding').classList.add('hidden');
  }}
}}

function skipOnboarding() {{
  localStorage.setItem('jerome7_user', JSON.stringify({{ name: 'builder', skipped: true }}));
  userName = 'builder';
  document.getElementById('onboarding').classList.add('hidden');
}}

// ── Blocks preview ──
function renderPreview() {{
  const el = document.getElementById('blocksPreview');
  el.innerHTML = blocks.map((b, i) => {{
    const dur = b.duration_seconds || 60;
    const m = Math.floor(dur / 60);
    const s = dur % 60;
    const time = m > 0 ? m + ':' + s.toString().padStart(2, '0') : s + 's';
    return '<div class="block-row">' +
      '<span class="block-num">' + (i+1) + '</span>' +
      '<span class="block-name-prev">' + b.name + '</span>' +
      '<span class="block-dur">' + time + '</span>' +
    '</div>';
  }}).join('');
}}

// ── Voice narration (browser speech) ──
function speak(text) {{
  if (!('speechSynthesis' in window)) return;
  window.speechSynthesis.cancel();
  const u = new SpeechSynthesisUtterance(text);
  u.rate = 0.8; u.pitch = 1.0; u.volume = 1.0;
  const voices = window.speechSynthesis.getVoices();
  const preferredNames = ['Samantha', 'Karen', 'Moira', 'Daniel'];
  let chosen = voices.find(v => preferredNames.some(n => v.name.includes(n)));
  if (!chosen) chosen = voices.find(v => v.lang && v.lang.startsWith('en'));
  if (chosen) u.voice = chosen;
  window.speechSynthesis.speak(u);
}}

// ── Breathing animation ──
function startBreathing() {{
  const circle = document.getElementById('breathCircle');
  const cue = document.getElementById('breathCue');
  if (!circle || !cue) return;
  circle.classList.add('active');
  circle.style.borderColor = typeColor;

  const patterns = {{
    breathwork: {{ inhale: 4000, hold1: 4000, exhale: 4000, hold2: 4000 }},
    meditation: {{ inhale: 6000, hold1: 1000, exhale: 6000, hold2: 1000 }},
    reflection: {{ inhale: 5000, hold1: 2000, exhale: 5000, hold2: 2000 }},
    preparation: {{ inhale: 3000, hold1: 1000, exhale: 3000, hold2: 1000 }},
  }};
  const p = patterns[sessionType] || patterns.meditation;

  function cycle() {{
    try {{
    if (sessionFinished || isPaused) return;
    circle.className = 'breath-circle active inhale';
    cue.textContent = 'BREATHE IN';
    breathTimeout = setTimeout(() => {{
      if (sessionFinished || isPaused) return;
      circle.className = 'breath-circle active hold';
      cue.textContent = 'HOLD';
      breathTimeout = setTimeout(() => {{
        if (sessionFinished || isPaused) return;
        circle.className = 'breath-circle active exhale';
        cue.textContent = 'BREATHE OUT';
        breathTimeout = setTimeout(() => {{
          if (sessionFinished || isPaused) return;
          circle.className = 'breath-circle active';
          cue.textContent = 'HOLD';
          breathTimeout = setTimeout(() => {{
            if (!sessionFinished && !isPaused) cycle();
          }}, p.hold2);
        }}, p.exhale);
      }}, p.hold1);
    }}, p.inhale);
    }} catch(e) {{ /* breathing animation error - session continues */ }}
  }}
  cycle();
}}

function stopBreathing() {{
  if (breathTimeout) {{ clearTimeout(breathTimeout); breathTimeout = null; }}
  const circle = document.getElementById('breathCircle');
  const cue = document.getElementById('breathCue');
  if (circle) {{ circle.classList.remove('active'); circle.className = 'breath-circle'; }}
  if (cue) cue.textContent = '';
}}

function pauseBreathing() {{
  if (breathTimeout) {{ clearTimeout(breathTimeout); breathTimeout = null; }}
  const cue = document.getElementById('breathCue');
  if (cue) cue.textContent = '';
}}

function resumeBreathing() {{
  startBreathing();
}}

// ── Session runner ──
function beginSession() {{
  document.getElementById('preStart').classList.add('hidden');
  document.getElementById('activeSession').classList.remove('hidden');

  // Init and start ambient audio
  initAmbient();
  startAmbient();

  // Build dots
  document.getElementById('dots').innerHTML = blocks.map((_, i) =>
    '<div class="dot" id="d' + i + '"></div>').join('');

  // Start AI voice narration OR browser speech
  if (voiceMode === 'ai' && aiReady && aiAudio) {{
    aiAudio.currentTime = 0;
    aiAudio.play().catch(() => {{}});
  }} else {{
    // Personalized welcome with Jerome# (browser speech fallback)
    let greeting = 'Welcome to Jerome 7.';
    if (userName && jeromeNumber) {{
      greeting = 'Good morning, Jerome' + jeromeNumber + '.';
    }} else if (userName && userName !== 'builder') {{
      greeting = 'Welcome, ' + userName + '.';
    }}
    speak(greeting + ' Today is a ' + sessionType + ' session. Let\\'s begin.');
  }}

  currentBlock = 0;
  totalElapsed = 0;
  totalRemaining = TOTAL;
  sessionStarted = true;
  sessionFinished = false;
  isPaused = false;
  document.getElementById('pauseBtn').classList.add('visible');
  startBreathing();
  showBlock(0);
  tick();
}}

function togglePause() {{
  if (!sessionStarted || sessionFinished) return;
  if (isPaused) {{
    // Resume
    isPaused = false;
    document.getElementById('pauseBtn').textContent = 'PAUSE';
    document.getElementById('pausedLabel').classList.remove('show');
    if (voiceMode === 'ai' && aiAudio && !aiAudio.ended) {{
      aiAudio.play().catch(() => {{}});
    }}
    startAmbient();
    resumeBreathing();
    tick();
  }} else {{
    // Pause
    isPaused = true;
    clearInterval(interval);
    interval = null;
    document.getElementById('pauseBtn').textContent = 'RESUME';
    document.getElementById('pausedLabel').classList.add('show');
    if (voiceMode === 'ai' && aiAudio && !aiAudio.paused) {{
      aiAudio.pause();
    }}
    if ('speechSynthesis' in window) window.speechSynthesis.cancel();
    stopAmbient();
    pauseBreathing();
  }}
}}

function showBlock(i) {{
  const b = blocks[i];
  const phase = b.phase || sessionType;
  const nameEl = document.getElementById('blockName');
  const instrEl = document.getElementById('blockInstruction');

  // Fade out current text
  nameEl.classList.add('fade');
  instrEl.classList.add('fade');

  setTimeout(() => {{
    document.getElementById('phaseLabel').textContent = (phase || sessionType).toUpperCase();
    document.getElementById('phaseLabel').style.color = typeColor;
    nameEl.textContent = b.name.toUpperCase();
    instrEl.textContent = b.instruction || '';
    remaining = b.duration_seconds || 60;

    // Fade in new text
    nameEl.classList.remove('fade');
    instrEl.classList.remove('fade');
  }}, 300);

  remaining = b.duration_seconds || 60;
  document.getElementById('timer').textContent = formatTime(totalRemaining);
  document.getElementById('blockTimer').textContent = 'BLOCK ' + (i + 1) + '/' + blocks.length + ' - ' + formatTime(remaining);

  // Update dots
  blocks.forEach((_, j) => {{
    const dot = document.getElementById('d' + j);
    dot.className = 'dot' + (j < i ? ' done' : j === i ? ' active' : '');
  }});

  // Narrate block (only with browser speech -- AI voice handles its own pacing)
  if (voiceMode !== 'ai' || !aiReady) {{
    setTimeout(() => {{ speak(b.name + '. ' + (b.instruction || '')); }}, 400);
  }}
}}

function tick() {{
  interval = setInterval(() => {{
    remaining--;
    totalElapsed++;
    totalRemaining--;
    document.getElementById('timer').textContent = formatTime(totalRemaining);
    document.getElementById('blockTimer').textContent = 'BLOCK ' + (currentBlock + 1) + '/' + blocks.length + ' - ' + formatTime(remaining);
    document.getElementById('progress').style.width = (totalElapsed / TOTAL * 100) + '%';
    document.getElementById('progress').style.backgroundColor = typeColor;

    if (remaining <= 0) {{
      currentBlock++;
      if (currentBlock < blocks.length) {{
        showBlock(currentBlock);
      }} else {{
        clearInterval(interval);
        finishSession();
      }}
    }}
  }}, 1000);
}}

function finishSession() {{
  sessionFinished = true;
  document.getElementById('pauseBtn').classList.remove('visible');
  document.getElementById('pausedLabel').classList.remove('show');
  // Stop breathing animation
  stopBreathing();
  // Fade out ambient
  stopAmbient();

  document.getElementById('activeSession').classList.add('hidden');
  document.getElementById('complete').classList.remove('hidden');
  document.getElementById('closingText').textContent = closingText;

  // Record streak
  recordSession();

  // Show streak status with Jerome#
  const day = getStreakDay();
  const jLabel = jeromeNumber ? 'Jerome' + jeromeNumber : (userName || 'YU');
  document.getElementById('streakStatus').textContent =
    'Day ' + day + '. ' + jLabel + ' showed up.';

  // Show CTA: email capture if no email yet, share button otherwise
  const user = JSON.parse(localStorage.getItem('jerome7_user') || '{{}}');
  if (user.userId && !user.emailSubmitted) {{
    document.getElementById('ctaEmail').classList.remove('hidden');
  }} else {{
    document.getElementById('ctaShare').classList.remove('hidden');
  }}

  // Stop AI audio if playing
  if (aiAudio && !aiAudio.paused) {{
    aiAudio.pause();
  }}

  // Personalized closing narration (browser speech only — AI voice includes its own closing)
  if (voiceMode !== 'ai' || !aiReady) {{
    const closingNarration = 'Session complete. Day ' + day + '. ' + jLabel + ' showed up. ' + closingText;
    speak(closingNarration);
  }}
}}

function formatTime(s) {{
  const m = Math.floor(s / 60);
  const sec = s % 60;
  return m + ':' + sec.toString().padStart(2, '0');
}}

// ── Streak tracking ──
function recordSession() {{
  const today = new Date().toISOString().slice(0, 10);
  const data = JSON.parse(localStorage.getItem('jerome7_streak') || '{{}}');
  if (data.lastDate === today) return;

  let day = data.day || 0;
  if (data.lastDate) {{
    const diff = Math.floor((new Date(today) - new Date(data.lastDate)) / 86400000);
    day = diff <= 3 ? day + 1 : 1;
  }} else {{
    day = 1;
  }}

  localStorage.setItem('jerome7_streak', JSON.stringify({{
    day: day, lastDate: today,
    totalSessions: (data.totalSessions || 0) + 1,
  }}));

  // Log to server
  const user = JSON.parse(localStorage.getItem('jerome7_user') || '{{}}');
  if (user.userId && user.authToken) {{
    fetch('/log/' + user.userId, {{
      method: 'POST',
      headers: {{
        'Content-Type': 'application/json',
        'Authorization': 'Bearer ' + user.authToken,
      }},
      body: JSON.stringify({{ duration_minutes: 7 }}),
    }}).catch(() => {{}});
  }}
}}

// ── Share ──
function getStreakDay() {{
  const data = JSON.parse(localStorage.getItem('jerome7_streak') || '{{}}');
  return data.day || 1;
}}

function buildCardText() {{
  const day = getStreakDay();
  const user = JSON.parse(localStorage.getItem('jerome7_user') || '{{}}');
  const jnum = user.jeromeNumber ? 'Jerome' + user.jeromeNumber : 'Jerome7';
  return 'Day ' + day + '. 7 minutes. \\u2713\\n\\n' +
    'I\\'m ' + jnum + '. @Jerome7app\\n\\n' +
    'https://jerome7.com/join';
}}

async function shareSession() {{
  const user = JSON.parse(localStorage.getItem('jerome7_user') || '{{}}');
  const jnum = user.jeromeNumber || '';
  const link = 'https://jerome7.com/timer' + (jnum ? '?ref=jerome' + jnum : '');
  const text = buildCardText();

  // Try native share first (mobile), fall back to clipboard
  if (navigator.share) {{
    try {{
      await navigator.share({{ text: text, url: link }});
      return;
    }} catch(e) {{ /* user cancelled or unsupported */ }}
  }}
  const ok = await copyToClipboard(text);
  if (ok) {{
    const toast = document.getElementById('toast');
    toast.style.display = 'block';
    setTimeout(() => toast.style.display = 'none', 2000);
  }}
}}

// ── Email verification ──
async function submitEmail() {{
  const email = document.getElementById('email-input').value.trim();
  if (!email) return;
  const statusEl = document.getElementById('email-status');
  const user = JSON.parse(localStorage.getItem('jerome7_user') || '{{}}');
  if (!user.userId || !user.authToken) {{
    statusEl.style.color = '#f85149';
    statusEl.textContent = 'Complete onboarding first.';
    return;
  }}
  try {{
    const res = await fetch('/user/' + user.userId + '/email', {{
      method: 'POST',
      headers: {{
        'Content-Type': 'application/json',
        'Authorization': 'Bearer ' + user.authToken,
      }},
      body: JSON.stringify({{email}}),
    }});
    const data = await res.json();
    if (res.ok) {{
      statusEl.style.color = '#E85D04';
      statusEl.textContent = 'Verification link ready! Check back soon.';
      document.getElementById('email-input').disabled = true;
      // Mark email submitted and swap CTA
      const u = JSON.parse(localStorage.getItem('jerome7_user') || '{{}}');
      u.emailSubmitted = true;
      localStorage.setItem('jerome7_user', JSON.stringify(u));
      setTimeout(() => {{
        document.getElementById('ctaEmail').classList.add('hidden');
        document.getElementById('ctaShare').classList.remove('hidden');
      }}, 2000);
    }} else {{
      statusEl.style.color = '#f85149';
      statusEl.textContent = data.detail || 'Something went wrong.';
    }}
  }} catch(e) {{
    statusEl.style.color = '#f85149';
    statusEl.textContent = 'Connection error. Try again.';
  }}
}}

// ── Init ──
if ('speechSynthesis' in window) window.speechSynthesis.getVoices();
renderPreview();
checkOnboarding();
loadCommunityStats();
initVoiceToggle();
</script>
</body>
</html>"""
    return HTMLResponse(
        content=html,
        headers={"Cache-Control": "public, max-age=300, stale-while-revalidate=3300"},
    )
