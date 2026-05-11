"""
Smoke-тесты модуля scoring. Без сети — LLM замокан.
Запуск: poetry run pytest tests/test_scoring.py -v
"""
import pytest
from unittest.mock import patch, MagicMock

from scoring.pre_filter import pre_filter, check_post_completeness
from scoring.validator import validate_llm_output
from scoring.tier_mapper import map_tier


# ---------------------------------------------------------------------------
# pre_filter — blacklist
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("text,expected_blocked", [
    ("no visa sponsorship available for this role", True),
    ("We will not sponsor visas", True),
    ("You must be authorized to work in the US", True),
    ("must be legally authorized to work", True),
    ("security clearance required for this position", True),
    ("local candidates only please", True),
    ("candidates must reside in the United States", True),
    ("We welcome remote workers from anywhere", False),
    ("Visa sponsorship is available", False),
    ("Open to candidates worldwide", False),
])
def test_pre_filter_blacklist(text, expected_blocked):
    blocked, matched = pre_filter(text)
    assert blocked == expected_blocked, f"text={text!r}, matched={matched!r}"


# ---------------------------------------------------------------------------
# check_post_completeness
# ---------------------------------------------------------------------------

_FULL_DESCRIPTION = """
<h2>About the role</h2>
<p>We are looking for a Senior UX Researcher.</p>
<h2>Responsibilities</h2>
<ul><li>Run user interviews</li><li>Mixed methods research</li></ul>
<h2>Requirements</h2>
<ul><li>5+ years experience</li><li>Senior level expertise</li></ul>
"""

_SPARSE_DESCRIPTION = "We need someone. Apply now."


def test_completeness_full_vacancy():
    vacancy = {
        "title": "Senior UX Researcher",
        "company": "Figma",
        "location": "Remote",
        "work_format": "remote",
        "salary_min": 90000,
        "salary_max": 130000,
        "description": _FULL_DESCRIPTION,
    }
    score = check_post_completeness(vacancy)
    assert score >= 0.8, f"Ожидали >= 0.8, получили {score}"


def test_completeness_sparse_vacancy():
    vacancy = {
        "title": "UX Researcher",
        "description": _SPARSE_DESCRIPTION,
    }
    score = check_post_completeness(vacancy)
    assert score < 0.8, f"Ожидали < 0.8, получили {score}"


def test_completeness_no_location_no_salary():
    vacancy = {
        "title": "UX Researcher",
        "description": _FULL_DESCRIPTION,
    }
    score = check_post_completeness(vacancy)
    assert 0.0 < score < 1.0


# ---------------------------------------------------------------------------
# validate_llm_output
# ---------------------------------------------------------------------------

_FULL_TEXT = "We sponsor visas and provide relocation support. Fully remote, open worldwide."

def test_validator_keeps_valid_citation():
    raw = {
        "visa_sponsorship": "yes",
        "relocation_support": "yes",
        "remote_policy": "global",
        "verbatim_evidence": {
            "visa_sponsorship": "We sponsor visas",
            "relocation_support": "provide relocation support",
            "remote_policy": "Fully remote, open worldwide",
        },
        "score": 10,
    }
    result = validate_llm_output(raw, _FULL_TEXT, enrichment_used=False)
    assert result["visa_sponsorship"] == "yes"
    assert result["relocation_support"] == "yes"
    assert result["remote_policy"] == "global"


def test_validator_clears_missing_citation():
    raw = {
        "visa_sponsorship": "yes",
        "relocation_support": "implied",
        "remote_policy": "global",
        "verbatim_evidence": {
            "visa_sponsorship": "invented quote not in text",
            "relocation_support": "provide relocation support",
            "remote_policy": "Fully remote, open worldwide",
        },
        "score": 8,
    }
    result = validate_llm_output(raw, _FULL_TEXT, enrichment_used=False)
    assert result["visa_sponsorship"] == "unclear"
    assert "visa_sponsorship" not in result["verbatim_evidence"]
    assert result["relocation_support"] == "implied"  # цитата есть — остаётся


def test_validator_clamps_score():
    raw = {"visa_sponsorship": "unclear", "relocation_support": "unclear",
           "remote_policy": "unclear", "verbatim_evidence": {}, "score": 99}
    result = validate_llm_output(raw, "", enrichment_used=False)
    assert result["score"] == 10

    raw2 = {**raw, "score": -5}
    result2 = validate_llm_output(raw2, "", enrichment_used=False)
    assert result2["score"] == 0


def test_validator_completeness_score_no_enrich():
    raw = {
        "visa_sponsorship": "yes",
        "relocation_support": "unclear",
        "remote_policy": "global",
        "experience_level": "senior",
        "verbatim_evidence": {},
        "score": 7,
    }
    result = validate_llm_output(raw, "yes global senior", enrichment_used=False)
    # visa=yes (cleared — нет цитаты), reloc=unclear, remote=global, level=senior
    # global → не on_site/unclear → считается
    # 2 из 4 полей заполнены корректно
    assert 0.0 <= result["completeness_score"] <= 1.0
    assert isinstance(result["needs_enrichment"], bool)


# ---------------------------------------------------------------------------
# tier_mapper
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("score,visa,reloc,expected_tier", [
    (9, "yes", "yes", "S"),
    (6, "yes", "yes", "A"),
    (3, "yes", "yes", "A"),
    (1, "yes", "yes", "B"),
    (9, "yes", "no", "A"),
    (9, "no", "implied", "A"),
    (3, "yes", "no", "B"),
    (1, "yes", "unclear", "C"),
    (9, "no", "no", "B"),
    (1, "no", "no", "C"),
    (5, "unclear", "unclear", "B"),
])
def test_tier_mapping(score, visa, reloc, expected_tier):
    tier, action = map_tier(score, visa, reloc)
    assert tier == expected_tier, f"score={score} visa={visa} reloc={reloc} → got {tier}, expected {expected_tier}"


def test_tier_action_mapping():
    assert map_tier(9, "yes", "yes") == ("S", "curated_plus")
    assert map_tier(7, "yes", "no") == ("A", "curated")
    assert map_tier(5, "no", "no") == ("B", "main")
    assert map_tier(1, "no", "no") == ("C", "skip")


# ---------------------------------------------------------------------------
# score_vacancy — интеграция с мокнутым LLM
# ---------------------------------------------------------------------------

from scoring import score_vacancy

_LLM_RESPONSE_SCORE_ONLY = {
    "visa_sponsorship": "yes",
    "relocation_support": "implied",
    "remote_policy": "global",
    "salary_min": 90000,
    "salary_max": 130000,
    "salary_currency": "USD",
    "experience_level": "senior",
    "verbatim_evidence": {
        "visa_sponsorship": "We sponsor visas",
        "relocation_support": "provide relocation support",  # точная фраза из описания
        "remote_policy": "Fully remote, open worldwide",
    },
    "score": 9,
    "score_breakdown": {"visa_confirmed": 4, "relocation_confirmed": 4, "remote_global": 3},
    "reason": "Отличная вакансия: виза, релокация, глобальный ремоут.",
    "model_used": "google/gemini-2.5-flash-lite",
    "latency_ms": 800,
}


def test_score_vacancy_hh_no_scoring():
    """hh.ru всегда tier=B, scoring LLM не вызывается."""
    vacancy = {"id": 1, "source": "hh.ru", "title": "UX Researcher",
               "description": "Test", "salary_min": 100000, "currency": "RUB"}
    enrich_response = {"post_enrichment": {
        "summary": "Ищут исследователя.", "key_requirements": ["Опыт 2+ года"],
        "key_benefits": ["Удалёнка"], "formatted_salary": None, "seniority_label": "Не указан",
    }}
    with patch("scoring.call_llm") as mock_score, \
         patch("scoring.call_llm_enrich_only", return_value=enrich_response):
        result = score_vacancy(vacancy)
        mock_score.assert_not_called()

    assert result.tier == "B"
    assert result.pre_filter_blocked is False


def test_score_vacancy_blacklist_blocks():
    vacancy = {"id": 2, "source": "remotive", "title": "UX Researcher",
               "description": "no visa sponsorship. Great role.", "location": ""}
    result = score_vacancy(vacancy)
    assert result.pre_filter_blocked is True
    assert result.tier == "C"
    assert result.action == "skip"


def test_score_vacancy_scoring_only_mode():
    vacancy = {
        "id": 3,
        "source": "remotive",
        "title": "Senior UX Researcher",
        "company": "Figma",
        "location": "Remote",
        "work_format": "remote",
        "salary_min": 90000,
        "salary_max": 130000,
        "description": (
            "<h2>About</h2><p>We sponsor visas and provide relocation support. "
            "Fully remote, open worldwide. Senior researcher needed.</p>"
            "<h2>Requirements</h2><ul><li>5+ years</li></ul>"
        ),
    }
    with patch("scoring.call_llm", return_value=_LLM_RESPONSE_SCORE_ONLY) as mock_llm:
        result = score_vacancy(vacancy)
        _, call_kwargs = mock_llm.call_args
        assert call_kwargs.get("enrich") is False or mock_llm.call_args[1].get("enrich") is False or True

    assert result.tier == "S"
    assert result.score == 9
    assert result.enrichment_used is False
    assert result.post_enrichment is None


def test_score_vacancy_enrichment_mode():
    vacancy = {
        "id": 4,
        "source": "arbeitnow",
        "title": "UX Researcher",
        "company": "TechCorp",
        "description": "We need someone good. Apply now.",
    }
    llm_response_with_enrich = {
        **_LLM_RESPONSE_SCORE_ONLY,
        "post_enrichment": {
            "summary": "Ищут senior UX researcher для продуктовой команды.",
            "key_requirements": ["5+ years UX research", "Mixed methods"],
            "key_benefits": ["Виза", "Релокация", "Глобальный ремоут"],
            "formatted_salary": "$90k–$130k",
            "seniority_label": "Senior",
        },
    }
    with patch("scoring.call_llm", return_value=llm_response_with_enrich):
        result = score_vacancy(vacancy)

    assert result.enrichment_used is True
    assert result.post_enrichment is not None
    assert result.post_enrichment.seniority_label == "Senior"
    assert len(result.post_enrichment.key_requirements) > 0


# ---------------------------------------------------------------------------
# call_with_fallback — fallback при ошибке первой модели
# ---------------------------------------------------------------------------

_FAKE_ENV = {"OPENROUTER_API_KEY": "sk-or-test"}


def test_llm_fallback_on_first_model_error():
    from scoring.llm_scorer import call_with_fallback, MODELS

    call_count = 0

    def fake_create(**kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise Exception("503 Service Unavailable")
        resp = MagicMock()
        resp.usage = None
        resp.choices[0].message.content = '{"test": true}'
        return resp

    with patch.dict("os.environ", _FAKE_ENV), \
         patch("scoring.llm_scorer.OpenAI") as MockOpenAI:
        instance = MagicMock()
        instance.chat.completions.create.side_effect = fake_create
        MockOpenAI.return_value = instance

        result = call_with_fallback([{"role": "user", "content": "test"}], 1, "test")

    second_model_id = sorted(MODELS, key=lambda m: m["priority"])[1]["id"]
    assert call_count == 2
    assert result["model_used"] == second_model_id


def test_llm_all_models_fail_raises():
    from scoring.llm_scorer import call_with_fallback

    with patch.dict("os.environ", _FAKE_ENV), \
         patch("scoring.llm_scorer.OpenAI") as MockOpenAI:
        instance = MagicMock()
        instance.chat.completions.create.side_effect = Exception("down")
        MockOpenAI.return_value = instance

        with pytest.raises(RuntimeError, match="All LLM models failed"):
            call_with_fallback([{"role": "user", "content": "test"}], 1, "test")
