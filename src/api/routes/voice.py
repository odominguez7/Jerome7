"""Voice-guided Jerome7 sessions — Web Speech API fallback + ElevenLabs AI TTS."""

import os
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter
from fastapi.responses import HTMLResponse, Response, JSONResponse

from src.api.routes.daily import get_daily

router = APIRouter()

# ── In-memory audio cache (keyed by date string) ────────────────────────────
_audio_cache: dict[str, bytes] = {}

def _get_api_key():
    return os.getenv("ELEVENLABS_API_KEY", "")

def _get_voice_id():
    return os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")


def _build_narration(blocks: list[dict], closing: str) -> str:
    """Turn session blocks into a narration script for TTS."""
    lines = [
        "Welcome to Jerome 7.",
        "Today's session. 7 blocks. 60 seconds each.",
        "Let's go.",
    ]
    for i, b in enumerate(blocks, 1):
        name = b.get("name", f"Block {i}")
        instruction = b.get("instruction", "")
        lines.append(f"Block {i}: {name}. {instruction}. Starting now.")
        # Add a brief pause marker between blocks (period + ellipsis)
        if i < len(blocks):
            lines.append("...")
    lines.append("Session complete. You showed up. 7 minutes. Chain unbroken.")
    lines.append(closing)
    return "\n".join(lines)


# ── POST /voice/generate ────────────────────────────────────────────────────

@router.post("/voice/generate")
async def voice_generate():
    """Generate ElevenLabs TTS audio for today's session. Cached per day."""
    api_key = _get_api_key()
    voice_id = _get_voice_id()
    if not api_key:
        return JSONResponse(
            status_code=503,
            content={"error": "ElevenLabs API key not configured. Use browser voice instead."},
        )

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

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
    """Voice-guided session — AI voice (ElevenLabs) or browser speech fallback."""
    session = await get_daily()
    blocks = session.get("blocks", [])
    title = session.get("session_title", "the seven 7")

    ai_available = "true" if ELEVENLABS_API_KEY else "false"

    # Serialize blocks to JS
    blocks_js = "[\n"
    for b in blocks:
        name = b.get("name", "").replace("'", "\\'")
        instruction = b.get("instruction", "").replace("'", "\\'")
        phase = b.get("phase", "build").replace("'", "\\'")
        duration = b.get("duration_seconds", 60)
        blocks_js += f"    {{name:'{name}',instruction:'{instruction}',phase:'{phase}',duration:{duration}}},\n"
    blocks_js += "  ]"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Jerome7 — Voice Session</title>
<meta name="description" content="Hands-free 7-minute session with AI voice narration.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700;800&display=swap" rel="stylesheet">
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    background: #0f1419; color: #c9d1d9;
    font-family: 'JetBrains Mono', monospace;
    min-height: 100vh; display: flex; align-items: center; justify-content: center;
  }}
  .container {{ max-width: 520px; width: 100%; padding: 40px 20px; text-align: center; }}

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
  .subtitle {{ font-size: 12px; color: #484f58; margin-bottom: 48px; letter-spacing: 1px; }}

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

  /* ── Current block ────────────────────────── */
  .block-phase {{
    font-size: 10px; letter-spacing: 3px; color: #e8713a; margin-bottom: 8px;
  }}
  .block-name {{
    font-size: 36px; font-weight: 800; color: #f0f6fc; margin-bottom: 12px;
    line-height: 1.2;
  }}
  .block-instruction {{
    font-size: 14px; color: #8b949e; margin-bottom: 32px; line-height: 1.6;
  }}

  /* Timer */
  .timer {{
    font-size: 72px; font-weight: 800; color: #f0f6fc;
    letter-spacing: -2px; margin-bottom: 8px;
    font-variant-numeric: tabular-nums;
  }}
  .timer-label {{ font-size: 10px; color: #484f58; letter-spacing: 2px; margin-bottom: 32px; }}

  /* Progress */
  .progress-bar {{
    width: 100%; height: 4px; background: #21262d;
    border-radius: 2px; margin-bottom: 24px; overflow: hidden;
  }}
  .progress-fill {{
    height: 100%; background: #e8713a; border-radius: 2px;
    transition: width 1s linear;
  }}
  .block-dots {{
    display: flex; justify-content: center; gap: 8px; margin-bottom: 48px;
  }}
  .dot {{
    width: 10px; height: 10px; border-radius: 50%;
    background: #21262d; transition: background 0.3s;
  }}
  .dot.done {{ background: #3fb950; }}
  .dot.active {{ background: #e8713a; animation: pulse 1s infinite; }}

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
  .complete-check {{ font-size: 64px; margin-bottom: 16px; }}
  .complete-text {{ font-size: 14px; color: #8b949e; line-height: 1.6; }}

  .hidden {{ display: none; }}

  @media (max-width: 480px) {{
    .timer {{ font-size: 56px; }}
    .block-name {{ font-size: 28px; }}
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
    <div class="title">{title.upper()}</div>
    <div class="subtitle">HANDS-FREE · AI NARRATION OR BROWSER VOICE</div>

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

    <button class="start-btn" id="startBtn" onclick="startSession()">START VOICE SESSION</button>
    <div class="note" id="voiceNote">AI-powered narration by ElevenLabs. Silky smooth.</div>
  </div>

  <div id="activeSession" class="hidden">
    <div class="block-phase" id="blockPhase">PRIME</div>
    <div class="block-name" id="blockName">—</div>
    <div class="block-instruction" id="blockInstruction">—</div>
    <div class="timer" id="timer">1:00</div>
    <div class="timer-label">REMAINING</div>
    <div class="progress-bar"><div class="progress-fill" id="progressFill"></div></div>
    <div class="block-dots" id="blockDots"></div>
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
  const blocks = {blocks_js};
  const closing = '{session.get("closing", "You showed up. That is the win.").replace(chr(39), chr(92)+chr(39))}';
  const aiAvailable = {ai_available};

  let voiceMode = aiAvailable ? 'ai' : 'browser';  // 'ai' or 'browser'
  let currentBlock = 0;
  let timerInterval = null;
  let aiAudio = null;
  let aiAudioReady = false;
  let aiSessionActive = false;

  // ── Initialization ──────────────────────────────────────────────────
  function init() {{
    if (!aiAvailable) {{
      // No API key — disable AI voice
      document.getElementById('btnAiVoice').disabled = true;
      document.getElementById('btnAiVoice').classList.remove('active');
      document.getElementById('btnBrowserVoice').classList.add('active');
      voiceMode = 'browser';
      document.getElementById('voiceNote').textContent =
        'Uses your browser\\'s speech synthesis. No data leaves your device.';
    }} else {{
      // Try to load existing audio
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
      if (resp.ok) {{
        loadAudioPlayer();
      }}
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

      // Sync blocks with audio playback if session is active
      if (aiSessionActive) syncBlocksWithAudio();
    }});

    aiAudio.addEventListener('ended', () => {{
      document.getElementById('aiPlayIcon').innerHTML = '<polygon points="6,4 20,12 6,20"/>';
    }});

    // Show playback controls, hide generate button
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

  // ── Block sync (AI mode) ────────────────────────────────────────────
  // Estimate block timing: the narration has an intro (~8s), then each
  // block is roughly (duration / total_duration) of the audio length.
  // We approximate evenly since each block is ~60s in the session.
  function syncBlocksWithAudio() {{
    if (!aiAudio || !aiAudio.duration) return;
    const totalBlocks = blocks.length;
    // Rough: intro takes ~5% of audio, rest divided evenly among blocks
    const introFraction = 0.05;
    const blockFraction = (1 - introFraction - 0.03) / totalBlocks; // 3% for closing
    const t = aiAudio.currentTime / aiAudio.duration;

    let estimated = 0;
    if (t < introFraction) {{
      estimated = 0;
    }} else {{
      estimated = Math.floor((t - introFraction) / blockFraction);
      estimated = Math.min(estimated, totalBlocks - 1);
      estimated = Math.max(estimated, 0);
    }}

    if (estimated !== currentBlock) {{
      currentBlock = estimated;
      showBlock(currentBlock);
    }}
  }}

  // ── Browser speech ──────────────────────────────────────────────────
  function speak(text) {{
    if (!('speechSynthesis' in window)) return;
    window.speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(text);
    u.rate = 0.9; u.pitch = 1.0; u.volume = 1.0;
    const voices = window.speechSynthesis.getVoices();
    const preferred = voices.find(v =>
      v.name.includes('Samantha') || v.name.includes('Daniel') || v.name.includes('Google'));
    if (preferred) u.voice = preferred;
    window.speechSynthesis.speak(u);
  }}

  // ── Block display ───────────────────────────────────────────────────
  function updateDots() {{
    const container = document.getElementById('blockDots');
    container.innerHTML = '';
    for (let i = 0; i < blocks.length; i++) {{
      const dot = document.createElement('div');
      dot.className = 'dot' + (i < currentBlock ? ' done' : i === currentBlock ? ' active' : '');
      container.appendChild(dot);
    }}
  }}

  function showBlock(index) {{
    if (index < 0 || index >= blocks.length) return;
    const block = blocks[index];
    document.getElementById('blockPhase').textContent = (block.phase || 'BUILD').toUpperCase();
    document.getElementById('blockName').textContent = block.name.toUpperCase();
    document.getElementById('blockInstruction').textContent = block.instruction;
    updateDots();

    if (voiceMode === 'browser') {{
      speak(block.name + '. ' + block.instruction);
    }}
  }}

  function formatTime(s) {{
    const m = Math.floor(s / 60);
    const sec = s % 60;
    return m + ':' + sec.toString().padStart(2, '0');
  }}

  function runTimer(seconds, onDone) {{
    let remaining = seconds;
    const total = seconds;
    document.getElementById('timer').textContent = formatTime(remaining);
    document.getElementById('progressFill').style.width = '0%';

    timerInterval = setInterval(() => {{
      remaining--;
      document.getElementById('timer').textContent = formatTime(remaining);
      const pct = ((total - remaining) / total) * 100;
      document.getElementById('progressFill').style.width = pct + '%';

      if (remaining === 5 && voiceMode === 'browser') {{
        speak('5 seconds');
      }}

      if (remaining <= 0) {{
        clearInterval(timerInterval);
        onDone();
      }}
    }}, 1000);
  }}

  function nextBlock() {{
    currentBlock++;
    if (currentBlock >= blocks.length) {{
      finishSession();
      return;
    }}
    showBlock(currentBlock);
    if (voiceMode === 'browser') {{
      runTimer(blocks[currentBlock].duration || 60, nextBlock);
    }}
  }}

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
    currentBlock = 0;

    if (voiceMode === 'ai' && aiAudio && aiAudioReady) {{
      // AI mode — play audio, sync blocks visually
      aiSessionActive = true;
      aiAudio.currentTime = 0;
      aiAudio.play();
      showBlock(0);
      // Use audio-driven timing: the audio timeupdate handles block sync
      // Also run a visual timer that matches total session time
      const totalDuration = blocks.reduce((s, b) => s + (b.duration || 60), 0);
      runTimer(totalDuration, finishSession);
    }} else {{
      // Browser voice mode
      speak("Starting today's Jerome 7. " + blocks[0].name);
      setTimeout(() => {{
        showBlock(0);
        runTimer(blocks[0].duration || 60, nextBlock);
      }}, 2000);
    }}
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
