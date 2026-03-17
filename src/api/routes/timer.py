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
    # json.dumps is safe for embedding in <script> (escapes </script>, quotes, etc.)
    # html_escape only for content rendered as HTML text, NOT for speech/JS strings
    blocks_raw = data.get("blocks", [])
    if not isinstance(blocks_raw, list):
        blocks_raw = []
    sanitized_blocks = []
    for b in blocks_raw:
        if not isinstance(b, dict):
            continue
        # Strip any HTML tags from AI output but keep apostrophes natural
        b["name"] = str(b.get("name", "")).replace("<", "").replace(">", "")
        b["instruction"] = str(b.get("instruction", "")).replace("<", "").replace(">", "")
        sanitized_blocks.append(b)
    blocks_raw = sanitized_blocks
    blocks_json = json.dumps(blocks_raw)  # json.dumps escapes for safe JS embedding
    title = html_escape(data.get("session_title", session_type.title()))
    closing_raw = str(data.get("closing", "You showed up. That's the win.")).replace("<", "").replace(">", "")
    closing_js = json.dumps(closing_raw)

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
    min-height: 100vh; display: flex; align-items: flex-start; justify-content: center;
    padding: 80px 20px 20px;
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

  /* ── FREQUENCY PILLS ── */
  .freq-pill {{
    background: #161b22; border: 1px solid #21262d;
    border-radius: 100px; padding: 6px 14px; cursor: pointer;
    font-family: inherit; font-size: 11px; color: #8b949e;
    transition: all 0.2s; white-space: nowrap;
  }}
  .freq-pill:hover {{ border-color: #30363d; color: #f0f6fc; }}
  .freq-pill.selected {{ border-color: #E85D04; color: #E85D04; background: rgba(232,93,4,0.08); }}

  /* ── ACTIVE SESSION ── */
  .phase-label {{
    font-size: 10px; letter-spacing: 3px; margin-bottom: 12px;
    transition: color 0.4s;
  }}
  .active-name {{
    font-size: 20px; font-weight: 700; color: #8b949e;
    margin-bottom: 8px; line-height: 1.2;
    letter-spacing: 2px;
  }}
  .active-instruction {{
    display: none;
  }}
  .timer {{
    font-size: 64px; font-weight: 800; color: #f0f6fc;
    letter-spacing: -2px; margin-bottom: 8px;
    font-variant-numeric: tabular-nums;
    opacity: 0.7;
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
    width: 280px; height: 280px; border-radius: 50%;
    border: 2px solid; opacity: 0.12;
    margin: 0 auto 24px;
    display: none;
  }}
  .breath-circle.active {{ display: block; animation: breathPulse var(--breath-speed, 8s) ease-in-out infinite; }}
  @keyframes breathPulse {{
    0% {{ transform: scale(0.7); opacity: 0.06; }}
    35% {{ transform: scale(1.2); opacity: 0.35; }}
    50% {{ transform: scale(1.2); opacity: 0.3; }}
    85% {{ transform: scale(0.7); opacity: 0.06; }}
    100% {{ transform: scale(0.7); opacity: 0.06; }}
  }}

  /* ── BLOCK TRANSITION ── */
  .block-transition {{ transition: opacity 0.3s ease; }}
  .block-transition.fade {{ opacity: 0; }}

  /* ── BLOCK TIMER (small) ── */
  .block-timer {{
    display: none;
  }}

  @media (max-width: 480px) {{
    .timer {{ font-size: 64px; }}
    .session-title {{ font-size: 24px; }}
    .active-name {{ font-size: 16px; }}
    .breath-circle {{ width: 200px; height: 200px; }}
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
    <h2 id="onboard-greeting">You showed up. That's the hardest part.</h2>
    <div class="subtitle">Claim your Jerome# identity. Takes 10 seconds.</div>

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
    <!-- Personalized greeting (filled by JS) -->
    <div id="personalGreeting" style="font-size:13px;color:#484f58;letter-spacing:1px;margin-bottom:32px;min-height:20px"></div>

    <div class="session-type" id="sessionType" style="--type-color:#4ecdc4">{session_type.upper()}</div>
    <div class="session-title">{title}</div>
    <div class="session-desc">{type_desc}</div>

    <button class="start-btn" id="startBtn" onclick="beginSession().catch(console.error)" style="margin-bottom:24px">START</button>

    <!-- Frequency selector: same session, different brain state -->
    <div style="font-size:9px;color:#484f58;letter-spacing:1px;margin-bottom:12px">CHOOSE YOUR FREQUENCY</div>
    <div id="freqRow" style="display:flex;gap:6px;justify-content:center;flex-wrap:wrap;margin-bottom:8px">
      <button class="freq-pill selected" onclick="selectFreq(this,'chill')" data-freq="chill">chill</button>
      <button class="freq-pill" onclick="selectFreq(this,'flow')" data-freq="flow">focus</button>
      <button class="freq-pill" onclick="selectFreq(this,'vibe')" data-freq="vibe">vibe</button>
      <button class="freq-pill" onclick="selectFreq(this,'boss')" data-freq="boss">energy</button>
      <button class="freq-pill" onclick="selectFreq(this,'war')" data-freq="war">intense</button>
    </div>
    <div id="freqDesc" style="font-size:10px;color:#484f58;margin-bottom:16px;min-height:16px">theta (6Hz) - reduces anxiety, calms the mind</div>
    <div style="font-size:8px;color:#30363d;letter-spacing:1px">SAME SESSION. DIFFERENT BRAIN STATE. USE EARPHONES.</div>

    <!-- Hidden voice toggle (AI auto-selected if available) -->
    <div id="voiceToggle" style="display:none">
      <button id="btnAiVoice" onclick="selectVoice('ai')">AI</button>
      <button id="btnBrowserVoice" onclick="selectVoice('browser')">BROWSER</button>
    </div>
    <div id="aiStatus" style="display:none"></div>

    <!-- Jerome# identity link -->
    <div id="identityLink" style="margin-top:24px;font-size:11px;color:#484f58">
      <span id="identityReturning" style="display:none">
        <a href="/graph" style="color:#E85D04;text-decoration:none">view your wellness graph</a>
      </span>
      <span id="identityNew">
        complete your first session to claim your Jerome#
      </span>
    </div>
  </div>

  <!-- ACTIVE SESSION -->
  <div id="activeSession" class="hidden">
    <div class="phase-label" id="phaseLabel" style="color:#4ecdc4">{session_type.upper()}</div>
    <div class="active-name block-transition" id="blockName">...</div>
    <div class="breath-circle" id="breathCircle"></div>
    <div class="breath-cue" id="breathCue" style="font-size:11px;letter-spacing:3px;color:#484f58;margin-bottom:16px;height:20px"></div>
    <div class="timer" id="timer">7:00</div>
    <div class="paused-label" id="pausedLabel">PAUSED</div>
    <div class="timer-label">REMAINING</div>
    <button class="pause-btn" id="pauseBtn" onclick="togglePause()">PAUSE</button>
    <div class="progress-bar"><div class="progress-fill" id="progress"></div></div>
    <div class="dots" id="dots"></div>
  </div>

  <!-- COMPLETE -->
  <div id="complete" class="hidden">
    <div class="complete-check">&#10003;</div>
    <div class="complete-title" id="completeTitle">SESSION COMPLETE</div>
    <div class="complete-text" id="closingText">{html_escape(closing_raw)}</div>

    <!-- Streak visual -->
    <div id="streakVisual" style="margin:24px 0">
      <div id="streakNumber" style="font-size:48px;font-weight:800;color:#E85D04">1</div>
      <div style="font-size:10px;letter-spacing:2px;color:#484f58">DAY STREAK</div>
    </div>

    <!-- Post-session onboarding (only if not registered) -->
    <div id="postOnboard" class="hidden" style="margin-bottom:24px;background:#161b22;border:1px solid #21262d;border-radius:12px;padding:24px;max-width:360px;margin-left:auto;margin-right:auto">
      <div style="font-size:11px;letter-spacing:2px;color:#E85D04;margin-bottom:12px">CLAIM YOUR JEROME#</div>
      <input type="text" id="post-ob-name" placeholder="your name" maxlength="50" autocomplete="off"
             style="width:100%;padding:10px 14px;background:#0d1117;border:1px solid #30363d;border-radius:8px;color:#f0f6fc;font-family:inherit;font-size:14px;outline:none;margin-bottom:8px">
      <input type="email" id="post-ob-email" placeholder="email (optional)" autocomplete="off"
             style="width:100%;padding:10px 14px;background:#0d1117;border:1px solid #30363d;border-radius:8px;color:#f0f6fc;font-family:inherit;font-size:14px;outline:none;margin-bottom:12px">
      <div style="position:absolute;left:-9999px" aria-hidden="true"><input type="text" id="hp-field2" tabindex="-1" autocomplete="off"></div>
      <button onclick="postSessionRegister()" style="width:100%;padding:12px;background:#E85D04;border:none;border-radius:100px;color:#fff;font-family:inherit;font-size:13px;font-weight:700;letter-spacing:1px;cursor:pointer">SAVE MY STREAK</button>
      <div id="post-ob-status" style="font-size:11px;margin-top:8px;color:#7ee787"></div>
    </div>

    <!-- Wellness graph + share CTA (shown if registered) -->
    <div id="wellnessGraph" class="hidden" style="margin-bottom:24px;max-width:400px;margin-left:auto;margin-right:auto">
      <img id="graphImg" src="" alt="Wellness contribution graph" style="width:100%;border-radius:6px;border:1px solid #21262d;margin-bottom:16px">

      <div style="font-size:12px;color:#8b949e;line-height:1.6;margin-bottom:16px">
        You showed up. Show the world.<br>
        <span style="color:#484f58">Add this to your GitHub profile README.</span>
      </div>

      <!-- One-click copy: the hero CTA -->
      <button onclick="copyGraph()" style="width:100%;padding:14px;background:#E85D04;border:none;border-radius:100px;color:#fff;font-family:inherit;font-size:14px;font-weight:700;letter-spacing:1px;cursor:pointer;margin-bottom:8px;transition:all 0.2s" onmouseover="this.style.background='#ff6b1a'" onmouseout="this.style.background='#E85D04'">ADD TO GITHUB PROFILE</button>

      <div style="display:flex;gap:8px;justify-content:center;margin-top:8px">
        <button class="share-btn" onclick="shareSession()">Share</button>
        <button class="share-btn" onclick="tweetSession()">Post on X</button>
      </div>
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
  <span id="freqLabel">396Hz</span>
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
  const vn = document.getElementById('voiceNote');
  if (vn) vn.textContent = mode === 'ai'
    ? 'AI-narrated by ElevenLabs. Use earphones.'
    : 'Browser voice with ambient 432Hz audio. Use earphones.';
}}

async function prepareAiVoice() {{
  if (!aiAvailable || aiReady || aiGenerating) return;
  aiGenerating = true;
  const status = document.getElementById('aiStatus');
  const startBtn = document.getElementById('startBtn');
  status.style.display = 'block';
  status.textContent = 'loading AI voice...';
  if (startBtn) {{ startBtn.textContent = 'LOADING VOICE...'; startBtn.style.opacity = '0.6'; }}

  try {{
    const resp = await fetch('/voice/wellness/generate', {{ method: 'POST' }});
    const data = await resp.json();
    if (resp.ok) {{
      aiAudio = new Audio('/voice/wellness/audio?t=' + Date.now());
      aiAudio.preload = 'auto';
      aiAudio.addEventListener('canplaythrough', () => {{
        aiReady = true;
        status.textContent = 'AI voice ready';
        if (startBtn) {{ startBtn.textContent = 'START'; startBtn.style.opacity = '1'; }}
      }}, {{ once: true }});
      aiAudio.addEventListener('error', () => {{
        status.textContent = 'using browser voice';
        voiceMode = 'browser';
        if (startBtn) {{ startBtn.textContent = 'START'; startBtn.style.opacity = '1'; }}
      }});
      // Timeout: if audio doesn't load in 15s, proceed with browser voice
      setTimeout(() => {{
        if (!aiReady) {{
          voiceMode = 'browser';
          status.textContent = 'using browser voice';
          if (startBtn) {{ startBtn.textContent = 'START'; startBtn.style.opacity = '1'; }}
        }}
      }}, 15000);
    }} else {{
      status.textContent = (data.error || 'AI voice unavailable');
      voiceMode = 'browser';
      if (startBtn) {{ startBtn.textContent = 'START'; startBtn.style.opacity = '1'; }}
    }}
  }} catch(e) {{
    status.textContent = 'using browser voice';
    voiceMode = 'browser';
    if (startBtn) {{ startBtn.textContent = 'START'; startBtn.style.opacity = '1'; }}
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

// ── Frequency Presets (binaural beats) ──
const FREQ_PRESETS = {{
  chill:  {{ f1: 396, f2: 402, label: '396Hz', desc: 'theta (6Hz) - reduces anxiety, calms the mind' }},
  flow:   {{ f1: 432, f2: 442, label: '432Hz', desc: 'alpha (10Hz) - deep focus, flow state' }},
  vibe:   {{ f1: 528, f2: 538, label: '528Hz', desc: 'alpha (10Hz) - mood lift, positive energy' }},
  boss:   {{ f1: 639, f2: 653, label: '639Hz', desc: 'beta (14Hz) - confidence, clarity' }},
  war:    {{ f1: 741, f2: 761, label: '741Hz', desc: 'beta (20Hz) - peak intensity, alertness' }},
}};
let selectedFreq = 'chill';

function selectFreq(el, key) {{
  selectedFreq = key;
  document.querySelectorAll('.freq-pill').forEach(c => c.classList.remove('selected'));
  el.classList.add('selected');
  // Update ambient toggle label
  const preset = FREQ_PRESETS[key];
  const fl = document.getElementById('freqLabel');
  if (fl) fl.textContent = preset?.label || '432Hz';
  // Update description
  const fd = document.getElementById('freqDesc');
  if (fd) fd.textContent = preset?.desc || '';
}}

// ── Ambient Audio (Web Audio API) ──
let ambientCtx = null;
let ambientOsc1 = null;
let ambientOsc2 = null;
let ambientGain = null;
let ambientOn = true;

function initAmbient() {{
  try {{
    const preset = FREQ_PRESETS[selectedFreq] || FREQ_PRESETS.chill;
    ambientCtx = new (window.AudioContext || window.webkitAudioContext)();
    ambientGain = ambientCtx.createGain();
    ambientGain.gain.value = 0;
    ambientGain.connect(ambientCtx.destination);

    ambientOsc1 = ambientCtx.createOscillator();
    ambientOsc1.type = 'sine';
    ambientOsc1.frequency.value = preset.f1;
    ambientOsc1.connect(ambientGain);
    ambientOsc1.start();

    ambientOsc2 = ambientCtx.createOscillator();
    ambientOsc2.type = 'sine';
    ambientOsc2.frequency.value = preset.f2;
    ambientOsc2.connect(ambientGain);
    ambientOsc2.start();
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
// ── Onboarding ──
function checkOnboarding() {{
  const stored = localStorage.getItem('jerome7_user');
  if (stored) {{
    const user = JSON.parse(stored);
    userName = user.name || '';
    jeromeNumber = user.jeromeNumber || null;
  }}
  updateIdentityLink();
}}

function updateIdentityLink() {{
  const ret = document.getElementById('identityReturning');
  const nw = document.getElementById('identityNew');
  if (jeromeNumber) {{
    if (ret) ret.style.display = 'inline';
    if (nw) nw.style.display = 'none';
  }} else {{
    if (ret) ret.style.display = 'none';
    if (nw) nw.style.display = 'inline';
  }}
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
// ── Show personalized greeting on page load ──
async function showPersonalGreeting() {{
  const el = document.getElementById('personalGreeting');
  if (!el) return;
  const user = JSON.parse(localStorage.getItem('jerome7_user') || '{{}}');
  const streakData = JSON.parse(localStorage.getItem('jerome7_streak') || '{{}}');
  const hour = new Date().getHours();
  const timeGreet = hour < 12 ? 'good morning' : hour < 17 ? 'good afternoon' : 'good evening';

  if (user.jeromeNumber) {{
    // Try server-side pattern data
    try {{
      const resp = await fetch('/api/insights/' + user.jeromeNumber);
      if (resp.ok) {{
        const data = await resp.json();
        const streak = data.current_streak || 0;
        const rate = data.completion_rate || 0;
        if (streak > 0) {{
          el.textContent = timeGreet + ', jerome' + user.jeromeNumber + '. day ' + streak + '. ' + Math.round(rate) + '% consistent.';
        }} else {{
          el.textContent = timeGreet + ', jerome' + user.jeromeNumber + '. welcome back.';
        }}
        return;
      }}
    }} catch {{}}
    el.textContent = timeGreet + ', jerome' + user.jeromeNumber + '.';
  }} else if (user.name && user.userId) {{
    el.textContent = timeGreet + ', ' + user.name + '. complete a session to claim your jerome#.';
  }} else {{
    el.textContent = timeGreet + ', builder. 7 minutes. lets go.';
  }}
}}

// ── Voice narration (browser speech) ──
let speechVoice = null;

function initSpeechVoice() {{
  if (!('speechSynthesis' in window)) return;
  const voices = window.speechSynthesis.getVoices();
  // Prefer calm, natural voices
  const preferredNames = ['Samantha', 'Karen', 'Moira', 'Tessa', 'Fiona', 'Daniel'];
  speechVoice = voices.find(v => preferredNames.some(n => v.name.includes(n)));
  if (!speechVoice) speechVoice = voices.find(v => v.lang && v.lang.startsWith('en') && v.name.includes('Enhanced'));
  if (!speechVoice) speechVoice = voices.find(v => v.lang && v.lang.startsWith('en'));
}}

function speak(text) {{
  if (!('speechSynthesis' in window)) return;
  window.speechSynthesis.cancel();
  const u = new SpeechSynthesisUtterance(text);
  u.rate = 0.75; u.pitch = 0.95; u.volume = 0.9;
  if (speechVoice) u.voice = speechVoice;
  window.speechSynthesis.speak(u);
}}

// Speak with a calm pause before starting
function speakCalm(text, delayMs) {{
  if (!('speechSynthesis' in window)) return;
  setTimeout(() => {{
    if (sessionFinished || isPaused) return;
    speak(text);
  }}, delayMs || 1500);
}}

// ── Breathing animation (CSS-driven, fast + smooth) ──
const BREATH_SPEEDS = {{
  breathwork: 8,   // 8s full cycle (fast box breathing)
  meditation: 10,  // 10s cycle
  reflection: 12,  // 12s gentle
  preparation: 6,  // 6s energizing
}};

let cueInterval = null;

function startBreathing() {{
  try {{
    const circle = document.getElementById('breathCircle');
    const cue = document.getElementById('breathCue');
    if (!circle || !cue) return;
    const speed = BREATH_SPEEDS[sessionType] || 8;
    circle.style.setProperty('--breath-speed', speed + 's');
    circle.style.borderColor = typeColor;
    circle.classList.add('active');

    // Cue text cycles: in sync with CSS animation
    const inTime = Math.round(speed * 0.35 * 1000);
    const holdTime = Math.round(speed * 0.15 * 1000);
    const outTime = Math.round(speed * 0.35 * 1000);
    const restTime = Math.round(speed * 0.15 * 1000);
    let phase = 0;

    function cueCycle() {{
      if (sessionFinished || isPaused) return;
      if (phase === 0) {{ cue.textContent = 'BREATHE IN'; breathTimeout = setTimeout(cueCycle, inTime); }}
      else if (phase === 1) {{ cue.textContent = 'HOLD'; breathTimeout = setTimeout(cueCycle, holdTime); }}
      else if (phase === 2) {{ cue.textContent = 'BREATHE OUT'; breathTimeout = setTimeout(cueCycle, outTime); }}
      else {{ cue.textContent = ''; breathTimeout = setTimeout(cueCycle, restTime); }}
      phase = (phase + 1) % 4;
    }}
    cueCycle();
  }} catch(e) {{ /* breathing error - session continues */ }}
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
  const circle = document.getElementById('breathCircle');
  if (circle) circle.style.animationPlayState = 'paused';
  const cue = document.getElementById('breathCue');
  if (cue) cue.textContent = '';
}}

function resumeBreathing() {{
  const circle = document.getElementById('breathCircle');
  if (circle) circle.style.animationPlayState = 'running';
  startBreathing();
}}

// ── Adaptive AI greeting ──
function buildAdaptiveGreeting() {{
  const streakData = JSON.parse(localStorage.getItem('jerome7_streak') || '{{}}');
  const day = streakData.day || 0;
  const total = streakData.totalSessions || 0;
  const lastDate = streakData.lastDate;
  const hour = new Date().getHours();

  // Time-of-day awareness
  let timeGreet = 'Welcome';
  if (hour < 12) timeGreet = 'Good morning';
  else if (hour < 17) timeGreet = 'Good afternoon';
  else timeGreet = 'Good evening';

  // Identity
  let identity = '';
  if (userName && jeromeNumber) {{
    identity = ', Jerome' + jeromeNumber;
  }} else if (userName && userName !== 'builder') {{
    identity = ', ' + userName;
  }}

  let greeting = timeGreet + identity + '. ';

  // Streak-aware context
  if (day === 0 && total === 0) {{
    // First ever session
    greeting += 'This is your first session. 7 minutes is all it takes. ';
  }} else if (day === 0) {{
    // Returning after a break
    greeting += 'Welcome back. Every restart is a win. ';
  }} else if (day === 1) {{
    greeting += 'Day 1. The hardest day. You chose to show up. ';
  }} else if (day < 7) {{
    greeting += 'Day ' + day + ' of your streak. Building momentum. ';
  }} else if (day === 7) {{
    greeting += 'Day 7. One full week. You are proving something to yourself. ';
  }} else if (day < 30) {{
    greeting += 'Day ' + day + '. ' + day + ' days of showing up. Keep going. ';
  }} else if (day === 30) {{
    greeting += 'Day 30. One month. You are not the same person who started. ';
  }} else if (day < 100) {{
    greeting += 'Day ' + day + '. You are becoming the person others aspire to be. ';
  }} else {{
    greeting += 'Day ' + day + '. Legendary. ';
  }}

  // Missed days acknowledgment
  if (lastDate) {{
    const daysSince = Math.floor((new Date() - new Date(lastDate)) / 86400000);
    if (daysSince > 1 && daysSince <= 3) {{
      greeting += 'Missed ' + (daysSince - 1) + ' day' + (daysSince > 2 ? 's' : '') + ', but you are here now. That is what matters. ';
    }}
  }}

  greeting += 'Today is ' + sessionType + '. Let us begin.';
  return greeting;
}}

// ── Fetch pattern insights from API for richer context ──
async function fetchPatternInsights() {{
  if (!jeromeNumber) return null;
  try {{
    const resp = await fetch('/api/insights/' + jeromeNumber);
    if (!resp.ok) return null;
    return await resp.json();
  }} catch {{ return null; }}
}}

function buildInsightGreeting(insights) {{
  if (!insights) return buildAdaptiveGreeting();

  const hour = new Date().getHours();
  let timeGreet = hour < 12 ? 'Good morning' : hour < 17 ? 'Good afternoon' : 'Good evening';
  let identity = jeromeNumber ? ', Jerome' + jeromeNumber : (userName && userName !== 'builder' ? ', ' + userName : '');
  let g = timeGreet + identity + '. ';

  // Streak context from server
  const streak = insights.current_streak || 0;
  const status = insights.streak_status || 'new';
  const rate = insights.completion_rate || 0;
  const score = insights.consistency_score || 0;

  if (status === 'new') {{
    g += 'Welcome to Jerome7. 7 minutes. That is all it takes. ';
  }} else if (status === 'returned') {{
    g += 'You came back. That takes more courage than starting. ';
  }} else if (status === 'at_risk') {{
    g += 'Yesterday was a miss. Today you showed up. That is the difference. ';
  }} else if (streak <= 7) {{
    g += 'Day ' + streak + '. Building the foundation. ';
  }} else if (streak <= 30) {{
    g += 'Day ' + streak + '. ' + Math.round(rate) + '% completion rate. You are proving this to yourself. ';
  }} else if (streak <= 100) {{
    g += 'Day ' + streak + '. Consistency score: ' + score + '. You are becoming someone different. ';
  }} else {{
    g += 'Day ' + streak + '. Legendary. ';
  }}

  g += 'Today is ' + sessionType + '. Let us begin.';
  return g;
}}

// ── Session runner ──
async function beginSession() {{
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
    // Fetch real pattern data from server, fall back to local
    const insights = await fetchPatternInsights();
    const greeting = insights ? buildInsightGreeting(insights) : buildAdaptiveGreeting();
    speakCalm(greeting, 1000);
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

  // Fade out
  nameEl.classList.add('fade');

  setTimeout(() => {{
    document.getElementById('phaseLabel').textContent = (phase || sessionType).toUpperCase();
    document.getElementById('phaseLabel').style.color = typeColor;
    nameEl.textContent = b.name.toUpperCase();
    remaining = b.duration_seconds || 60;
    nameEl.classList.remove('fade');
  }}, 300);

  remaining = b.duration_seconds || 60;
  document.getElementById('timer').textContent = formatTime(totalRemaining);

  // Update dots
  blocks.forEach((_, j) => {{
    const dot = document.getElementById('d' + j);
    dot.className = 'dot' + (j < i ? ' done' : j === i ? ' active' : '');
  }});

  // Narrate block (only with browser speech -- AI voice handles its own pacing)
  if (voiceMode !== 'ai' || !aiReady) {{
    speakCalm(b.name + '. ... ' + (b.instruction || ''), 2000);
  }}
}}

function tick() {{
  interval = setInterval(() => {{
    remaining--;
    totalElapsed++;
    totalRemaining--;
    if (totalRemaining < 0) totalRemaining = 0;
    document.getElementById('timer').textContent = formatTime(totalRemaining);
    document.getElementById('progress').style.width = Math.min(100, totalElapsed / TOTAL * 100) + '%';
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

  // Show streak visual
  const day = getStreakDay();
  document.getElementById('streakNumber').textContent = day;

  // Personalize title
  const jLabel = jeromeNumber ? 'Jerome' + jeromeNumber : (userName || 'You');
  document.getElementById('completeTitle').textContent = jLabel + ' showed up.';

  // Show CTA: onboarding if no Jerome#, graph if registered
  const user = JSON.parse(localStorage.getItem('jerome7_user') || '{{}}');
  if (!jeromeNumber) {{
    document.getElementById('postOnboard').classList.remove('hidden');
    if (userName && userName !== 'builder') {{
      document.getElementById('post-ob-name').value = userName;
    }}
  }} else {{
    const graphEl = document.getElementById('wellnessGraph');
    const graphImg = document.getElementById('graphImg');
    graphImg.src = '/graph/' + jeromeNumber + '.svg?t=' + Date.now();
    graphEl.classList.remove('hidden');
  }}

  // Stop AI audio if playing
  if (aiAudio && !aiAudio.paused) {{
    aiAudio.pause();
  }}

  // Adaptive closing narration (browser speech only)
  if (voiceMode !== 'ai' || !aiReady) {{
    let closingNarration = 'Session complete. ... ';
    if (day === 1) closingNarration += 'Day 1 is done. ... The hardest part is over. ';
    else if (day === 7) closingNarration += 'One full week. ... 7 days of showing up. ';
    else if (day === 30) closingNarration += '30 days. ... You built something real. ';
    else closingNarration += 'Day ' + day + '. ';
    closingNarration += '... ' + jLabel + ' showed up. ... ' + closingText;
    speakCalm(closingNarration, 1500);
  }}
}}

function formatTime(s) {{
  if (s < 0) s = 0;
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

async function postSessionRegister() {{
  const name = document.getElementById('post-ob-name').value.trim();
  const email = document.getElementById('post-ob-email').value.trim();
  const hp = document.getElementById('hp-field2')?.value || '';
  const status = document.getElementById('post-ob-status');
  if (!name) {{ document.getElementById('post-ob-name').style.borderColor = '#f85149'; return; }}

  try {{
    const resp = await fetch('/pledge', {{
      method: 'POST',
      headers: {{ 'Content-Type': 'application/json' }},
      body: JSON.stringify({{ name: name, goal: 'post_session', timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC', source: 'web', website: hp, elapsed: Date.now() - pageLoadTime, fp: navigator.language + '|' + screen.width + 'x' + screen.height + '|' + new Date().getTimezoneOffset() }}),
    }});
    const data = await resp.json();
    if (resp.ok) {{
      userName = name;
      jeromeNumber = data.jerome_number || null;
      localStorage.setItem('jerome7_user', JSON.stringify({{
        name: name, jeromeNumber: jeromeNumber, userId: data.user_id, authToken: data.auth_token,
      }}));
      status.textContent = 'You are Jerome' + jeromeNumber + '.';
      status.style.color = '#7ee787';
      // Update completion title
      document.getElementById('completeTitle').textContent = 'Jerome' + jeromeNumber + ' showed up.';
      // Subscribe email if provided
      if (email) {{
        fetch('/subscribe', {{
          method: 'POST',
          headers: {{ 'Content-Type': 'application/json' }},
          body: JSON.stringify({{ email: email }}),
        }}).catch(() => {{}});
      }}
      // Swap to graph view after brief delay
      setTimeout(() => {{
        document.getElementById('postOnboard').classList.add('hidden');
        if (jeromeNumber) {{
          const graphEl = document.getElementById('wellnessGraph');
          const graphImg = document.getElementById('graphImg');
          graphImg.src = '/graph/' + jeromeNumber + '.svg?t=' + Date.now();
          graphEl.classList.remove('hidden');
        }}
      }}, 1500);
    }} else {{
      status.textContent = data.detail || 'Something went wrong.';
      status.style.color = '#f85149';
    }}
  }} catch {{
    status.textContent = 'Network error. Try again.';
    status.style.color = '#f85149';
  }}
}}

function copyGraph() {{
  const num = jeromeNumber || 'YOUR_NUMBER';
  const md = '![Jerome7](https://jerome7.com/graph/' + num + '.svg)';
  copyToClipboard(md).then((ok) => {{
    if (ok) {{
      const toast = document.getElementById('toast');
      toast.textContent = 'copied! paste in your GitHub profile README';
      toast.style.display = 'block';
      setTimeout(() => toast.style.display = 'none', 3000);
    }}
  }});
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

function tweetSession() {{
  const day = getStreakDay();
  const user = JSON.parse(localStorage.getItem('jerome7_user') || '{{}}');
  const jnum = user.jeromeNumber ? 'Jerome' + user.jeromeNumber : '';
  const text = 'Day ' + day + '. 7 minutes of breathing before shipping.' +
    (jnum ? ' I\\'m ' + jnum + '.' : '') +
    ' You are important. Take care of yourself.';
  const url = 'https://jerome7.com/timer';
  window.open('https://x.com/intent/tweet?text=' + encodeURIComponent(text) + '&url=' + encodeURIComponent(url), '_blank');
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
if ('speechSynthesis' in window) {{
  window.speechSynthesis.getVoices();
  // Some browsers load voices async
  window.speechSynthesis.onvoiceschanged = initSpeechVoice;
  initSpeechVoice();
}}
checkOnboarding();
showPersonalGreeting();
initVoiceToggle();
</script>
</body>
</html>"""
    return HTMLResponse(
        content=html,
        headers={"Cache-Control": "public, max-age=300, stale-while-revalidate=3300"},
    )
