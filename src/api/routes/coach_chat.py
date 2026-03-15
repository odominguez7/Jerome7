"""GET /coach — Coach Chat UI.  POST /coach/ask — talk to your AI coach."""

import asyncio
import os

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session as DBSession

from src.db.database import get_db
from src.db.models import User, Streak, Seven7Session, Nudge, SessionFeedback

router = APIRouter()


# ---------------------------------------------------------------------------
# Gemini helper (same pattern as coach.py)
# ---------------------------------------------------------------------------

COACH_CHAT_SYSTEM = (
    "You are Jerome7's AI Coach. You have access to this user's complete data. "
    "Be direct, supportive, never shame. Use 'show up' not 'work out'. "
    "Use 'chain' not 'streak'. Use 'session' not 'workout'. "
    "Keep responses under 3 sentences. Reference their actual data."
)


def _call_gemini(system_prompt: str, user_content: str, api_key: str) -> str:
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=user_content,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
        ),
    )
    return response.text


# ---------------------------------------------------------------------------
# POST /coach/ask
# ---------------------------------------------------------------------------

class CoachAskRequest(BaseModel):
    user_id: str
    message: str


def _build_user_context(user: User, streak: Streak | None,
                        sessions: list, feedback: list,
                        nudges: list) -> str:
    """Build a plain-text context block the LLM can reference."""
    parts: list[str] = []
    parts.append(f"Name: {user.name}")
    parts.append(f"Goal: {user.goal.value if user.goal else 'not set'}")
    parts.append(f"Fitness level: {user.fitness_level.value if user.fitness_level else 'beginner'}")
    parts.append(f"Joined: {user.created_at.strftime('%Y-%m-%d') if user.created_at else 'unknown'}")

    if streak:
        parts.append(f"Current chain: {streak.current_streak} days")
        parts.append(f"Longest chain: {streak.longest_streak} days")
        parts.append(f"Total sessions: {streak.total_sessions}")
        parts.append(f"Last session date: {streak.last_session_date}")
    else:
        parts.append("No chain data yet.")

    if sessions:
        recent = sessions[:5]
        titles = [s.session_title or "untitled" for s in recent]
        parts.append(f"Recent sessions: {', '.join(titles)}")

    if feedback:
        diffs = [f.difficulty_rating for f in feedback if f.difficulty_rating]
        enjoys = [f.enjoyment_rating for f in feedback if f.enjoyment_rating]
        if diffs:
            parts.append(f"Avg difficulty (1-5): {sum(diffs)/len(diffs):.1f}")
        if enjoys:
            parts.append(f"Avg enjoyment (1-5): {sum(enjoys)/len(enjoys):.1f}")
        body_notes = [f.body_note for f in feedback if f.body_note]
        if body_notes:
            parts.append(f"Recent body notes: {'; '.join(body_notes[:3])}")

    if nudges:
        parts.append(f"Nudges sent recently: {len(nudges)}")
        latest = nudges[0]
        parts.append(f"Last nudge: {latest.message_text or '(no text)'}")

    return "\n".join(parts)


def _static_fallback(streak: Streak | None) -> str:
    """Return a helpful static message when Gemini is unavailable."""
    if streak and streak.current_streak > 0:
        return (
            f"Your chain is at {streak.current_streak} days. "
            "Keep showing up — consistency compounds. "
            "I can't connect to my brain right now, but your data is safe."
        )
    return (
        "I can't reach my AI brain right now, but your data is here. "
        "Show up today and the chain starts building."
    )


@router.post("/coach/ask")
async def coach_ask(req: CoachAskRequest, db: DBSession = Depends(get_db)):
    # 1. Look up user
    user = db.query(User).filter(User.id == req.user_id).first()
    if not user:
        return JSONResponse(content={
            "response": (
                "I don't have your data yet. "
                "Complete a session first at jerome7.com/timer — "
                "then come back and we'll talk."
            ),
            "agent": "coach",
        })

    # 2-4. Gather context
    streak = db.query(Streak).filter(Streak.user_id == req.user_id).first()

    sessions = (
        db.query(Seven7Session)
        .filter(Seven7Session.user_id == req.user_id)
        .order_by(Seven7Session.generated_at.desc())
        .limit(10)
        .all()
    )

    feedback = (
        db.query(SessionFeedback)
        .filter(SessionFeedback.user_id == req.user_id)
        .order_by(SessionFeedback.created_at.desc())
        .limit(10)
        .all()
    )

    nudges = (
        db.query(Nudge)
        .filter(Nudge.user_id == req.user_id)
        .order_by(Nudge.sent_at.desc())
        .limit(5)
        .all()
    )

    # 5. Build context string
    context = _build_user_context(user, streak, sessions, feedback, nudges)

    # 6. Call Gemini
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return JSONResponse(content={
            "response": _static_fallback(streak),
            "agent": "coach",
        })

    prompt = f"USER DATA:\n{context}\n\nUSER MESSAGE:\n{req.message}"

    try:
        text = await asyncio.wait_for(
            asyncio.to_thread(_call_gemini, COACH_CHAT_SYSTEM, prompt, api_key),
            timeout=25,
        )
        return JSONResponse(content={"response": text.strip(), "agent": "coach"})
    except Exception as e:
        print(f"[CoachChat] Gemini error: {e}")
        return JSONResponse(content={
            "response": _static_fallback(streak),
            "agent": "coach",
        })


# ---------------------------------------------------------------------------
# GET /coach — Chat UI
# ---------------------------------------------------------------------------

@router.get("/coach", response_class=HTMLResponse)
async def coach_chat_page():
    html = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Jerome7 — Coach Chat</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700;800&display=swap');
  * { box-sizing: border-box; margin: 0; padding: 0; }

  body {
    background: #0f1419;
    color: #c9d1d9;
    font-family: 'JetBrains Mono', monospace;
    height: 100vh;
    display: flex;
    flex-direction: column;
  }

  /* --- NAV --- */
  .nav {
    position: fixed; top: 0; left: 0; right: 0; z-index: 100;
    display: flex; align-items: center; justify-content: space-between;
    padding: 12px 24px;
    background: rgba(15,20,25,0.92);
    backdrop-filter: blur(12px);
    border-bottom: 1px solid #21262d;
  }
  .nav-brand {
    font-size: 13px; font-weight: 800; color: #e8713a;
    letter-spacing: 2px; text-decoration: none;
  }
  .nav-links { display: flex; gap: 20px; align-items: center; }
  .nav-links a {
    font-size: 12px; color: #8b949e; text-decoration: none;
    letter-spacing: 0.5px; transition: color 0.2s;
  }
  .nav-links a:hover { color: #f0f6fc; }
  .nav-links .nav-active { color: #e8713a; font-weight: 700; }

  /* --- LAYOUT --- */
  .chat-container {
    flex: 1; display: flex; flex-direction: column;
    max-width: 680px; width: 100%; margin: 0 auto;
    padding-top: 64px;
  }

  /* --- USER ID BAR --- */
  .id-bar {
    display: flex; gap: 8px; padding: 16px 20px;
    border-bottom: 1px solid #21262d;
    align-items: center;
  }
  .id-bar label {
    font-size: 11px; color: #8b949e; letter-spacing: 1px;
    white-space: nowrap;
  }
  .id-bar input {
    flex: 1; background: #161b22; border: 1px solid #30363d;
    border-radius: 6px; padding: 8px 12px; color: #f0f6fc;
    font-family: inherit; font-size: 12px; outline: none;
  }
  .id-bar input:focus { border-color: #e8713a; }

  /* --- CHIPS --- */
  .chips {
    display: flex; flex-wrap: wrap; gap: 8px;
    padding: 16px 20px; border-bottom: 1px solid #21262d;
  }
  .chip {
    background: #161b22; border: 1px solid #30363d;
    border-radius: 100px; padding: 6px 14px;
    font-size: 11px; color: #8b949e; cursor: pointer;
    font-family: inherit; transition: all 0.2s;
  }
  .chip:hover { border-color: #e8713a; color: #e8713a; }

  /* --- MESSAGES --- */
  .messages {
    flex: 1; overflow-y: auto; padding: 20px;
    display: flex; flex-direction: column; gap: 12px;
  }

  .msg {
    max-width: 85%; padding: 12px 16px;
    border-radius: 12px; font-size: 13px;
    line-height: 1.5; word-wrap: break-word;
  }

  .msg-user {
    align-self: flex-end; background: #2d333b; color: #f0f6fc;
    border-bottom-right-radius: 4px;
  }

  .msg-coach {
    align-self: flex-start;
    background: linear-gradient(135deg, #2a1f14 0%, #1a1510 100%);
    border: 1px solid rgba(232,113,58,0.25);
    color: #e8d5c4; border-bottom-left-radius: 4px;
  }

  .msg-coach .coach-label {
    font-size: 9px; font-weight: 700; letter-spacing: 1px;
    color: #e8713a; margin-bottom: 4px;
  }

  .msg-error {
    align-self: center; background: transparent;
    color: #f85149; font-size: 11px; text-align: center;
  }

  .msg-typing {
    align-self: flex-start; background: transparent;
    color: #484f58; font-size: 12px;
  }
  .msg-typing .dots span {
    animation: blink 1.4s infinite both;
  }
  .msg-typing .dots span:nth-child(2) { animation-delay: 0.2s; }
  .msg-typing .dots span:nth-child(3) { animation-delay: 0.4s; }
  @keyframes blink { 0%,80%,100% { opacity: 0.2; } 40% { opacity: 1; } }

  /* --- INPUT BAR --- */
  .input-bar {
    display: flex; gap: 8px; padding: 16px 20px;
    border-top: 1px solid #21262d; background: #0f1419;
  }
  .input-bar input {
    flex: 1; background: #161b22; border: 1px solid #30363d;
    border-radius: 8px; padding: 12px 16px; color: #f0f6fc;
    font-family: inherit; font-size: 13px; outline: none;
  }
  .input-bar input:focus { border-color: #e8713a; }
  .input-bar input::placeholder { color: #484f58; }

  .send-btn {
    background: #e8713a; border: none; border-radius: 8px;
    padding: 12px 20px; color: #fff; font-family: inherit;
    font-size: 13px; font-weight: 700; cursor: pointer;
    letter-spacing: 0.5px; transition: background 0.2s;
  }
  .send-btn:hover { background: #ff8a50; }
  .send-btn:disabled { opacity: 0.4; cursor: not-allowed; }

  /* --- EMPTY STATE --- */
  .empty-state {
    flex: 1; display: flex; flex-direction: column;
    align-items: center; justify-content: center;
    color: #484f58; text-align: center; padding: 40px 20px;
  }
  .empty-state .icon { font-size: 48px; margin-bottom: 16px; opacity: 0.4; }
  .empty-state h3 { font-size: 16px; color: #8b949e; margin-bottom: 8px; }
  .empty-state p { font-size: 12px; max-width: 320px; }

  @media (max-width: 480px) {
    .nav-links { gap: 12px; }
    .nav-links a { font-size: 11px; }
    .chips { padding: 12px 16px; gap: 6px; }
    .chip { font-size: 10px; padding: 5px 10px; }
    .messages { padding: 16px; }
    .input-bar { padding: 12px 16px; }
  }
</style>
</head>
<body>

<nav class="nav">
  <a href="/" class="nav-brand">JEROME7</a>
  <div class="nav-links">
    <a href="/timer">Timer</a>
    <a href="/voice">Voice</a>
    <a href="/coach" class="nav-active">Coach</a>
    <a href="/leaderboard">Leaderboard</a>
    <a href="/analytics">Analytics</a>
  </div>
</nav>

<div class="chat-container">
  <div class="id-bar">
    <label>YOUR ID</label>
    <input type="text" id="user-id" placeholder="paste your user_id here" />
  </div>

  <div class="chips" id="chips">
    <button class="chip" onclick="askChip(this)">Why was today's session so hard?</button>
    <button class="chip" onclick="askChip(this)">What's my predicted streak outcome?</button>
    <button class="chip" onclick="askChip(this)">How do I compare to other builders?</button>
    <button class="chip" onclick="askChip(this)">What should I focus on this week?</button>
    <button class="chip" onclick="askChip(this)">Tell me about my consistency pattern</button>
  </div>

  <div class="messages" id="messages">
    <div class="empty-state" id="empty-state">
      <div class="icon">&#9775;</div>
      <h3>Talk to your coach</h3>
      <p>Ask anything about your data, your chain, your progress. Pick a question above or type your own.</p>
    </div>
  </div>

  <div class="input-bar">
    <input type="text" id="msg-input" placeholder="Ask your coach anything..."
           onkeydown="if(event.key==='Enter')sendMessage()" />
    <button class="send-btn" id="send-btn" onclick="sendMessage()">SEND</button>
  </div>
</div>

<script>
const messagesEl = document.getElementById('messages');
const inputEl    = document.getElementById('msg-input');
const sendBtn    = document.getElementById('send-btn');
const emptyState = document.getElementById('empty-state');
const userIdEl   = document.getElementById('user-id');

// Pre-fill user_id from query param
const params = new URLSearchParams(window.location.search);
if (params.get('user_id')) userIdEl.value = params.get('user_id');

function addMessage(text, type) {
  if (emptyState) emptyState.remove();
  const div = document.createElement('div');
  div.className = 'msg msg-' + type;
  if (type === 'coach') {
    div.innerHTML = '<div class="coach-label">COACH</div>' + escapeHtml(text);
  } else if (type === 'typing') {
    div.innerHTML = '<span class="dots"><span>.</span><span>.</span><span>.</span></span>';
    div.id = 'typing-indicator';
  } else {
    div.textContent = text;
  }
  messagesEl.appendChild(div);
  messagesEl.scrollTop = messagesEl.scrollHeight;
  return div;
}

function removeTyping() {
  const t = document.getElementById('typing-indicator');
  if (t) t.remove();
}

function escapeHtml(text) {
  const d = document.createElement('div');
  d.textContent = text;
  return d.innerHTML;
}

function askChip(el) {
  inputEl.value = el.textContent;
  sendMessage();
}

async function sendMessage() {
  const userId = userIdEl.value.trim();
  const message = inputEl.value.trim();
  if (!message) return;
  if (!userId) {
    addMessage('Enter your user_id above first.', 'error');
    return;
  }

  addMessage(message, 'user');
  inputEl.value = '';
  sendBtn.disabled = true;
  addMessage('', 'typing');

  try {
    const res = await fetch('/coach/ask', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: userId, message: message }),
    });
    const data = await res.json();
    removeTyping();
    addMessage(data.response, 'coach');
  } catch (err) {
    removeTyping();
    addMessage('Connection error. Try again.', 'error');
  }
  sendBtn.disabled = false;
  inputEl.focus();
}
</script>
</body>
</html>"""
    return HTMLResponse(content=html)
