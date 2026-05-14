# Integrations

_Last mapped: 2026-05-14_

## Telegram

### Bot API (python-telegram-bot, async)
- **Used in:** `bot_app.py`, `bot/handlers.py`, `bot/poster.py`
- Handles: inline keyboard callbacks (✅ Approve / ❌ Reject)
- Sends moderation posts with formatted HTML and reply_markup
- Publishes approved vacancies to channels

### Bot API (requests, sync)
- **Used in:** `bot/moderator.py`
- Sends vacancies to `TELEGRAM_MODERATION_CHAT` via direct HTTP POST
- Delay: 3.5s between sends to avoid rate limits

### Telegram Client (Telethon / MTProto)
- **Used in:** `parsers/telegram.py`
- Parses job posts from source Telegram channels
- Requires: `TG_API_ID`, `TG_API_HASH`, `TG_SESSION_STRING`
- Configured channels: `TG_SOURCE_CHANNELS` (comma-separated), lookback `TG_DAYS_BACK` days

### Alert Chat
- **Used in:** `bot/alerts.py`
- Sends operational alerts to `TELEGRAM_ALERT_CHAT` (separate from moderation)

## External Job APIs

| Parser | Auth | Method | Notes |
|---|---|---|---|
| `parsers/hh.py` | OAuth2 (`HH_CLIENT_ID`, `HH_CLIENT_SECRET`) | REST JSON | Russian jobs, `channel=ru` |
| `parsers/adzuna.py` | App ID + Key | REST JSON | + HTML scraping for full description |
| `parsers/arbeitnow.py` | None | REST JSON | Public API |
| `parsers/himalayas.py` | None | REST JSON | Remote jobs |
| `parsers/remotive.py` | None | REST JSON | Remote jobs |
| `parsers/weworkremotely.py` | None | RSS/HTML | HTML parsing |
| `parsers/workingnomads.py` | None | REST JSON | Remote jobs |
| `parsers/greenhouse.py` | None | REST JSON | Job board API |

## OpenRouter (LLM)

- **Used in:** `scoring/llm_scorer.py`
- Client: `openai.OpenAI` pointed at `https://openrouter.ai/api/v1`
- Auth: `OPENROUTER_API_KEY` env var
- Models with fallback priority:
  1. `google/gemini-2.5-flash-lite` (priority 1)
  2. `mistralai/mistral-small-3.1` (priority 2)
  3. `meta-llama/llama-3.3-70b-instruct:free` (priority 3)
- Timeout: 15s per call
- Response format: `json_object`

## PostgreSQL

- **Provider:** Railway (managed PostgreSQL)
- **Driver:** `psycopg2-binary`
- Connection: `DATABASE_URL` env var (auto-corrects `postgres://` → `postgresql://`)
- Tables: `vacancies`, `vacancy_scores`, `settings`
- Migrations in `migrations/` (SQL files, applied manually)

## Google Sheets

- **Used in:** `exporters/sheets.py`
- Auth: service account via `GOOGLE_CREDENTIALS_JSON` (env) or `google_credentials.json` (file)
- Sheets: `Vacancies` (approved), `Rejected` (filtered-out vacancies)
- Library: `gspread` + `google-auth`
