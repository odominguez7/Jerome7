"""Jerome7 Token system — non-financial tokens representing commitment."""

import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session as DBSession

from src.db.database import get_db
from src.db.models import Event, User

router = APIRouter()
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Token earn rates
# ---------------------------------------------------------------------------
EARN_RATES = {
    "session_complete": 10,
    "help_others": 25,
    "code_contribution": 50,
    "feedback": 15,
    "streak_milestone_7": 100,
    "streak_milestone_30": 500,
    "streak_milestone_100": 2000,
}

# Community pool — Omar's $1K equivalent = 10,000 tokens
COMMUNITY_POOL_INITIAL = 10_000
AUTO_APPROVE_LIMIT = 100

# Spend catalogue (for display)
SPEND_CATALOGUE = [
    {"item": "premium_audio", "cost": 50, "label": "Premium guided audio"},
    {"item": "coaching_call", "cost": 200, "label": "1-on-1 coaching call"},
    {"item": "exclusive_event", "cost": 150, "label": "Exclusive community event"},
]


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------
class EarnRequest(BaseModel):
    action: str


class SpendRequest(BaseModel):
    item: str
    cost: int


class PoolRequest(BaseModel):
    amount: int
    reason: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _user_balance(db: DBSession, user_id: str) -> dict:
    """Calculate balance by summing token events."""
    rows = (
        db.query(Event)
        .filter(
            Event.user_id == user_id,
            Event.event_type.in_(["token:earn", "token:spend", "token:request"]),
        )
        .order_by(Event.created_at.desc())
        .all()
    )

    earned_total = 0
    spent_total = 0
    recent = []

    for ev in rows:
        payload = ev.payload or {}
        amount = payload.get("amount", 0)
        if ev.event_type == "token:earn" or ev.event_type == "token:request":
            earned_total += amount
        elif ev.event_type == "token:spend":
            spent_total += amount

        if len(recent) < 20:
            recent.append({
                "type": ev.event_type,
                "amount": amount,
                "detail": payload.get("detail", ""),
                "created_at": ev.created_at.isoformat() if ev.created_at else None,
            })

    return {
        "balance": earned_total - spent_total,
        "earned_total": earned_total,
        "spent_total": spent_total,
        "recent_transactions": recent,
    }


def _pool_status(db: DBSession) -> dict:
    """Community pool: initial minus all token:request distributions."""
    distributed = (
        db.query(func.coalesce(func.sum(Event.payload["amount"].as_integer()), 0))
        .filter(Event.event_type == "token:request")
        .scalar()
    )
    # Fallback: iterate if JSON extraction isn't supported
    if distributed is None:
        distributed = 0
    # SQLite doesn't support JSON path extraction well, manual sum:
    req_events = (
        db.query(Event)
        .filter(Event.event_type == "token:request")
        .all()
    )
    distributed = sum((ev.payload or {}).get("amount", 0) for ev in req_events)

    return {
        "initial": COMMUNITY_POOL_INITIAL,
        "distributed": distributed,
        "remaining": COMMUNITY_POOL_INITIAL - distributed,
    }


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/tokens/{user_id}")
def get_token_balance(user_id: str, db: DBSession = Depends(get_db)):
    """Get user's token balance and history."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return _user_balance(db, user_id)


@router.post("/tokens/{user_id}/earn")
def earn_tokens(user_id: str, body: EarnRequest, db: DBSession = Depends(get_db)):
    """Award tokens for an action."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if body.action not in EARN_RATES:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown action '{body.action}'. Valid: {list(EARN_RATES.keys())}",
        )

    amount = EARN_RATES[body.action]
    event = Event(
        event_type="token:earn",
        user_id=user_id,
        payload={"action": body.action, "amount": amount, "detail": f"Earned {amount} tokens for {body.action}"},
    )
    db.add(event)
    db.commit()

    balance = _user_balance(db, user_id)
    return {"awarded": amount, "action": body.action, **balance}


@router.post("/tokens/{user_id}/spend")
def spend_tokens(user_id: str, body: SpendRequest, db: DBSession = Depends(get_db)):
    """Spend tokens on an item."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if body.cost <= 0:
        raise HTTPException(status_code=400, detail="Cost must be positive")

    balance_info = _user_balance(db, user_id)
    if balance_info["balance"] < body.cost:
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient balance. Have {balance_info['balance']}, need {body.cost}.",
        )

    event = Event(
        event_type="token:spend",
        user_id=user_id,
        payload={"item": body.item, "amount": body.cost, "detail": f"Spent {body.cost} tokens on {body.item}"},
    )
    db.add(event)
    db.commit()

    balance_info = _user_balance(db, user_id)
    return {"spent": body.cost, "item": body.item, **balance_info}


@router.get("/tokens/leaderboard")
def token_leaderboard(db: DBSession = Depends(get_db)):
    """Top 20 token earners by total earned."""
    earn_events = (
        db.query(Event)
        .filter(Event.event_type == "token:earn")
        .all()
    )

    # Aggregate per user
    totals: dict[str, int] = {}
    for ev in earn_events:
        uid = ev.user_id
        amt = (ev.payload or {}).get("amount", 0)
        totals[uid] = totals.get(uid, 0) + amt

    # Sort and take top 20
    sorted_users = sorted(totals.items(), key=lambda x: x[1], reverse=True)[:20]

    board = []
    for uid, total in sorted_users:
        user = db.query(User).filter(User.id == uid).first()
        board.append({
            "user_id": uid,
            "name": user.name if user else "Unknown",
            "earned_total": total,
        })

    return {"leaderboard": board}


@router.get("/tokens/pool")
def community_pool(db: DBSession = Depends(get_db)):
    """Community pool status."""
    return _pool_status(db)


@router.post("/tokens/{user_id}/request")
def request_tokens(user_id: str, body: PoolRequest, db: DBSession = Depends(get_db)):
    """Request tokens from the community pool."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if body.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")

    pool = _pool_status(db)
    if body.amount > pool["remaining"]:
        raise HTTPException(
            status_code=400,
            detail=f"Pool has {pool['remaining']} tokens remaining. Requested {body.amount}.",
        )

    approved = body.amount <= AUTO_APPROVE_LIMIT
    if not approved:
        raise HTTPException(
            status_code=400,
            detail=f"Requests above {AUTO_APPROVE_LIMIT} tokens require community approval.",
        )

    event = Event(
        event_type="token:request",
        user_id=user_id,
        payload={
            "amount": body.amount,
            "reason": body.reason,
            "detail": f"Pool request: {body.amount} tokens — {body.reason}",
            "auto_approved": True,
        },
    )
    db.add(event)
    db.commit()

    balance_info = _user_balance(db, user_id)
    return {"granted": body.amount, "reason": body.reason, **balance_info}


# ---------------------------------------------------------------------------
# HTML page
# ---------------------------------------------------------------------------

@router.get("/tokens", response_class=HTMLResponse)
def tokens_page(user_id: str = None, db: DBSession = Depends(get_db)):
    """HTML page explaining the token system."""

    # Earn rates table rows
    earn_rows = ""
    for action, amount in EARN_RATES.items():
        label = action.replace("_", " ").title()
        earn_rows += f'<tr><td>{label}</td><td class="amt">+{amount}</td></tr>\n'

    # Spend catalogue rows
    spend_rows = ""
    for item in SPEND_CATALOGUE:
        spend_rows += f'<tr><td>{item["label"]}</td><td class="amt">{item["cost"]}</td></tr>\n'

    # Pool status
    pool = _pool_status(db)

    # User balance (if provided)
    user_section = ""
    if user_id:
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            bal = _user_balance(db, user_id)
            txn_html = ""
            for txn in bal["recent_transactions"][:10]:
                sign = "+" if txn["type"] != "token:spend" else "-"
                color = "#3fb950" if sign == "+" else "#f85149"
                txn_html += f"""
                <div class="txn-row">
                  <span class="txn-amt" style="color:{color}">{sign}{txn['amount']}</span>
                  <span class="txn-detail">{txn['detail']}</span>
                </div>"""
            user_section = f"""
            <div class="section-label">YOUR BALANCE</div>
            <div class="balance-card">
              <div class="balance-name">{user.name}</div>
              <div class="balance-num">{bal['balance']}</div>
              <div class="balance-sub">tokens</div>
              <div class="balance-meta">Earned: {bal['earned_total']} &middot; Spent: {bal['spent_total']}</div>
            </div>
            <div class="section-label" style="margin-top:32px">RECENT TRANSACTIONS</div>
            {txn_html if txn_html else '<div class="empty">No transactions yet.</div>'}
            """

    # Leaderboard
    earn_events = db.query(Event).filter(Event.event_type == "token:earn").all()
    totals: dict[str, int] = {}
    for ev in earn_events:
        uid = ev.user_id
        amt = (ev.payload or {}).get("amount", 0)
        totals[uid] = totals.get(uid, 0) + amt
    sorted_users = sorted(totals.items(), key=lambda x: x[1], reverse=True)[:10]
    lb_html = ""
    for i, (uid, total) in enumerate(sorted_users):
        user_obj = db.query(User).filter(User.id == uid).first()
        name = user_obj.name if user_obj else "Unknown"
        rank = i + 1
        rank_color = {1: "#E85D04", 2: "#8b949e", 3: "#79c0ff"}.get(rank, "#484f58")
        lb_html += f"""
        <div class="lb-row">
          <span class="lb-rank" style="color:{rank_color}">{rank}</span>
          <span class="lb-name">{name}</span>
          <span class="lb-tokens">{total}</span>
        </div>"""
    if not lb_html:
        lb_html = '<div class="empty">No tokens earned yet. Be first.</div>'

    pool_pct = int((pool["distributed"] / pool["initial"]) * 100) if pool["initial"] else 0

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Jerome7 Tokens — Commitment, Not Currency</title>
<meta name="description" content="Jerome7 Tokens represent commitment, not money. Earn by showing up.">
<style>
  @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700;800&display=swap');
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    background: #0d1117; color: #c9d1d9;
    font-family: 'JetBrains Mono', monospace;
    min-height: 100vh; padding: 40px 20px;
  }}
  .container {{ max-width: 640px; margin: 0 auto; }}
  .nav {{
    display: flex; justify-content: space-between; align-items: center;
    margin-bottom: 48px;
  }}
  .brand {{ font-size: 11px; letter-spacing: 3px; color: #E85D04; text-decoration: none; }}
  .nav-links {{ display: flex; gap: 16px; }}
  .nav-links a {{ font-size: 12px; color: #484f58; text-decoration: none; }}
  .nav-links a:hover {{ color: #E85D04; }}

  h1 {{ font-size: 28px; font-weight: 800; color: #f0f6fc; margin-bottom: 8px; }}
  .subtitle {{ font-size: 13px; color: #8b949e; margin-bottom: 48px; line-height: 1.6; }}

  .section-label {{
    font-size: 10px; letter-spacing: 3px; color: #E85D04;
    margin-bottom: 16px; margin-top: 48px;
  }}
  .section-label:first-of-type {{ margin-top: 0; }}

  /* Tables */
  table {{ width: 100%; border-collapse: collapse; margin-bottom: 8px; }}
  th {{ font-size: 10px; letter-spacing: 2px; color: #484f58; text-align: left; padding: 8px 0; border-bottom: 1px solid #21262d; }}
  td {{ font-size: 13px; padding: 10px 0; border-bottom: 1px solid #21262d; color: #c9d1d9; }}
  .amt {{ font-weight: 700; color: #E85D04; text-align: right; }}

  /* Balance card */
  .balance-card {{
    background: #161b22; border: 1px solid #30363d; border-radius: 12px;
    padding: 32px; text-align: center; margin-bottom: 16px;
  }}
  .balance-name {{ font-size: 14px; color: #8b949e; margin-bottom: 8px; }}
  .balance-num {{ font-size: 48px; font-weight: 800; color: #E85D04; }}
  .balance-sub {{ font-size: 11px; color: #484f58; letter-spacing: 3px; margin-top: 4px; }}
  .balance-meta {{ font-size: 12px; color: #8b949e; margin-top: 16px; }}

  /* Transactions */
  .txn-row {{
    display: flex; align-items: center; gap: 12px;
    padding: 10px 0; border-bottom: 1px solid #21262d;
  }}
  .txn-amt {{ font-size: 14px; font-weight: 700; min-width: 60px; }}
  .txn-detail {{ font-size: 12px; color: #8b949e; }}

  /* Leaderboard */
  .lb-row {{
    display: flex; align-items: center; gap: 12px;
    padding: 12px 0; border-bottom: 1px solid #21262d;
  }}
  .lb-rank {{ font-size: 16px; font-weight: 800; min-width: 24px; }}
  .lb-name {{ font-size: 14px; color: #f0f6fc; font-weight: 600; flex: 1; }}
  .lb-tokens {{ font-size: 14px; font-weight: 700; color: #E85D04; }}

  /* Pool */
  .pool-card {{
    background: #161b22; border: 1px solid #30363d; border-radius: 12px;
    padding: 24px; margin-bottom: 16px;
  }}
  .pool-bar {{
    height: 8px; background: #21262d; border-radius: 4px; overflow: hidden;
    margin: 16px 0;
  }}
  .pool-fill {{ height: 100%; background: #E85D04; border-radius: 4px; }}
  .pool-nums {{
    display: flex; justify-content: space-between;
    font-size: 12px; color: #8b949e;
  }}
  .pool-remaining {{ font-size: 24px; font-weight: 800; color: #f0f6fc; }}
  .pool-label {{ font-size: 11px; color: #484f58; letter-spacing: 2px; }}

  .empty {{ font-size: 13px; color: #484f58; padding: 24px 0; }}

  .philosophy {{
    background: #161b22; border-left: 3px solid #E85D04;
    padding: 20px 24px; margin-bottom: 48px;
    font-size: 13px; color: #8b949e; line-height: 1.7;
  }}

  .back-link {{
    display: inline-block; margin-top: 48px;
    font-size: 12px; color: #484f58; text-decoration: none;
  }}
  .back-link:hover {{ color: #E85D04; }}
</style>
</head>
<body>
<div class="container">
  <div class="nav">
    <a href="/" class="brand">JEROME7</a>
    <div class="nav-links">
      <a href="/leaderboard">Leaderboard</a>
      <a href="https://discord.gg/5AZP8DbEJm">Discord</a>
    </div>
  </div>

  <h1>Tokens.</h1>
  <div class="subtitle">
    Jerome7 Tokens represent commitment, not money.<br>
    You earn them by showing up. You spend them on things that help you keep showing up.
  </div>

  <div class="philosophy">
    These aren't cryptocurrency. They aren't tradeable. They aren't worth dollars.<br><br>
    They're proof that you did the work. Every token is a record of commitment —
    sessions completed, people helped, code contributed, feedback given.<br><br>
    The community pool started with 10,000 tokens — Omar's way of saying
    "I believe in you before you believe in yourself." Anyone can request tokens.
    No gatekeeping. No means testing.
  </div>

  {user_section}

  <div class="section-label">HOW TO EARN</div>
  <table>
    <tr><th>ACTION</th><th style="text-align:right">TOKENS</th></tr>
    {earn_rows}
  </table>

  <div class="section-label">HOW TO SPEND</div>
  <table>
    <tr><th>ITEM</th><th style="text-align:right">COST</th></tr>
    {spend_rows}
  </table>

  <div class="section-label">COMMUNITY POOL</div>
  <div class="pool-card">
    <div class="pool-label">REMAINING</div>
    <div class="pool-remaining">{pool['remaining']:,}</div>
    <div class="pool-bar"><div class="pool-fill" style="width:{pool_pct}%"></div></div>
    <div class="pool-nums">
      <span>Distributed: {pool['distributed']:,}</span>
      <span>Initial: {pool['initial']:,}</span>
    </div>
  </div>

  <div class="section-label">TOP EARNERS</div>
  {lb_html}

  <a href="/" class="back-link">&larr; back to jerome7.com</a>
</div>
</body>
</html>"""
    return HTMLResponse(content=html)
