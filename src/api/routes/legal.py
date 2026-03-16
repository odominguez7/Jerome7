"""GET /privacy and /terms — legal pages."""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()

_HEAD = """<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="theme-color" content="#0d1117">
<link rel="icon" type="image/svg+xml" href="/static/favicon.svg">
<link rel="manifest" href="/static/manifest.json">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&display=swap">
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: #0d1117; color: #c9d1d9; font-family: 'JetBrains Mono', monospace; padding: 40px 20px; line-height: 1.7; }
  .container { max-width: 700px; margin: 0 auto; }
  h1 { color: #E85D04; margin-bottom: 24px; font-size: 1.8rem; }
  h2 { color: #E85D04; margin: 32px 0 12px; font-size: 1.1rem; }
  p, li { font-size: 0.85rem; color: #8b949e; margin-bottom: 12px; }
  ul { padding-left: 20px; }
  a { color: #E85D04; text-decoration: none; }
  .back { display: inline-block; margin-bottom: 24px; font-size: 0.8rem; }
</style>"""


@router.get("/privacy", response_class=HTMLResponse)
async def privacy_policy():
    return HTMLResponse(content=f"""<!DOCTYPE html>
<html lang="en"><head>
<title>Jerome7 | Privacy Policy</title>
{_HEAD}
</head><body>
<div class="container">
<a href="/" class="back">&larr; Back to Jerome7</a>
<h1>Privacy Policy</h1>
<p>Last updated: March 15, 2026</p>

<h2>What We Collect</h2>
<p>When you sign up, we collect:</p>
<ul>
<li><strong>Name</strong>: to personalize your Jerome# identity</li>
<li><strong>Goal</strong>: to tailor your wellness experience</li>
<li><strong>Timezone</strong>: auto-detected from your browser for country mapping</li>
<li><strong>Session data</strong>: completion timestamps and streak counts</li>
</ul>
<p>We do <strong>not</strong> collect email addresses (unless you provide one), passwords, payment info, health data, or location coordinates.</p>

<h2>How We Use It</h2>
<ul>
<li>Generate your Jerome# identity</li>
<li>Track your streak and session history</li>
<li>Show community stats (total Jeromes, countries represented)</li>
<li>Display your country on the global globe</li>
</ul>

<h2>What We Don't Do</h2>
<ul>
<li>We never sell your data</li>
<li>We never share your data with advertisers</li>
<li>We don't use tracking cookies or third-party analytics that identify you</li>
<li>We use privacy-friendly analytics (page views only, no personal data)</li>
</ul>

<h2>Data Storage</h2>
<p>Data is stored on Railway (PostgreSQL) with encrypted connections. Session audio is generated ephemerally and not stored.</p>

<h2>Your Rights</h2>
<p>You can request deletion of your data at any time by contacting us. We will remove all records associated with your Jerome# within 7 days.</p>

<h2>Contact</h2>
<p>Email: <a href="mailto:omar@jerome7.com">omar@jerome7.com</a></p>
<p>GitHub: <a href="https://github.com/odominguez7/Jerome7">github.com/odominguez7/Jerome7</a></p>
</div>
</body></html>""")


@router.get("/terms", response_class=HTMLResponse)
async def terms_of_service():
    return HTMLResponse(content=f"""<!DOCTYPE html>
<html lang="en"><head>
<title>Jerome7 | Terms of Service</title>
{_HEAD}
</head><body>
<div class="container">
<a href="/" class="back">&larr; Back to Jerome7</a>
<h1>Terms of Service</h1>
<p>Last updated: March 15, 2026</p>

<h2>The Short Version</h2>
<p>Jerome7 is a free, open-source wellness tool. Use it, share it, breathe with it. Don't abuse it.</p>

<h2>What Jerome7 Is</h2>
<p>Jerome7 provides daily 7-minute guided wellness sessions including breathwork, meditation, reflection, and preparation. It is <strong>not</strong> medical advice, therapy, or a substitute for professional healthcare.</p>

<h2>Your Account</h2>
<ul>
<li>You receive a Jerome# identity upon signup</li>
<li>You are responsible for any activity under your Jerome#</li>
<li>Don't create fake accounts or spam the system</li>
</ul>

<h2>Content</h2>
<p>Sessions are AI-generated daily by Google Gemini and narrated by ElevenLabs. Content varies each day and is the same for every user globally.</p>

<h2>Open Source</h2>
<p>Jerome7 is licensed under Apache 2.0. You can view, fork, and contribute to the source code on <a href="https://github.com/odominguez7/Jerome7">GitHub</a>.</p>

<h2>Limitations</h2>
<ul>
<li>Jerome7 is provided "as is" with no warranty</li>
<li>We may modify or discontinue features at any time</li>
<li>We are not liable for any damages arising from use of the service</li>
</ul>

<h2>Contact</h2>
<p>Email: <a href="mailto:omar@jerome7.com">omar@jerome7.com</a></p>
</div>
</body></html>""")
