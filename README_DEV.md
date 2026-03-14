# Jerome 7 — Developer Setup

## Run locally in 3 commands

```bash
pip install -e ".[dev]"
alembic upgrade head
make dev
```

Server runs at `http://localhost:8000`. Health check: `GET /health`.

## Seed data

```bash
make seed
```

Creates 3 sample users with streaks for testing.

## Run tests

```bash
make test
```

## Environment

Copy `.env.example` to `.env` and fill in your `ANTHROPIC_API_KEY`.
