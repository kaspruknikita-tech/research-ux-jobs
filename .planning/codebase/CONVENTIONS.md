# Conventions

_Last mapped: 2026-05-14_

## Code Style

- **Formatter/Linter:** `ruff` (configured in `pyproject.toml`)
- Type hints used throughout — `str | None`, `list[dict]`, `int | None`
- `from __future__ import annotations` in scoring modules
- Docstrings: module-level and public functions; single-line preferred
- No inline comments unless explaining non-obvious behavior

## Error Handling

- **Parsers:** `run()` in `BaseParser` wraps `fetch()` in try/except — parser failure returns empty list, never crashes the cycle
- **Scheduler:** each vacancy is processed independently; LLM failure logs warning and skips scoring (vacancy still saved)
- **Moderator:** `send_to_moderation()` returns `bool`, catches all exceptions; bot continues with next vacancy
- **Database:** each function opens/closes its own connection; `UniqueViolation` returns `None` (not an exception)
- **LLM fallback:** `call_with_fallback()` tries models in priority order; only raises `RuntimeError` if ALL fail
- **DB migration fallback:** `save_vacancy_score()` catches column-not-found and retries without `post_enrichment` column

## Logging

- All modules use `logging.getLogger(__name__)`
- `logging.basicConfig` configured in `bot_app.py` and `main.py` at startup
- `LOG_LEVEL` env var controls verbosity (default `INFO`)
- DEBUG logs added for LLM input/output (marked `# DEBUG: remove before release`)
- `httpx` logger set to WARNING to suppress token-containing URLs

## Config Access Pattern

```python
import config
config.TELEGRAM_BOT_TOKEN  # accessed as module attributes
```

No dependency injection — config is a global module read once at import time.

## Database Pattern

Each `database.py` function:
1. Opens a new connection (`_get_connection()`)
2. Does its work with a cursor
3. Commits (on write) or just reads
4. Closes connection in `finally` block

No connection pool — suitable for low-frequency scheduled workloads.

## Parser Pattern

```python
class MyParser(BaseParser):
    source_name = "mysite"
    channel = "global"

    def fetch(self) -> list[dict]:
        # return list of dicts with: title, company, url, description, ...
        return [...]
```

`BaseParser.run()` handles: prepare (hash, source, channel, status, parsed_at) + exception wrapping.

## Telegram Message Format

- `parse_mode="HTML"` everywhere
- `disable_web_page_preview=True` everywhere
- Rate limit: 3.5s delay between messages

## Async vs Sync Boundary

- `bot/handlers.py`, `bot/poster.py` — async (python-telegram-bot uses asyncio)
- `bot/moderator.py` — sync (uses `requests` directly, called from APScheduler thread)
- `scheduler.py` — sync (run in background thread by APScheduler)
- `database.py` — sync only (psycopg2)
- Async code never calls sync DB directly from ptb handlers — all DB access is in sync contexts
