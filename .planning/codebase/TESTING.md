# Testing

_Last mapped: 2026-05-14_

## Framework

- **pytest** ^8.2
- **unittest.mock** — `patch`, `MagicMock` for LLM mocking
- Run: `poetry run pytest tests/test_scoring.py -v`

## Test Files

| File | Scope | Count |
|---|---|---|
| `tests/test_scoring.py` | Scoring pipeline (unit, no network) | 49 tests |
| `tests/smoke_test.py` | Basic smoke checks | (small) |
| `test_score.py` (root) | Ad-hoc manual scoring test | Not in pytest |
| `preview_score.py` (root) | Manual score preview script | Not in pytest |
| `preview_post.py` (root) | Manual post format preview | Not in pytest |

## Test Coverage Areas (`test_scoring.py`)

### pre_filter (blacklist)
- 10 parametrized cases for `pre_filter()` — blacklist patterns and negatives

### check_post_completeness
- Full vacancy → high completeness score
- Sparse description → low score

### validate_llm_output (validator)
- Valid output → pass-through
- `None` input → defaults applied
- Incomplete JSON (missing fields) → defaults
- Wrong field names → defaults
- Score out of range → clamped to 0–10
- Invalid enum values → normalized to "unclear"
- `reason` as wrong type (dict) → converted to str
- `verbatim_evidence` as non-dict → replaced with `{}`

### map_tier
- Score/visa/reloc combinations → expected tier + action
- Edge cases: score=0, all "no", all "yes"

### score_vacancy (integration, LLM mocked)
- Happy path: LLM returns valid JSON → ScoringResult created
- Pre-filter blocked: tier=C, action=skip, no LLM call
- **7 failure-mode parametrized cases** (mocked bad LLM responses):
  - Returns `null` JSON
  - Returns JSON array
  - Returns empty dict `{}`
  - Returns dict with wrong field names
  - Returns invalid enum values
  - Returns score out of range
  - Raises exception (all models fail)

## Mocking Strategy

All LLM calls mocked via `patch("scoring.llm_scorer.call_with_fallback")`:

```python
with patch("scoring.llm_scorer.call_with_fallback") as mock_llm:
    mock_llm.return_value = {...}
    result = score_vacancy(vacancy)
```

No real network calls in test suite. Database calls not tested (no test DB).

## What's NOT Tested

- Parser HTTP calls (no mocked responses for parsers)
- Database functions (no test database)
- Bot/Telegram API interactions (no bot mocking)
- Google Sheets export
- End-to-end pipeline (scheduler.run_cycle)
- Telegram channel parsing (Telethon)

## Running Tests

```bash
poetry run pytest tests/test_scoring.py -v          # all scoring tests
poetry run pytest tests/test_scoring.py -k "tier"   # filter by name
poetry run pytest tests/ -v                          # all tests
```
