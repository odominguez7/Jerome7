"""GET /sponsor — Sponsorship page for Jerome7."""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()


@router.get("/sponsor", response_class=HTMLResponse)
async def sponsor_page():
    html = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Support Jerome7 — Because YU Matter</title>
<meta name="description" content="Support Jerome7. Omar is investing $1,000 of his own money. Because YU matter.">
<style>
  @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700;800&display=swap');
  * { box-sizing: border-box; margin: 0; padding: 0; }

  body {
    background: #0f1419;
    color: #c9d1d9;
    font-family: 'JetBrains Mono', monospace;
    line-height: 1.6;
    overflow-x: hidden;
  }

  /* --- NAV --- */
  .nav {
    position: fixed;
    top: 0; left: 0; right: 0;
    z-index: 100;
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 12px 24px;
    background: rgba(15,20,25,0.92);
    backdrop-filter: blur(12px);
    border-bottom: 1px solid #21262d;
  }
  .nav-brand {
    font-size: 13px; font-weight: 800;
    color: #E85D04; letter-spacing: 2px;
    text-decoration: none;
  }
  .nav-links { display: flex; gap: 20px; align-items: center; }
  .nav-links a {
    font-size: 12px; color: #8b949e;
    text-decoration: none; letter-spacing: 0.5px;
    transition: color 0.2s;
  }
  .nav-links a:hover { color: #f0f6fc; }

  /* --- HERO --- */
  .hero {
    min-height: 50vh;
    display: flex; flex-direction: column;
    align-items: center; justify-content: center;
    text-align: center;
    padding: 120px 20px 60px;
  }

  .section-label {
    font-size: 10px; letter-spacing: 3px;
    color: #E85D04; margin-bottom: 24px;
  }

  h1 {
    font-size: clamp(28px, 6vw, 48px);
    font-weight: 800; color: #f0f6fc;
    line-height: 1.1; margin-bottom: 16px;
  }
  h1 span { color: #E85D04; }

  .subtitle {
    font-size: 16px; color: #8b949e;
    max-width: 520px; margin-bottom: 48px;
  }

  /* --- SECTIONS --- */
  section {
    max-width: 680px;
    margin: 0 auto;
    padding: 60px 20px;
  }

  h2 {
    font-size: 22px; font-weight: 700;
    color: #f0f6fc; margin-bottom: 16px;
  }

  p { color: #8b949e; font-size: 14px; margin-bottom: 16px; }

  /* --- FUND TABLE --- */
  .fund-table {
    width: 100%;
    border-collapse: collapse;
    margin: 24px 0;
    font-size: 13px;
  }
  .fund-table th {
    text-align: left;
    font-size: 10px; letter-spacing: 2px;
    color: #E85D04;
    padding: 10px 12px;
    border-bottom: 2px solid #E85D04;
  }
  .fund-table td {
    padding: 10px 12px;
    border-bottom: 1px solid #21262d;
    color: #c9d1d9;
  }
  .fund-table td:last-child {
    color: #E85D04; font-weight: 700;
    text-align: right;
  }
  .fund-table tr:last-child td {
    border-bottom: none;
    color: #f0f6fc; font-weight: 800;
  }
  .fund-table tr:last-child td:last-child {
    color: #E85D04;
  }

  .tracked {
    font-size: 12px; color: #484f58;
    margin-top: 12px; font-style: italic;
  }

  /* --- TIERS --- */
  .tiers {
    display: flex; flex-direction: column;
    gap: 16px; margin: 24px 0;
  }
  .tier {
    background: #161b22;
    border: 1px solid #21262d;
    border-radius: 12px;
    padding: 24px;
    transition: border-color 0.2s;
  }
  .tier:hover { border-color: #E85D04; }

  .tier-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 12px;
  }
  .tier-name {
    font-size: 16px; font-weight: 700;
    color: #f0f6fc;
  }
  .tier-price {
    font-size: 20px; font-weight: 800;
    color: #E85D04;
  }
  .tier-price span {
    font-size: 12px; font-weight: 400;
    color: #484f58;
  }
  .tier-benefits {
    list-style: none; padding: 0;
  }
  .tier-benefits li {
    font-size: 13px; color: #8b949e;
    padding: 4px 0;
    padding-left: 20px;
    position: relative;
  }
  .tier-benefits li::before {
    content: ">";
    position: absolute; left: 0;
    color: #E85D04; font-weight: 700;
  }

  /* --- IN-KIND --- */
  .in-kind {
    background: #161b22;
    border: 1px solid #21262d;
    border-radius: 12px;
    padding: 24px;
    margin: 24px 0;
  }
  .in-kind-title {
    font-size: 14px; font-weight: 700;
    color: #f0f6fc; margin-bottom: 8px;
  }
  .in-kind p { font-size: 13px; margin-bottom: 0; }

  /* --- CTA BUTTONS --- */
  .cta-row {
    display: flex; gap: 16px;
    flex-wrap: wrap;
    justify-content: center;
    margin: 40px 0;
  }
  .btn {
    padding: 14px 32px;
    border-radius: 100px; border: none;
    cursor: pointer; font-family: inherit;
    font-size: 14px; font-weight: 700;
    letter-spacing: 1px;
    text-decoration: none;
    transition: all 0.2s;
  }
  .btn-primary { background: #E85D04; color: #fff; }
  .btn-primary:hover { background: #ff6b1a; transform: translateY(-1px); }
  .btn-ghost {
    background: transparent; color: #8b949e;
    border: 1px solid #30363d;
  }
  .btn-ghost:hover { border-color: #E85D04; color: #E85D04; }

  /* --- WALL OF GRATITUDE --- */
  .wall {
    text-align: center;
    padding: 60px 20px 80px;
    max-width: 680px;
    margin: 0 auto;
  }
  .wall h2 { margin-bottom: 24px; }
  .sponsors-grid {
    display: flex; flex-wrap: wrap;
    gap: 12px; justify-content: center;
    margin-top: 24px;
  }
  .sponsor-badge {
    background: #161b22;
    border: 1px solid #21262d;
    border-radius: 100px;
    padding: 8px 20px;
    font-size: 13px; color: #c9d1d9;
    transition: border-color 0.2s;
  }
  .sponsor-badge:hover { border-color: #E85D04; }
  .sponsor-badge.anon { color: #484f58; font-style: italic; }

  /* --- FOOTER --- */
  .footer {
    text-align: center;
    padding: 40px 20px 60px;
    border-top: 1px solid #21262d;
  }
  .footer-brand {
    font-size: 11px; letter-spacing: 3px;
    color: #E85D04; margin-bottom: 8px;
  }
  .footer-text { font-size: 12px; color: #484f58; }
  .footer a { color: #E85D04; text-decoration: none; }

  /* --- DIVIDER --- */
  .divider {
    width: 60px; height: 2px;
    background: #E85D04;
    margin: 0 auto 24px;
    opacity: 0.5;
  }

  @media (max-width: 480px) {
    .hero { padding: 100px 16px 40px; }
    h1 { font-size: 26px; }
    section { padding: 40px 16px; }
    .tier { padding: 16px; }
    .nav-links { gap: 12px; }
    .nav-links a { font-size: 11px; }
  }
</style>
</head>
<body>

<!-- NAV -->
<nav class="nav">
  <a href="/" class="nav-brand">JEROME7</a>
  <div class="nav-links">
    <a href="/">Home</a>
    <a href="/timer">Timer</a>
    <a href="/leaderboard">Leaderboard</a>
    <a href="https://github.com/odominguez7/Jerome7">GitHub</a>
    <a href="https://discord.gg/5AZP8DbEJm">Discord</a>
  </div>
</nav>

<!-- HERO -->
<div class="hero">
  <div class="section-label">SUPPORT</div>
  <h1>Support <span>Jerome7</span></h1>
  <div class="subtitle">Omar is investing $1,000 of his own money. Because YU matter.</div>
</div>

<!-- THE $1,000 PROMISE -->
<section>
  <div class="section-label">THE $1,000 PROMISE</div>
  <h2>Where every dollar goes.</h2>
  <p>Full transparency. Every dollar is tracked publicly. This is a commitment to the community, not a pitch.</p>

  <table class="fund-table">
    <thead>
      <tr><th>ALLOCATION</th><th>AMOUNT</th></tr>
    </thead>
    <tbody>
      <tr><td>ElevenLabs API (AI Voice)</td><td>$300</td></tr>
      <tr><td>Gemini API (Coach Agent)</td><td>$200</td></tr>
      <tr><td>Terra API (Wearables)</td><td>$150</td></tr>
      <tr><td>Cloud Hosting</td><td>$200</td></tr>
      <tr><td>Community Rewards</td><td>$100</td></tr>
      <tr><td>Contingency</td><td>$50</td></tr>
      <tr><td><strong>Total</strong></td><td>$1,000</td></tr>
    </tbody>
  </table>

  <div class="tracked">Every dollar is tracked publicly.</div>
</section>

<!-- SPONSORSHIP TIERS -->
<section>
  <div class="section-label">SPONSORSHIP TIERS</div>
  <h2>Stand with builders.</h2>
  <p>Your support keeps Jerome7 free, open source, and evolving. Pick a tier that feels right.</p>

  <div class="tiers">
    <div class="tier">
      <div class="tier-header">
        <div class="tier-name">Supporter</div>
        <div class="tier-price">$10 <span>/mo</span></div>
      </div>
      <ul class="tier-benefits">
        <li>Name on README</li>
        <li>Discord sponsor role</li>
      </ul>
    </div>

    <div class="tier">
      <div class="tier-header">
        <div class="tier-name">Champion</div>
        <div class="tier-price">$50 <span>/mo</span></div>
      </div>
      <ul class="tier-benefits">
        <li>Everything in Supporter</li>
        <li>Early access to new features</li>
        <li>Private Discord channel</li>
      </ul>
    </div>

    <div class="tier">
      <div class="tier-header">
        <div class="tier-name">Patron</div>
        <div class="tier-price">$100 <span>/mo</span></div>
      </div>
      <ul class="tier-benefits">
        <li>Everything in Champion</li>
        <li>Steering input on roadmap</li>
        <li>Quarterly call with Omar</li>
      </ul>
    </div>
  </div>
</section>

<!-- IN-KIND SPONSORS -->
<section>
  <div class="section-label">IN-KIND SPONSORS</div>
  <h2>Technology Partners.</h2>
  <div class="in-kind">
    <div class="in-kind-title">API Credits &amp; Infrastructure</div>
    <p>Companies donating API credits are recognized as Technology Partners. Your logo on the README, website, and all launch materials. Reach out via Discord or GitHub.</p>
  </div>
</section>

<!-- CTA -->
<div class="cta-row">
  <a href="https://github.com/sponsors/odominguez7" class="btn btn-primary" target="_blank">SPONSOR ON GITHUB</a>
  <a href="https://discord.gg/5AZP8DbEJm" class="btn btn-ghost" target="_blank">JOIN DISCORD</a>
</div>

<!-- WALL OF GRATITUDE -->
<div class="wall">
  <div class="divider"></div>
  <div class="section-label">WALL OF GRATITUDE</div>
  <h2>Those who showed up first.</h2>
  <p>Every sponsor gets their name here. You believed before it was obvious.</p>
  <div class="sponsors-grid">
    <div class="sponsor-badge anon">A builder who cares &#10084;&#65039;</div>
    <div class="sponsor-badge anon">A builder who cares &#10084;&#65039;</div>
    <div class="sponsor-badge anon">A builder who cares &#10084;&#65039;</div>
  </div>
  <p style="margin-top:24px;font-size:12px;color:#484f58;">Your name here. Be the first.</p>
</div>

<!-- FOOTER -->
<div class="footer">
  <div class="footer-brand">JEROME7</div>
  <div class="footer-text">Free forever. Open source. Built at MIT.</div>
  <div class="footer-text" style="margin-top: 8px;">
    <a href="/">Home</a> &middot;
    <a href="/timer">Timer</a> &middot;
    <a href="/leaderboard">Leaderboard</a> &middot;
    <a href="https://github.com/odominguez7/Jerome7">GitHub</a> &middot;
    <a href="https://discord.gg/5AZP8DbEJm">Discord</a>
  </div>
</div>

</body>
</html>"""
    return HTMLResponse(content=html)
