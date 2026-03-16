"""Shared <head> meta tags for all HTML pages — OG, favicon, PWA, analytics."""

# Plausible analytics — privacy-friendly, no cookies, GDPR compliant
_PLAUSIBLE = """<script async src="https://plausible.io/js/pa-Ar14FrKY9n2naAlU6cYFy.js"></script>
<script>window.plausible=window.plausible||function(){(plausible.q=plausible.q||[]).push(arguments)},plausible.init=plausible.init||function(i){plausible.o=i||{}};plausible.init()</script>"""


def head_meta(
    title: str = "Jerome7 — 7 minutes. Show up.",
    description: str = "Daily 7-minute guided wellness for builders. Breathwork, meditation, reflection. Free forever.",
    url: str = "https://jerome7.com",
    og_type: str = "website",
) -> str:
    """Return HTML meta tags to inject after <head><meta charset> block."""
    return f"""<meta name="theme-color" content="#0d1117">
<link rel="icon" type="image/svg+xml" href="/static/favicon.svg">
<link rel="apple-touch-icon" href="/static/favicon.svg">
<link rel="manifest" href="/static/manifest.json">
<link rel="canonical" href="{url}">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{description}">
<meta property="og:type" content="{og_type}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="https://jerome7.com/static/og-image.svg">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{title}">
<meta name="twitter:description" content="{description}">
<meta name="twitter:image" content="https://jerome7.com/static/og-image.svg">
<meta name="twitter:site" content="@Jerome7app">
{_PLAUSIBLE}"""
