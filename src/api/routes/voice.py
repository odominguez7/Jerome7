"""GET /voice — hands-free voice-guided Jerome7 session using Web Speech API."""

from datetime import datetime

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session as DBSession

from src.db.database import get_db
from src.api.routes.daily import get_daily

router = APIRouter()


@router.get("/voice", response_class=HTMLResponse)
async def voice_session(db: DBSession = Depends(get_db)):
    """Voice-guided session — browser reads each block aloud. Hands-free."""
    session = await get_daily(db)
    blocks = session.get("blocks", [])
    title = session.get("session_title", "the seven 7")

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
<meta name="description" content="Hands-free 7-minute session. Your browser reads each block aloud.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700;800&display=swap" rel="stylesheet">
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    background: #0d1117; color: #c9d1d9;
    font-family: 'JetBrains Mono', monospace;
    min-height: 100vh; display: flex; align-items: center; justify-content: center;
  }}
  .container {{ max-width: 520px; width: 100%; padding: 40px 20px; text-align: center; }}

  .nav {{
    display: flex; justify-content: space-between; align-items: center;
    margin-bottom: 60px;
  }}
  .brand {{ font-size: 11px; letter-spacing: 3px; color: #E85D04; text-decoration: none; font-weight: 700; }}
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

  /* Current block */
  .block-phase {{
    font-size: 10px; letter-spacing: 3px; color: #E85D04; margin-bottom: 8px;
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
    height: 100%; background: #E85D04; border-radius: 2px;
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
  .dot.active {{ background: #E85D04; animation: pulse 1s infinite; }}

  /* Start button */
  .start-btn {{
    display: inline-block; padding: 16px 48px;
    background: #E85D04; color: #fff; font-weight: 700;
    font-size: 13px; letter-spacing: 2px;
    border: none; border-radius: 6px; cursor: pointer;
    font-family: inherit;
  }}
  .start-btn:hover {{ background: #c24e03; }}
  .start-btn:disabled {{ background: #21262d; color: #484f58; cursor: default; }}

  .note {{ font-size: 10px; color: #30363d; margin-top: 16px; letter-spacing: 1px; }}

  /* Complete state */
  .complete {{ display: none; }}
  .complete.show {{ display: block; }}
  .complete-check {{ font-size: 64px; margin-bottom: 16px; }}
  .complete-text {{ font-size: 14px; color: #8b949e; line-height: 1.6; }}

  .hidden {{ display: none; }}
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
    <div class="subtitle">HANDS-FREE · YOUR BROWSER READS EACH BLOCK</div>
    <button class="start-btn" id="startBtn" onclick="startSession()">START VOICE SESSION</button>
    <div class="note">Uses your browser's speech synthesis. No data leaves your device.</div>
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
    <div class="complete-check">\u2705</div>
    <div class="title">SESSION COMPLETE</div>
    <div class="complete-text" id="closingText"></div>
    <div class="note" style="margin-top:24px">
      <a href="/timer" style="color:#E85D04;text-decoration:none">TIMER</a> ·
      <a href="/leaderboard" style="color:#484f58;text-decoration:none">LEADERBOARD</a> ·
      <a href="/voice" style="color:#484f58;text-decoration:none">REPLAY</a>
    </div>
  </div>

</div>

<script>
  const blocks = {blocks_js};
  const closing = '{session.get("closing", "You showed up. That is the win.").replace(chr(39), chr(92)+chr(39))}';
  let currentBlock = 0;
  let timerInterval = null;

  function speak(text) {{
    if (!('speechSynthesis' in window)) return;
    window.speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(text);
    u.rate = 0.9;
    u.pitch = 1.0;
    u.volume = 1.0;
    // Try to pick a good voice
    const voices = window.speechSynthesis.getVoices();
    const preferred = voices.find(v => v.name.includes('Samantha') || v.name.includes('Daniel') || v.name.includes('Google'));
    if (preferred) u.voice = preferred;
    window.speechSynthesis.speak(u);
  }}

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
    const block = blocks[index];
    document.getElementById('blockPhase').textContent = (block.phase || 'BUILD').toUpperCase();
    document.getElementById('blockName').textContent = block.name.toUpperCase();
    document.getElementById('blockInstruction').textContent = block.instruction;
    updateDots();

    // Speak the instruction
    speak(block.name + '. ' + block.instruction);
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

      // 5-second warning
      if (remaining === 5) {{
        speak('5 seconds');
      }}

      if (remaining <= 0) {{
        clearInterval(timerInterval);
        onDone();
      }}
    }}, 1000);
  }}

  function formatTime(s) {{
    const m = Math.floor(s / 60);
    const sec = s % 60;
    return m + ':' + sec.toString().padStart(2, '0');
  }}

  function nextBlock() {{
    currentBlock++;
    if (currentBlock >= blocks.length) {{
      // Done
      document.getElementById('activeSession').classList.add('hidden');
      document.getElementById('complete').classList.add('show');
      document.getElementById('closingText').textContent = closing;
      document.getElementById('voicePulse').classList.remove('active');
      speak('Session complete. ' + closing);
      return;
    }}
    showBlock(currentBlock);
    runTimer(blocks[currentBlock].duration || 60, nextBlock);
  }}

  function startSession() {{
    document.getElementById('preStart').classList.add('hidden');
    document.getElementById('activeSession').classList.remove('hidden');
    document.getElementById('voicePulse').classList.add('active');

    speak("Starting today's Jerome 7. " + blocks[0].name);

    setTimeout(() => {{
      showBlock(0);
      runTimer(blocks[0].duration || 60, nextBlock);
    }}, 2000);
  }}

  // Preload voices
  if ('speechSynthesis' in window) {{
    window.speechSynthesis.getVoices();
  }}
</script>
</body>
</html>"""

    return HTMLResponse(content=html)
