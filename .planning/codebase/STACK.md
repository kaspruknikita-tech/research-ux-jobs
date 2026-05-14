# Stack

_Last mapped: 2026-05-14_

## Language & Runtime

- **Python 3.12** — primary language
- **Poetry** — dependency management and packaging (`pyproject.toml`)
- Runtime entrypoint: `bot_app.py` (production), `main.py` (scheduler-only mode)

## Core Frameworks & Libraries

| Library | Version | Purpose |
|---|---|---|
| `python-telegram-bot` | ^21.3 | Telegram bot (async, callback query handling) |
| `APScheduler` | ^3.10 | Background job scheduling (cron + interval) |
| `telethon` | ^1.36 | Telegram client for channel parsing (MTProto) |
| `requests` | ^2.32 | HTTP calls to external job APIs |
| `beautifulsoup4` | >=4.12 | HTML parsing for job descriptions |
| `pydantic` | >=2.0 | Data models, validation (ScoringResult, PostEnrichment) |
| `openai` | >=1.0 | OpenRouter LLM calls (scoring + enrichment) |
| `psycopg2-binary` | ^2.9 | PostgreSQL driver |
| `gspread` | ^6.2.1 | Google Sheets export |
| `python-dotenv` | ^1.0 | `.env` file loading |
| `langdetect` | ^1.0.9 | Language detection (used in filters) |

## Dev Dependencies

- `ruff` ^0.5 — linter
- `pytest` ^8.2 — test framework

## Configuration

- All secrets/settings loaded from `.env` via `config.py`
- `config.validate()` checks required vars at startup
- Key env vars: `DATABASE_URL`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_MODERATION_CHAT`, `TELEGRAM_CHANNEL_RU`, `TELEGRAM_CHANNEL_GLOBAL`, `OPENROUTER_API_KEY`, `GOOGLE_SHEET_ID`, `GOOGLE_CREDENTIALS_JSON`

## Deployment

- **Railway** — production platform
- **Docker** — `Dockerfile` uses `python:3.12-slim`, Poetry installs main deps only
- `railway.json` — `startCommand: python bot_app.py`, restart on failure, max 5 retries
- `nixpacks.toml` — alternative build config (fallback)
- `Procfile` — `web: python bot_app.py`
