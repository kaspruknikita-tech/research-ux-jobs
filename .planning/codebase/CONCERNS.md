# Concerns

_Last mapped: 2026-05-14_

## Technical Debt

### No Connection Pool
`database.py` opens a new connection per call. Fine at current load (scheduled every 2h), but will be a bottleneck if call frequency increases significantly.

### Manual Migrations
SQL migration files in `migrations/` must be applied manually. No migration runner. Version tracking only via naming convention. `save_vacancy_score()` has a defensive fallback for unapplied migration 003 — this is a workaround, not a solution.

### Two Entry Points for Same Process
`main.py` (scheduler-only) and `bot_app.py` (scheduler + bot) serve different purposes but share `scheduler.run_cycle()`. The `Procfile` and `railway.json` both point to `bot_app.py` — the `main.py` entry is for local dev only, but this is not obvious.

### Duplicate Code: `handlers.py` vs `moderator.py`
Both have a `_format()` function. `handlers.py:_format()` calls `format_ru/format_global` without enrichment. `moderator.py:_format()` passes enrichment. When a vacancy is approved in `handlers.py`, the published post does NOT include AI enrichment — only the moderation preview has it.

### `scheduler.py.save`
A stale backup file in the root directory. Should be deleted.

### `data/vacancies.db`
SQLite remnant from early development. Not used in production (PostgreSQL). Should be excluded from deployments.

### Nested `research-ux-jobs/` directory
A duplicate subtree exists at `research-ux-jobs/research-ux-jobs/`. Likely a git checkout artifact. Confusing and wastes disk space.

## Security

### `google_credentials.json` in repo root
Service account credentials file committed to the repository. Should be in `.gitignore` and loaded from `GOOGLE_CREDENTIALS_JSON` env var only (the code already supports this path — the file fallback is the risk).

### Telegram session string in env
`TG_SESSION_STRING` gives full MTProto session access. Compromise of this env var = full Telegram account access. Treat as a high-value secret.

### No input sanitization on vacancy fields
Vacancy fields (title, company, description) come from external APIs and are inserted into HTML messages. `bot/templates.py` uses `html.escape()` on some fields but not consistently throughout all code paths.

## Performance

### Adzuna HTML scraping per vacancy
`_enrich_adzuna()` in `scheduler.py` makes one HTTP request per Adzuna vacancy to scrape the full description. No caching. If Adzuna returns many vacancies, this blocks the cycle.

### LLM calls are synchronous and serial
Each vacancy that needs scoring makes 1–2 LLM calls serially. Timeout is 15s with 3 model fallbacks = up to 45s per vacancy. With many new vacancies, cycles can be slow.

### No rate limit handling for external APIs
Parsers don't have retry logic or rate limit backoff. HTTP 429 responses will surface as logged exceptions and skip the parser.

## Fragile Areas

### `bot/templates.py` section parser
`_parse_sections()` relies on HTML structure from external job boards. Different boards format differently. Keyword matching uses exact strings that can break with typographic quotes (partially fixed with `_normalize()`) or language variations.

### LLM prompt versioning
`PROMPT_VERSION = "v1"` is a constant. If the prompt changes significantly, old scores in the DB are compared with new scoring logic using the same version string. No mechanism to invalidate old scores.

### Telegram callback_query timeout
Callbacks expire after 60 seconds. `handle_moderation()` handles this gracefully, but moderation buttons on old posts (before redeploy) appear active but fail silently — users see no feedback until the show_alert message.

### APScheduler `max_instances=1`
The scheduled job won't run if a previous cycle is still running. If a cycle takes > 2h (unlikely but possible with many LLM calls), the next cycle is skipped silently.

## Missing Features / TODOs

- No mechanism to re-score vacancies with updated prompt
- No monitoring/metrics beyond operational alerts
- No pagination support in some parsers (may miss vacancies if source returns >1 page)
- `evals/` directory present but eval runner is not wired into CI
- Debug log statements in `scoring/` are marked `# DEBUG: remove before release` but still present
