# Structure

_Last mapped: 2026-05-14_

## Directory Layout

```
research-ux-jobs/
├── bot_app.py              # Production entrypoint (scheduler + TG bot)
├── main.py                 # Dev entrypoint (scheduler only)
├── scheduler.py            # Core pipeline: parse → filter → score → export
├── config.py               # All env var reading + validation
├── database.py             # PostgreSQL: all DB operations
│
├── parsers/                # Job source parsers
│   ├── base.py             # BaseParser ABC
│   ├── hh.py               # hh.ru (OAuth2, Russian jobs)
│   ├── adzuna.py           # Adzuna (API + HTML scraping)
│   ├── arbeitnow.py        # Arbeitnow (public API)
│   ├── himalayas.py        # Himalayas
│   ├── remotive.py         # Remotive
│   ├── weworkremotely.py   # We Work Remotely
│   ├── workingnomads.py    # Working Nomads
│   ├── greenhouse.py       # Greenhouse job board
│   └── telegram.py         # Telegram channels (Telethon)
│
├── filters/
│   ├── stopwords.py        # Whitelist + blacklist filtering, lang detect
│   └── dedup.py            # Duplicate detection (hash/external_id/title+company)
│
├── scoring/
│   ├── __init__.py         # score_vacancy() orchestrator
│   ├── models.py           # ScoringInput, ScoringResult, PostEnrichment (Pydantic)
│   ├── llm_scorer.py       # OpenRouter LLM calls with fallback, prompt templates
│   ├── pre_filter.py       # Regex blacklist + completeness scoring
│   ├── tier_mapper.py      # Score + visa/reloc → S/A/B/C tier
│   └── validator.py        # LLM output normalization + validation
│
├── bot/
│   ├── templates.py        # HTML post formatting, section parsing
│   ├── moderator.py        # Send to moderation chat (sync, requests)
│   ├── handlers.py         # Telegram callback handler (async, ptb)
│   ├── poster.py           # Post to channels (async, ptb)
│   └── alerts.py           # Operational alerts to alert chat
│
├── exporters/
│   └── sheets.py           # Google Sheets export (vacancies + rejected)
│
├── migrations/             # PostgreSQL migration SQL files (manual apply)
│   ├── 001_vacancy_scores.sql
│   ├── 002_add_model_tracking.sql
│   └── 003_add_post_enrichment.sql
│
├── tests/
│   ├── test_scoring.py     # 49 tests, scoring pipeline (mocked LLM)
│   └── smoke_test.py       # Basic smoke tests
│
├── data/
│   └── vacancies.db        # SQLite (local dev remnant, not used in prod)
│
├── evals/                  # LLM eval runner (scoring quality evaluation)
├── scoring/eval_runner.py  # Eval runner for scoring prompts
│
├── pyproject.toml          # Poetry config + dependencies
├── Dockerfile              # python:3.12-slim, CMD=bot_app.py
├── railway.json            # Railway deploy config
├── nixpacks.toml           # Nixpacks alternative build
└── Procfile                # web: python bot_app.py
```

## Key Locations

| What | Where |
|---|---|
| Add a new parser | `parsers/<name>.py`, add to `ACTIVE_PARSERS` in `scheduler.py` |
| Change whitelist/blacklist | `filters/stopwords.py` |
| Change LLM prompt | `scoring/llm_scorer.py` (_SCORING_INSTRUCTIONS, _ENRICH_INSTRUCTIONS) |
| Change scoring tiers | `scoring/tier_mapper.py` |
| Change post format | `bot/templates.py` |
| Add DB column | Create `migrations/00N_*.sql`, apply manually |
| Change schedule | `bot_app.py` (cron params in `scheduler.add_job`) |

## Naming Conventions

- Python modules: `snake_case.py`
- Classes: `PascalCase` (e.g., `BaseParser`, `ScoringResult`)
- Functions: `snake_case`
- Private functions: `_leading_underscore` (e.g., `_enrich_adzuna`, `_fmt_bullets`)
- Constants: `SCREAMING_SNAKE_CASE` (e.g., `ACTIVE_PARSERS`, `PROMPT_VERSION`)
- Parser `source_name`: matches short domain (`"hh.ru"`, `"adzuna"`, `"remotive"`)
- Parser `channel`: `"ru"` or `"global"`
