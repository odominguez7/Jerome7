# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in Jerome7, please report it responsibly.

**Do not open a public issue.**

Email **omar.dominguez7@gmail.com** with:

- Description of the vulnerability
- Steps to reproduce
- Impact assessment

You will receive a response within 48 hours. We will work with you to understand and fix the issue before any public disclosure.

## Supported Versions

| Version | Supported |
|---|---|
| Latest `main` | Yes |
| Older commits | No |

## Scope

The following are in scope:

- [jerome7.com](https://jerome7.com) (production API)
- Authentication and token handling
- Data exposure or injection
- Rate limiting bypasses

Out of scope:

- Social engineering
- Denial of service
- Issues in third-party dependencies (report upstream)

## Security Practices

- All secrets are loaded from environment variables, never hardcoded
- HMAC-SHA256 signed tokens for email verification and unsubscribe
- Bearer token auth with 90-day expiry
- Rate limiting on all public endpoints
- Bot protection (honeypot + timing checks) on signup
- CSP, HSTS, X-Frame-Options, and other security headers in production
- Input validation via Pydantic with strict constraints
