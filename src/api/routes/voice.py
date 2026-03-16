"""Voice-guided Jerome7 sessions — 5-phase wellness structure.

Phases: ARRIVAL (30s) → BREATHWORK (90s) → PRACTICE (180s) → INTENTION (60s) → COMMUNITY (60s)
Uses Web Speech API fallback + ElevenLabs AI TTS.
"""

import json
import os
import time
from datetime import datetime, timezone
from html import escape as html_escape

import httpx
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, Response, JSONResponse

from src.api.routes.daily import get_daily, get_daily_wellness

router = APIRouter()

# ── In-memory audio cache (keyed by date string, max 1 entry) ────────────────
_audio_cache: dict[str, bytes] = {}
_wellness_audio_cache: dict[str, bytes] = {}

# ── Simple rate limiter for voice generation ──────────────────────────────────
_voice_rate: dict[str, list] = {}  # ip -> [timestamps]
_VOICE_RATE_LIMIT = 5  # max calls per IP per hour


def _prune_cache(cache: dict, keep_key: str):
    """Remove all entries except today's to prevent memory leak."""
    stale = [k for k in cache if k != keep_key]
    for k in stale:
        del cache[k]


def _prune_rate_limits(rate_dict: dict, max_age: float = 7200):
    cutoff = time.time() - max_age
    to_delete = []
    for ip, timestamps in rate_dict.items():
        rate_dict[ip] = [t for t in timestamps if t > cutoff]
        if not rate_dict[ip]:
            to_delete.append(ip)
    for ip in to_delete:
        del rate_dict[ip]


def _check_voice_rate(ip: str) -> bool:
    """Return True if request is allowed, False if rate-limited."""
    _prune_rate_limits(_voice_rate)
    now = datetime.now(timezone.utc).timestamp()
    hour_ago = now - 3600
    hits = _voice_rate.get(ip, [])
    hits = [t for t in hits if t > hour_ago]
    if len(hits) >= _VOICE_RATE_LIMIT:
        _voice_rate[ip] = hits
        return False
    hits.append(now)
    _voice_rate[ip] = hits
    return True


def _get_api_key():
    return os.getenv("ELEVENLABS_API_KEY", "")

def _get_voice_id():
    return os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")


def _build_narration(blocks: list[dict], closing: str) -> str:
    """Build the 5-phase narration script for TTS.

    Phases:
      ARRIVAL    (0:00-0:30)  — warm welcome, ambient
      BREATHWORK (0:30-2:00)  — box breathing, 4-count cycles
      PRACTICE   (2:00-5:00)  — 7 wellness blocks from daily session
      INTENTION  (5:00-6:00)  — affirmation / what are you shipping
      COMMUNITY  (6:00-7:00)  — streak celebration, see you tomorrow
    """
    lines = []

    # ── ARRIVAL (30s) ────────────────────────────────────────────────────
    lines.append(
        "Welcome to Jerome 7. "
        "Today is your session. "
        "Builders around the world are showing up with you right now. "
        "Take a breath. You're here. That's what matters."
    )
    lines.append("...")

    # ── BREATHWORK (90s) ─────────────────────────────────────────────────
    lines.append(
        "Let's begin with box breathing. "
        "Find a comfortable position. Relax your shoulders."
    )
    # 4 cycles of box breathing (~20s each with pauses)
    for cycle in range(1, 5):
        lines.append(
            f"Cycle {cycle}. "
            "Breathe in... two... three... four. "
            "Hold... two... three... four. "
            "Breathe out... two... three... four. "
            "Hold... two... three... four."
        )
        lines.append("...")
    lines.append("Good. Let that settle.")
    lines.append("...")

    # ── PRACTICE (180s) ──────────────────────────────────────────────────
    lines.append(
        "Time for today's practice. "
        "Seven blocks. Follow along at your own pace."
    )
    for i, b in enumerate(blocks, 1):
        name = b.get("name", f"Block {i}")
        instruction = b.get("instruction", "")
        lines.append(f"Block {i}. {name}. {instruction}.")
        if i < len(blocks):
            lines.append("...")
    lines.append("...")

    # ── INTENTION (60s) ──────────────────────────────────────────────────
    lines.append(
        "Take a moment. "
        "What are you building today? "
        "Hold that intention. "
        "You showed up. That compounds. "
        "Every day you show up, you become harder to stop."
    )
    lines.append("...")

    # ── COMMUNITY (60s) ──────────────────────────────────────────────────
    lines.append(
        "Session complete. "
        "You just showed up with builders across the world. "
        "Your chain continues. "
        "See you tomorrow."
    )
    lines.append(closing)

    return "\n".join(lines)


# ── POST /voice/generate ────────────────────────────────────────────────────

@router.post("/voice/generate")
async def voice_generate(request: Request):
    """Generate ElevenLabs TTS audio for today's session. Cached per day."""
    ip = request.client.host if request.client else "unknown"
    if not _check_voice_rate(ip):
        return JSONResponse(status_code=429, content={"error": "Rate limited. Try again later."})

    api_key = _get_api_key()
    voice_id = _get_voice_id()
    if not api_key:
        return JSONResponse(
            status_code=503,
            content={"error": "ElevenLabs API key not configured. Use browser voice instead."},
        )

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    _prune_cache(_audio_cache, today)

    # Already generated today
    if today in _audio_cache:
        return {"status": "generated", "url": "/voice/audio", "cached": True}

    # Fetch today's session
    session = await get_daily()
    # Handle both dict and Pydantic model responses
    if hasattr(session, "dict"):
        session = session.dict()
    elif hasattr(session, "model_dump"):
        session = session.model_dump()
    blocks = session.get("blocks", [])
    closing = session.get("closing", "You showed up. That is the win.")

    script = _build_narration(blocks, closing)

    # Call ElevenLabs TTS
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg",
    }
    payload = {
        "text": script,
        "model_id": "eleven_turbo_v2_5",
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75,
            "style": 0.0,
            "use_speaker_boost": True,
        },
    }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
            if resp.status_code != 200:
                return JSONResponse(
                    status_code=502,
                    content={"error": f"ElevenLabs API error: {resp.status_code}", "detail": resp.text[:200]},
                )
            _audio_cache[today] = resp.content
    except httpx.TimeoutException:
        return JSONResponse(status_code=504, content={"error": "ElevenLabs API timed out."})
    except httpx.HTTPError as exc:
        return JSONResponse(status_code=502, content={"error": f"HTTP error: {str(exc)}"})

    return {"status": "generated", "url": "/voice/audio", "cached": False}


# ── GET /voice/audio ────────────────────────────────────────────────────────

@router.head("/voice/audio")
async def voice_audio_head():
    """Check if today's audio exists."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if today in _audio_cache:
        return Response(status_code=200, headers={"Content-Type": "audio/mpeg"})
    return Response(status_code=404)


@router.get("/voice/audio")
async def voice_audio():
    """Stream the cached TTS MP3 for today's session."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    audio = _audio_cache.get(today)
    if audio is None:
        return JSONResponse(
            status_code=404,
            content={"error": "No audio for today. POST /voice/generate first."},
        )
    return Response(
        content=audio,
        media_type="audio/mpeg",
        headers={
            "Content-Disposition": f'inline; filename="jerome7-{today}.mp3"',
            "Cache-Control": "public, max-age=86400",
        },
    )


# ── GET /voice — voice session page ────────────────────────────────────────

@router.get("/voice", response_class=HTMLResponse)
async def voice_session():
    """Voice-guided session — 5-phase wellness structure with AI or browser voice."""
    session = await get_daily()
    if hasattr(session, "model_dump"):
        session = session.model_dump()
    elif hasattr(session, "dict"):
        session = session.dict()
    blocks = session.get("blocks", []) if isinstance(session, dict) else []
    title = session.get("session_title", "the seven 7") if isinstance(session, dict) else "the seven 7"

    # Sanitize AI-generated content to prevent XSS
    closing_raw = session.get("closing", "You showed up. That is the win.") if isinstance(session, dict) else "You showed up. That is the win."
    ai_available = "true" if _get_api_key() else "false"

    # Serialize blocks safely using json.dumps
    blocks_raw = blocks if isinstance(blocks, list) else []
    for b in blocks_raw:
        b["name"] = html_escape(b.get("name", ""))
        b["instruction"] = html_escape(b.get("instruction", ""))
    blocks_js = json.dumps(blocks_raw)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Jerome7 — Voice Session</title>
<meta name="robots" content="noindex, nofollow">
<meta name="description" content="Guided 7-minute wellness session with AI voice narration.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700;800&display=swap" rel="stylesheet">
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    background: #0f1419; color: #c9d1d9;
    font-family: 'JetBrains Mono', monospace;
    min-height: 100vh; display: flex; align-items: center; justify-content: center;
  }}
  .container {{ max-width: 560px; width: 100%; padding: 40px 20px; text-align: center; }}

  .nav {{
    display: flex; justify-content: space-between; align-items: center;
    margin-bottom: 60px;
  }}
  .brand {{ font-size: 11px; letter-spacing: 3px; color: #e8713a; text-decoration: none; font-weight: 700; }}
  .nav-links {{ display: flex; gap: 20px; }}
  .nav-links a {{ font-size: 11px; color: #484f58; text-decoration: none; letter-spacing: 1px; }}

  .voice-badge {{
    display: inline-flex; align-items: center; gap: 8px;
    background: #161b22; border: 1px solid #3fb950;
    border-radius: 100px; padding: 8px 20px;
    font-size: 10px; letter-spacing: 3px; color: #3fb950;
    margin-bottom: 24px;
  }}
  .voice-pulse {{
    width: 10px; height: 10px; border-radius: 50%;
    background: #3fb950;
  }}
  .voice-pulse.active {{ animation: pulse 1s infinite; }}
  @keyframes pulse {{
    0%, 100% {{ opacity: 1; transform: scale(1); }}
    50% {{ opacity: 0.4; transform: scale(1.3); }}
  }}

  .title {{ font-size: 28px; font-weight: 800; color: #f0f6fc; margin-bottom: 8px; }}
  .subtitle {{ font-size: 12px; color: #484f58; margin-bottom: 32px; letter-spacing: 1px; }}

  /* ── Phase indicators ─────────────────────────── */
  .phase-bar {{
    display: flex; justify-content: center; gap: 4px;
    margin-bottom: 32px; flex-wrap: wrap;
  }}
  .phase-pill {{
    font-size: 9px; letter-spacing: 1.5px; font-weight: 700;
    padding: 5px 12px; border-radius: 100px;
    background: #161b22; border: 1px solid #21262d;
    color: #484f58; transition: all 0.4s;
  }}
  .phase-pill.active {{
    border-color: var(--phase-color);
    color: var(--phase-color);
    background: color-mix(in srgb, var(--phase-color) 10%, #161b22);
  }}
  .phase-pill.done {{
    border-color: #30363d;
    color: #30363d;
    background: #161b22;
  }}
  .phase-pill[data-phase="arrival"]    {{ --phase-color: #79c0ff; }}
  .phase-pill[data-phase="breathwork"] {{ --phase-color: #4ecdc4; }}
  .phase-pill[data-phase="practice"]   {{ --phase-color: #e8713a; }}
  .phase-pill[data-phase="intention"]  {{ --phase-color: #b392f0; }}
  .phase-pill[data-phase="community"]  {{ --phase-color: #7ee787; }}

  /* ── Voice toggle ─────────────────────────── */
  .voice-toggle {{
    display: inline-flex; background: #161b22; border: 1px solid #21262d;
    border-radius: 100px; margin-bottom: 24px; overflow: hidden;
  }}
  .voice-toggle button {{
    padding: 8px 20px; font-size: 10px; letter-spacing: 2px;
    background: none; border: none; color: #484f58;
    cursor: pointer; font-family: inherit; font-weight: 600;
    transition: all 0.2s;
  }}
  .voice-toggle button.active {{
    background: #e8713a; color: #fff;
  }}
  .voice-toggle button:disabled {{
    opacity: 0.3; cursor: not-allowed;
  }}

  /* ── AI Audio player ──────────────────────── */
  .ai-player {{
    background: #161b22; border: 1px solid #21262d;
    border-radius: 12px; padding: 16px 20px;
    margin-bottom: 32px; display: none;
  }}
  .ai-player.show {{ display: block; }}

  .ai-player-row {{
    display: flex; align-items: center; gap: 12px;
  }}
  .ai-play-btn {{
    width: 40px; height: 40px; border-radius: 50%;
    background: #e8713a; border: none; cursor: pointer;
    display: flex; align-items: center; justify-content: center;
    flex-shrink: 0; transition: background 0.2s;
  }}
  .ai-play-btn:hover {{ background: #c45f2e; }}
  .ai-play-btn svg {{ fill: #fff; width: 16px; height: 16px; }}

  .ai-progress-wrap {{
    flex: 1; display: flex; flex-direction: column; gap: 4px;
  }}
  .ai-progress-bar {{
    width: 100%; height: 6px; background: #21262d;
    border-radius: 3px; cursor: pointer; position: relative; overflow: hidden;
  }}
  .ai-progress-fill {{
    height: 100%; background: #e8713a; border-radius: 3px;
    width: 0%; transition: width 0.25s linear;
  }}
  .ai-time {{
    display: flex; justify-content: space-between;
    font-size: 9px; color: #484f58; letter-spacing: 1px;
  }}
  .ai-status {{
    font-size: 10px; color: #484f58; letter-spacing: 1px;
    margin-top: 8px;
  }}

  .generate-btn {{
    display: inline-block; padding: 10px 28px;
    background: #e8713a; color: #fff; font-weight: 700;
    font-size: 11px; letter-spacing: 2px;
    border: none; border-radius: 6px; cursor: pointer;
    font-family: inherit; margin-bottom: 16px;
  }}
  .generate-btn:hover {{ background: #c45f2e; }}
  .generate-btn:disabled {{ background: #21262d; color: #484f58; cursor: default; }}

  /* ── Active session content ────────────────── */
  .phase-label {{
    font-size: 10px; letter-spacing: 3px; margin-bottom: 8px;
    transition: color 0.4s;
  }}
  .block-name {{
    font-size: 36px; font-weight: 800; color: #f0f6fc; margin-bottom: 12px;
    line-height: 1.2;
  }}
  .block-instruction {{
    font-size: 14px; color: #8b949e; margin-bottom: 32px; line-height: 1.6;
    max-width: 420px; margin-left: auto; margin-right: auto;
  }}

  /* Timer */
  .timer {{
    font-size: 72px; font-weight: 800; color: #f0f6fc;
    letter-spacing: -2px; margin-bottom: 8px;
    font-variant-numeric: tabular-nums;
  }}
  .timer-label {{ font-size: 10px; color: #484f58; letter-spacing: 2px; margin-bottom: 32px; }}

  /* Session-wide progress */
  .session-progress {{
    width: 100%; height: 4px; background: #21262d;
    border-radius: 2px; margin-bottom: 12px; overflow: hidden;
    position: relative;
  }}
  .session-progress-fill {{
    height: 100%; border-radius: 2px;
    transition: width 1s linear, background-color 0.4s;
    width: 0%;
  }}

  /* Phase progress segments */
  .phase-segments {{
    display: flex; gap: 3px; margin-bottom: 48px;
  }}
  .phase-seg {{
    height: 3px; border-radius: 2px; background: #21262d;
    transition: background 0.4s;
  }}
  .phase-seg.done {{ background: #30363d; }}
  .phase-seg.active {{ animation: pulse 1.5s infinite; }}

  /* Start button */
  .start-btn {{
    display: inline-block; padding: 16px 48px;
    background: #e8713a; color: #fff; font-weight: 700;
    font-size: 13px; letter-spacing: 2px;
    border: none; border-radius: 6px; cursor: pointer;
    font-family: inherit;
  }}
  .start-btn:hover {{ background: #c45f2e; }}
  .start-btn:disabled {{ background: #21262d; color: #484f58; cursor: default; }}

  .note {{ font-size: 10px; color: #30363d; margin-top: 16px; letter-spacing: 1px; }}

  /* Complete state */
  .complete {{ display: none; }}
  .complete.show {{ display: block; }}
  .complete-check {{ font-size: 64px; margin-bottom: 16px; color: #7ee787; }}
  .complete-text {{ font-size: 14px; color: #8b949e; line-height: 1.6; }}

  .hidden {{ display: none; }}

  @media (max-width: 480px) {{
    .timer {{ font-size: 56px; }}
    .block-name {{ font-size: 24px; }}
    .phase-pill {{ font-size: 8px; padding: 4px 8px; }}
    .phase-bar {{ gap: 3px; }}
  }}
</style>
</head>
<body>
<div class="container">

  <nav class="nav">
    <a href="/" class="brand">JEROME7</a>
    <div class="nav-links">
      <a href="/timer">TIMER</a>
      <a href="/leaderboard">BOARD</a>
    </div>
  </nav>

  <div class="voice-badge">
    <div class="voice-pulse" id="voicePulse"></div>
    VOICE MODE
  </div>

  <div id="preStart">
    <div class="title">{html_escape(title).upper()}</div>
    <div class="subtitle">GUIDED SESSION · 5 PHASES · 7 MINUTES</div>

    <!-- Phase overview -->
    <div class="phase-bar" id="phaseBarPre">
      <div class="phase-pill" data-phase="arrival">ARRIVAL</div>
      <div class="phase-pill" data-phase="breathwork">BREATHWORK</div>
      <div class="phase-pill" data-phase="practice">PRACTICE</div>
      <div class="phase-pill" data-phase="intention">INTENTION</div>
      <div class="phase-pill" data-phase="community">COMMUNITY</div>
    </div>

    <!-- Voice toggle -->
    <div class="voice-toggle" id="voiceToggle">
      <button id="btnAiVoice" class="active" onclick="selectVoiceMode('ai')">AI VOICE</button>
      <button id="btnBrowserVoice" onclick="selectVoiceMode('browser')">BROWSER VOICE</button>
    </div>

    <!-- AI Audio player -->
    <div class="ai-player" id="aiPlayer">
      <div id="aiGenerate" style="text-align:center">
        <button class="generate-btn" id="generateBtn" onclick="generateAudio()">GENERATE AI VOICE</button>
        <div class="ai-status" id="aiGenerateStatus"></div>
      </div>
      <div id="aiPlayback" style="display:none">
        <div class="ai-player-row">
          <button class="ai-play-btn" id="aiPlayBtn" onclick="toggleAiPlayback()">
            <svg id="aiPlayIcon" viewBox="0 0 24 24"><polygon points="6,4 20,12 6,20"/></svg>
          </button>
          <div class="ai-progress-wrap">
            <div class="ai-progress-bar" id="aiProgressBar" onclick="seekAudio(event)">
              <div class="ai-progress-fill" id="aiProgressFill"></div>
            </div>
            <div class="ai-time">
              <span id="aiTimeCurrent">0:00</span>
              <span id="aiTimeDuration">0:00</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <button class="start-btn" id="startBtn" onclick="startSession()">BEGIN SESSION</button>
    <div class="note" id="voiceNote">AI-powered narration by ElevenLabs.</div>
  </div>

  <div id="activeSession" class="hidden">
    <!-- Phase bar during session -->
    <div class="phase-bar" id="phaseBarActive">
      <div class="phase-pill" data-phase="arrival">ARRIVAL</div>
      <div class="phase-pill" data-phase="breathwork">BREATHWORK</div>
      <div class="phase-pill" data-phase="practice">PRACTICE</div>
      <div class="phase-pill" data-phase="intention">INTENTION</div>
      <div class="phase-pill" data-phase="community">COMMUNITY</div>
    </div>

    <div class="phase-label" id="phaseLabel">ARRIVAL</div>
    <div class="block-name" id="blockName">—</div>
    <div class="block-instruction" id="blockInstruction">—</div>
    <div class="timer" id="timer">0:30</div>
    <div class="timer-label">REMAINING</div>

    <!-- Full session progress bar -->
    <div class="session-progress">
      <div class="session-progress-fill" id="sessionProgressFill"></div>
    </div>

    <!-- Phase segment indicators -->
    <div class="phase-segments" id="phaseSegments">
      <div class="phase-seg" data-phase="arrival"    style="flex:30"></div>
      <div class="phase-seg" data-phase="breathwork" style="flex:90"></div>
      <div class="phase-seg" data-phase="practice"   style="flex:180"></div>
      <div class="phase-seg" data-phase="intention"  style="flex:60"></div>
      <div class="phase-seg" data-phase="community"  style="flex:60"></div>
    </div>
  </div>

  <div class="complete" id="complete">
    <div class="complete-check">&#10003;</div>
    <div class="title">SESSION COMPLETE</div>
    <div class="complete-text" id="closingText"></div>
    <div class="note" style="margin-top:24px">
      <a href="/timer" style="color:#e8713a;text-decoration:none">TIMER</a> &middot;
      <a href="/leaderboard" style="color:#484f58;text-decoration:none">LEADERBOARD</a> &middot;
      <a href="/voice" style="color:#484f58;text-decoration:none">REPLAY</a>
    </div>
  </div>

</div>

<script>
  // ── Data from server ────────────────────────────────────────────────
  const wellnessBlocks ={blocks_js};
  const closing = {json.dumps(closing_raw)};
  const aiAvailable = {ai_available};

  // ── Phase colors ────────────────────────────────────────────────────
  const PHASE_COLORS = {{
    arrival:    '#79c0ff',
    breathwork: '#4ecdc4',
    practice:   '#e8713a',
    intention:  '#b392f0',
    community:  '#7ee787',
  }};

  // ── 5-phase session structure ───────────────────────────────────────
  // Each phase is an array of "steps" with name, instruction, duration.
  function buildPhases() {{
    const phases = [
      {{
        id: 'arrival', label: 'ARRIVAL', totalDuration: 30,
        steps: [{{
          name: 'Welcome',
          instruction: 'Builders around the world are showing up with you right now. Take a breath. You are here. That is what matters.',
          duration: 30,
        }}],
      }},
      {{
        id: 'breathwork', label: 'BREATHWORK', totalDuration: 90,
        steps: [
          {{ name: 'Box Breathing', instruction: 'Breathe in for 4... hold for 4... breathe out for 4... hold for 4. Repeat with me.', duration: 90 }},
        ],
      }},
      {{
        id: 'practice', label: 'PRACTICE', totalDuration: 180,
        steps: wellnessBlocks.map((b, i) => ({{
          name: b.name,
          instruction: b.instruction,
          duration: Math.floor(180 / wellnessBlocks.length),
        }})),
      }},
      {{
        id: 'intention', label: 'INTENTION', totalDuration: 60,
        steps: [{{
          name: 'Set Your Intention',
          instruction: 'What are you building today? Hold that intention. You showed up. That compounds.',
          duration: 60,
        }}],
      }},
      {{
        id: 'community', label: 'COMMUNITY', totalDuration: 60,
        steps: [{{
          name: 'Chain Unbroken',
          instruction: 'You just showed up with builders across the world. Your chain continues. See you tomorrow.',
          duration: 60,
        }}],
      }},
    ];

    // Ensure movement step durations add up to exactly 180
    const mv = phases[2];
    const perStep = Math.floor(180 / mv.steps.length);
    let remainder = 180 - perStep * mv.steps.length;
    mv.steps.forEach((s, i) => {{
      s.duration = perStep + (i < remainder ? 1 : 0);
    }});

    return phases;
  }}

  const SESSION_PHASES = buildPhases();
  const TOTAL_DURATION = 420; // 7 minutes

  // ── State ───────────────────────────────────────────────────────────
  let voiceMode = aiAvailable ? 'ai' : 'browser';
  let currentPhaseIdx = 0;
  let currentStepIdx = 0;
  let timerInterval = null;
  let sessionStartTime = null;
  let aiAudio = null;
  let aiAudioReady = false;
  let aiSessionActive = false;

  // ── Browser speech narration scripts per phase ──────────────────────
  const PHASE_NARRATION = {{
    arrival: [
      'Welcome to Jerome 7.',
      'Today is your session.',
      'Builders around the world are showing up with you right now.',
      'Take a breath. You are here. That is what matters.',
    ],
    breathwork: [
      'Let us begin with box breathing. Find a comfortable position.',
      'Breathe in for four. Hold for four. Breathe out for four. Hold for four.',
      'Again. Breathe in... hold... breathe out... hold.',
      'One more cycle. In... hold... out... hold.',
      'Good. Let that settle.',
    ],
    practice_intro: 'Time for today\\'s practice. Follow along at your own pace.',
    intention: [
      'Take a moment.',
      'What are you building today?',
      'Hold that intention. You showed up. That compounds.',
    ],
    community: [
      'Session complete.',
      'You just showed up with builders across the world.',
      'Your chain continues. See you tomorrow.',
    ],
  }};

  // ── Initialization ──────────────────────────────────────────────────
  function init() {{
    if (!aiAvailable) {{
      document.getElementById('btnAiVoice').disabled = true;
      document.getElementById('btnAiVoice').classList.remove('active');
      document.getElementById('btnBrowserVoice').classList.add('active');
      voiceMode = 'browser';
      document.getElementById('voiceNote').textContent =
        'Uses your browser\\'s speech synthesis. No data leaves your device.';
    }} else {{
      checkExistingAudio();
    }}
    updateToggleUI();
  }}

  function selectVoiceMode(mode) {{
    if (mode === 'ai' && !aiAvailable) return;
    voiceMode = mode;
    updateToggleUI();
  }}

  function updateToggleUI() {{
    const btnAi = document.getElementById('btnAiVoice');
    const btnBrowser = document.getElementById('btnBrowserVoice');
    const player = document.getElementById('aiPlayer');
    const note = document.getElementById('voiceNote');

    btnAi.classList.toggle('active', voiceMode === 'ai');
    btnBrowser.classList.toggle('active', voiceMode === 'browser');

    if (voiceMode === 'ai' && aiAvailable) {{
      player.classList.add('show');
      note.textContent = 'AI-powered narration by ElevenLabs.';
    }} else {{
      player.classList.remove('show');
      note.textContent = 'Uses your browser\\'s speech synthesis. No data leaves your device.';
    }}
  }}

  // ── AI Audio ────────────────────────────────────────────────────────
  async function checkExistingAudio() {{
    try {{
      const resp = await fetch('/voice/audio', {{ method: 'HEAD' }});
      if (resp.ok) loadAudioPlayer();
    }} catch(e) {{ /* no audio yet */ }}
  }}

  async function generateAudio() {{
    const btn = document.getElementById('generateBtn');
    const status = document.getElementById('aiGenerateStatus');
    btn.disabled = true;
    btn.textContent = 'GENERATING...';
    status.textContent = 'Calling ElevenLabs TTS API...';

    try {{
      const resp = await fetch('/voice/generate', {{ method: 'POST' }});
      const data = await resp.json();
      if (!resp.ok) {{
        status.textContent = data.error || 'Generation failed.';
        btn.disabled = false;
        btn.textContent = 'RETRY';
        return;
      }}
      status.textContent = 'Audio ready!';
      loadAudioPlayer();
    }} catch(e) {{
      status.textContent = 'Network error. Try again.';
      btn.disabled = false;
      btn.textContent = 'RETRY';
    }}
  }}

  function loadAudioPlayer() {{
    aiAudio = new Audio('/voice/audio');
    aiAudio.preload = 'auto';

    aiAudio.addEventListener('loadedmetadata', () => {{
      document.getElementById('aiTimeDuration').textContent = fmtAudioTime(aiAudio.duration);
      aiAudioReady = true;
    }});

    aiAudio.addEventListener('timeupdate', () => {{
      if (!aiAudio.duration) return;
      const pct = (aiAudio.currentTime / aiAudio.duration) * 100;
      document.getElementById('aiProgressFill').style.width = pct + '%';
      document.getElementById('aiTimeCurrent').textContent = fmtAudioTime(aiAudio.currentTime);
    }});

    aiAudio.addEventListener('ended', () => {{
      document.getElementById('aiPlayIcon').innerHTML = '<polygon points="6,4 20,12 6,20"/>';
    }});

    document.getElementById('aiGenerate').style.display = 'none';
    document.getElementById('aiPlayback').style.display = 'block';
  }}

  function toggleAiPlayback() {{
    if (!aiAudio || !aiAudioReady) return;
    if (aiAudio.paused) {{
      aiAudio.play();
      document.getElementById('aiPlayIcon').innerHTML =
        '<rect x="6" y="4" width="4" height="16"/><rect x="14" y="4" width="4" height="16"/>';
    }} else {{
      aiAudio.pause();
      document.getElementById('aiPlayIcon').innerHTML = '<polygon points="6,4 20,12 6,20"/>';
    }}
  }}

  function seekAudio(e) {{
    if (!aiAudio || !aiAudio.duration) return;
    const bar = document.getElementById('aiProgressBar');
    const rect = bar.getBoundingClientRect();
    const pct = (e.clientX - rect.left) / rect.width;
    aiAudio.currentTime = pct * aiAudio.duration;
  }}

  function fmtAudioTime(s) {{
    if (!s || isNaN(s)) return '0:00';
    const m = Math.floor(s / 60);
    const sec = Math.floor(s % 60);
    return m + ':' + sec.toString().padStart(2, '0');
  }}

  // ── Browser speech ──────────────────────────────────────────────────
  function speak(text) {{
    if (!('speechSynthesis' in window)) return;
    window.speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(text);
    u.rate = 0.85; u.pitch = 1.0; u.volume = 1.0;
    const voices = window.speechSynthesis.getVoices();
    const preferred = voices.find(v =>
      v.name.includes('Samantha') || v.name.includes('Daniel') || v.name.includes('Google'));
    if (preferred) u.voice = preferred;
    window.speechSynthesis.speak(u);
  }}

  function speakSequence(texts, delay) {{
    // Speak an array of texts with a delay between each
    let d = 0;
    texts.forEach(t => {{
      setTimeout(() => speak(t), d);
      d += delay;
    }});
  }}

  // ── Phase UI helpers ────────────────────────────────────────────────
  function updatePhasePills() {{
    const pills = document.querySelectorAll('#phaseBarActive .phase-pill');
    const segments = document.querySelectorAll('#phaseSegments .phase-seg');
    pills.forEach((pill, i) => {{
      pill.classList.remove('active', 'done');
      if (i < currentPhaseIdx) pill.classList.add('done');
      else if (i === currentPhaseIdx) pill.classList.add('active');
    }});
    segments.forEach((seg, i) => {{
      seg.classList.remove('active', 'done');
      seg.style.background = '#21262d';
      if (i < currentPhaseIdx) {{
        seg.classList.add('done');
        seg.style.background = '#30363d';
      }} else if (i === currentPhaseIdx) {{
        seg.classList.add('active');
        seg.style.background = PHASE_COLORS[SESSION_PHASES[i].id];
      }}
    }});
  }}

  function showPhaseStep(phaseIdx, stepIdx) {{
    const phase = SESSION_PHASES[phaseIdx];
    const step = phase.steps[stepIdx];
    const color = PHASE_COLORS[phase.id];

    document.getElementById('phaseLabel').textContent = phase.label;
    document.getElementById('phaseLabel').style.color = color;
    document.getElementById('blockName').textContent = step.name.toUpperCase();
    document.getElementById('blockInstruction').textContent = step.instruction;
    document.getElementById('sessionProgressFill').style.backgroundColor = color;
    updatePhasePills();
  }}

  function updateSessionProgress() {{
    // Calculate total elapsed seconds across all completed phases + current
    let elapsed = 0;
    for (let p = 0; p < currentPhaseIdx; p++) {{
      elapsed += SESSION_PHASES[p].totalDuration;
    }}
    // Add elapsed within current phase
    const phase = SESSION_PHASES[currentPhaseIdx];
    for (let s = 0; s < currentStepIdx; s++) {{
      elapsed += phase.steps[s].duration;
    }}
    // Current step: its duration minus what the timer shows
    const timerEl = document.getElementById('timer');
    const parts = timerEl.textContent.split(':');
    const remaining = parseInt(parts[0]) * 60 + parseInt(parts[1]);
    const stepDuration = phase.steps[currentStepIdx] ? phase.steps[currentStepIdx].duration : 0;
    elapsed += stepDuration - remaining;

    const pct = Math.min(100, (elapsed / TOTAL_DURATION) * 100);
    document.getElementById('sessionProgressFill').style.width = pct + '%';
  }}

  function formatTime(s) {{
    const m = Math.floor(s / 60);
    const sec = s % 60;
    return m + ':' + sec.toString().padStart(2, '0');
  }}

  // ── Timer ───────────────────────────────────────────────────────────
  function runTimer(seconds, onDone) {{
    let remaining = seconds;
    document.getElementById('timer').textContent = formatTime(remaining);
    updateSessionProgress();

    timerInterval = setInterval(() => {{
      remaining--;
      document.getElementById('timer').textContent = formatTime(remaining);
      updateSessionProgress();

      if (remaining <= 0) {{
        clearInterval(timerInterval);
        onDone();
      }}
    }}, 1000);
  }}

  // ── Phase runner ────────────────────────────────────────────────────
  function runStep() {{
    if (currentPhaseIdx >= SESSION_PHASES.length) {{
      finishSession();
      return;
    }}

    const phase = SESSION_PHASES[currentPhaseIdx];
    if (currentStepIdx >= phase.steps.length) {{
      // Move to next phase
      currentPhaseIdx++;
      currentStepIdx = 0;
      runStep();
      return;
    }}

    const step = phase.steps[currentStepIdx];
    showPhaseStep(currentPhaseIdx, currentStepIdx);

    // Browser voice narration for each phase
    if (voiceMode === 'browser') {{
      narratePhaseStep(phase.id, currentStepIdx);
    }}

    runTimer(step.duration, () => {{
      currentStepIdx++;
      runStep();
    }});
  }}

  function narratePhaseStep(phaseId, stepIdx) {{
    if (phaseId === 'arrival' && stepIdx === 0) {{
      speakSequence(PHASE_NARRATION.arrival, 4000);
    }} else if (phaseId === 'breathwork' && stepIdx === 0) {{
      speakSequence(PHASE_NARRATION.breathwork, 8000);
    }} else if (phaseId === 'practice') {{
      if (stepIdx === 0) speak(PHASE_NARRATION.practice_intro);
      const block = wellnessBlocks[stepIdx];
      if (block) {{
        setTimeout(() => {{
          speak('Block ' + (stepIdx + 1) + '. ' + block.name + '. ' + block.instruction + '.');
        }}, stepIdx === 0 ? 3000 : 500);
      }}
    }} else if (phaseId === 'intention' && stepIdx === 0) {{
      speakSequence(PHASE_NARRATION.intention, 5000);
    }} else if (phaseId === 'community' && stepIdx === 0) {{
      speakSequence(PHASE_NARRATION.community, 4000);
    }}
  }}

  // ── AI mode: play narration alongside the session ──────────────────
  function startAiNarration() {{
    if (!aiAudio || !aiAudioReady) return;
    aiSessionActive = true;
    aiAudio.currentTime = 0;
    aiAudio.play();
  }}

  // ── Finish ──────────────────────────────────────────────────────────
  function finishSession() {{
    document.getElementById('activeSession').classList.add('hidden');
    document.getElementById('complete').classList.add('show');
    document.getElementById('closingText').textContent = closing;
    document.getElementById('voicePulse').classList.remove('active');
    aiSessionActive = false;

    if (voiceMode === 'browser') {{
      speak('Session complete. ' + closing);
    }}
  }}

  // ── Start session ───────────────────────────────────────────────────
  function startSession() {{
    document.getElementById('preStart').classList.add('hidden');
    document.getElementById('activeSession').classList.remove('hidden');
    document.getElementById('voicePulse').classList.add('active');
    sessionStartTime = Date.now();
    currentPhaseIdx = 0;
    currentStepIdx = 0;

    if (voiceMode === 'ai' && aiAudio && aiAudioReady) {{
      startAiNarration();
    }}

    runStep();
  }}

  // ── Preload ─────────────────────────────────────────────────────────
  if ('speechSynthesis' in window) {{
    window.speechSynthesis.getVoices();
  }}
  init();
</script>
</body>
</html>"""

    return HTMLResponse(content=html)


# ── Wellness audio generation ──────────────────────────────────────────────

def _build_wellness_narration(blocks: list[dict], session_type: str, closing: str) -> str:
    """Build narration script for wellness sessions (breathwork/meditation/reflection/preparation)."""
    lines = []

    # Opening
    lines.append(
        "Welcome to Jerome 7. "
        f"Today is a {session_type} session. "
        "Builders around the world are with you right now. "
        "Find a comfortable position. Close your eyes if that feels right."
    )
    lines.append("...")

    # Walk through each block
    for i, b in enumerate(blocks, 1):
        name = b.get("name", f"Block {i}")
        instruction = b.get("instruction", "")
        lines.append(f"{name}. {instruction}")
        lines.append("...")

    # Closing
    lines.append(closing)
    return "\n".join(lines)


@router.post("/voice/wellness/generate")
async def voice_wellness_generate(request: Request):
    """Generate ElevenLabs TTS audio for today's wellness session. Cached per day."""
    ip = request.client.host if request.client else "unknown"
    if not _check_voice_rate(ip):
        return JSONResponse(status_code=429, content={"error": "Rate limited. Try again later."})

    api_key = _get_api_key()
    voice_id = _get_voice_id()
    if not api_key:
        return JSONResponse(
            status_code=503,
            content={"error": "ElevenLabs API key not configured."},
        )

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    _prune_cache(_wellness_audio_cache, today)
    if today in _wellness_audio_cache:
        return {"status": "generated", "url": "/voice/wellness/audio", "cached": True}

    session = await get_daily_wellness()
    if hasattr(session, "model_dump"):
        session = session.model_dump()
    elif hasattr(session, "dict"):
        session = session.dict()

    blocks = session.get("blocks", [])
    session_type = session.get("session_type", "breathwork")
    closing = session.get("closing", "You showed up. That's the win.")

    script = _build_wellness_narration(blocks, session_type, closing)

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg",
    }
    payload = {
        "text": script,
        "model_id": "eleven_turbo_v2_5",
        "voice_settings": {
            "stability": 0.6,
            "similarity_boost": 0.8,
            "style": 0.0,
            "use_speaker_boost": True,
        },
    }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
            if resp.status_code != 200:
                return JSONResponse(
                    status_code=502,
                    content={"error": f"ElevenLabs API error: {resp.status_code}"},
                )
            _wellness_audio_cache[today] = resp.content
    except httpx.TimeoutException:
        return JSONResponse(status_code=504, content={"error": "ElevenLabs API timed out."})
    except httpx.HTTPError as exc:
        return JSONResponse(status_code=502, content={"error": f"HTTP error: {str(exc)}"})

    return {"status": "generated", "url": "/voice/wellness/audio", "cached": False}


@router.get("/voice/wellness/audio")
async def voice_wellness_audio():
    """Stream the cached wellness TTS MP3 for today's session."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    audio = _wellness_audio_cache.get(today)
    if audio is None:
        return JSONResponse(
            status_code=404,
            content={"error": "No wellness audio for today. POST /voice/wellness/generate first."},
        )
    return Response(
        content=audio,
        media_type="audio/mpeg",
        headers={
            "Content-Disposition": f'inline; filename="jerome7-wellness-{today}.mp3"',
            "Cache-Control": "public, max-age=86400",
        },
    )
