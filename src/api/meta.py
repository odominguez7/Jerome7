"""Shared <head> meta tags for all HTML pages — OG, favicon, PWA, analytics."""

# Plausible analytics -- update script filename if Plausible account changes
# Privacy-friendly, no cookies, GDPR compliant
_PLAUSIBLE = """<script async src="https://plausible.io/js/pa-Ar14FrKY9n2naAlU6cYFy.js"></script>
<script>window.plausible=window.plausible||function(){(plausible.q=plausible.q||[]).push(arguments)},plausible.init=plausible.init||function(i){plausible.o=i||{}};plausible.init()</script>"""


def head_meta(
    title: str = "Jerome7 | 7 minutes. Show up.",
    description: str = "Daily 7-minute guided wellness for builders. Breathwork, meditation, reflection. Personally funded. Open source.",
    url: str = "https://jerome7.com",
    og_type: str = "website",
) -> str:
    """Return HTML meta tags to inject after <head><meta charset> block."""
    return f"""<meta name="theme-color" content="#0d1117">
<link rel="icon" type="image/svg+xml" href="/static/favicon.svg">
<link rel="apple-touch-icon" href="/static/icon-192.png">
<link rel="manifest" href="/static/manifest.json">
<link rel="canonical" href="{url}">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{description}">
<meta property="og:type" content="{og_type}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="https://jerome7.com/static/og-image.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{title}">
<meta name="twitter:description" content="{description}">
<meta name="twitter:image" content="https://jerome7.com/static/og-image.png">
<meta name="twitter:site" content="@Jerome7app">
{_PLAUSIBLE}
<script>if('serviceWorker' in navigator)navigator.serviceWorker.register('/static/sw.js')</script>"""


def nav_html() -> str:
    """Shared fixed nav bar for public pages."""
    return '''<nav style="position:fixed;top:0;left:0;right:0;z-index:1000;display:flex;align-items:center;justify-content:space-between;padding:16px 24px;background:rgba(13,17,23,0.95);backdrop-filter:blur(10px);border-bottom:1px solid #21262d">
  <a href="/" style="color:#e6edf3;text-decoration:none;font-family:'JetBrains Mono',monospace;font-weight:700;font-size:16px;letter-spacing:2px">JEROME7</a>
  <div style="display:flex;gap:20px;align-items:center">
    <a href="/globe" style="color:#8b949e;text-decoration:none;font-family:'JetBrains Mono',monospace;font-size:13px;letter-spacing:1px">GLOBE</a>
    <a href="https://discord.gg/jerome7" target="_blank" rel="noopener noreferrer" style="color:#8b949e;text-decoration:none;font-family:'JetBrains Mono',monospace;font-size:13px;letter-spacing:1px">DISCORD</a>
    <a href="https://github.com/odominguez7/Jerome7" target="_blank" rel="noopener noreferrer" style="color:#8b949e;text-decoration:none;font-family:'JetBrains Mono',monospace;font-size:13px;letter-spacing:1px">GITHUB</a>
    <a href="/timer" style="background:#E85D04;color:white;text-decoration:none;font-family:'JetBrains Mono',monospace;font-size:13px;letter-spacing:1px;padding:8px 16px;border-radius:6px;font-weight:700">START</a>
  </div>
</nav>'''
