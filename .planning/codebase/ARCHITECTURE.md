# Architecture

_Last mapped: 2026-05-14_

## Pattern

**Pipeline + Scheduler** — A scheduled pipeline fetches, filters, scores, and stores vacancies. A separate async Telegram bot loop handles moderation interactions. The two processes run concurrently within one container via `bot_app.py`.

## Layers

```
┌──────────────────────────────────────────────────────────────┐
│                        bot_app.py                            │
│  BackgroundScheduler (APScheduler) + TG bot (ptb async)      │
├────────────────────┬─────────────────────────────────────────┤
│  scheduler.py      │  bot/moderator.py                        │
│  (parse cycle)     │  (send to moderation)                    │
├────────────────────┴─────────────────────────────────────────┤
│  parsers/          filters/         scoring/                  │
│  (fetch raw)       (whitelist/dedup) (LLM scoring)            │
├──────────────────────────────────────────────────────────────┤
│  database.py (PostgreSQL)    exporters/sheets.py (GSheets)   │
└──────────────────────────────────────────────────────────────┘
```

## Data Flow

```
1. APScheduler triggers full_cycle() every 2h (10:00–21:00 MSK)
   │
2. scheduler.run_cycle()
   ├── For each parser in ACTIVE_PARSERS:
   │   ├── parser.run() → fetch() + prepare() → list[dict]
   │   ├── is_duplicate(v) → skip if seen (hash / external_id / title+company)
   │   ├── apply_filters(v) → whitelist check + language detect
   │   │   └── if rejected: insert as 'rejected', add to Google Sheets Rejected
   │   ├── [adzuna only] _enrich_adzuna(v) → scrape full description
   │   ├── database.insert_vacancy(v) → returns new_id
   │   └── score_vacancy(v) → LLM scoring → database.save_vacancy_score()
   │
3. send_new_vacancies_to_moderation()
   ├── get_new_vacancies() from DB (status='new')
   ├── _get_or_score(v) → load from vacancy_scores or re-score
   ├── format_ru/format_global(v, enrichment) → HTML text
   ├── _scoring_footer(result) → tier/score/evidence footer
   └── sendMessage to MODERATION_CHAT with inline keyboard
   │
4. Moderator presses button → handle_moderation()
   ├── approve → send_message to channel → mark_posted()
   └── reject  → mark_rejected()
```

## Key Abstractions

- **`BaseParser`** (`parsers/base.py`) — ABC. All parsers implement `fetch() → list[dict]`. `run()` wraps fetch + prepare + error handling.
- **`ScoringResult`** / **`PostEnrichment`** (`scoring/models.py`) — Pydantic models. `ScoringResult` flows from scorer through DB through moderator.
- **`score_vacancy()`** (`scoring/__init__.py`) — orchestrates pre-filter → completeness check → LLM call → validation → tier mapping.
- **`format_ru/format_global()`** (`bot/templates.py`) — HTML post builder with section parsing + enrichment fallback.

## Entry Points

| File | Role |
|---|---|
| `bot_app.py` | Production: scheduler + bot polling |
| `main.py` | Dev/debug: scheduler only, `--once`, `--init-db` |
| `scheduler.py` | `run_cycle()` — the core pipeline function |

## Concurrency Model

- `APScheduler` runs `full_cycle()` in a background thread (non-blocking)
- `python-telegram-bot` runs its own event loop for bot polling
- Both share the same process — no interprocess communication
- Database is the only shared state; each DB function opens/closes its own connection (no connection pool)
