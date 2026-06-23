from __future__ import annotations

import logging

from .brand_scorer import call_brand_scorer
from .llm_scorer import PROMPT_VERSION, call_llm, call_llm_enrich_only
from .models import PostEnrichment, ScoringInput, ScoringResult
from .pre_filter import check_post_completeness, pre_filter
from .score_combiner import combine_score
from .tier_mapper import map_tier
from .validator import validate_llm_output

logger = logging.getLogger(__name__)

_LOCAL_SOURCES = {"hh.ru"}
_COMPLETENESS_THRESHOLD = 1.0

# Опциональный кэш бренда по компании. Подключается на старте приложения
# (см. bot_app.py::main → enable_brand_cache). В тестах/preview не задан —
# кэш выключен, поведение как раньше.
brand_cache_get = None  # Callable[[str], dict | None]
brand_cache_put = None  # Callable[[str, dict], None]

# Опциональный lookup визовых спонсоров по компании. Подключается на старте
# (bot_app.py::main → enable_visa_lookup). В тестах/preview не задан — выключен.
visa_lookup = None  # Callable[[str], dict | None]


def enable_brand_cache(get, put) -> None:
    """Подключает БД-кэш бренда. get(company)->dict|None, put(company, data)->None."""
    global brand_cache_get, brand_cache_put
    brand_cache_get = get
    brand_cache_put = put


def enable_visa_lookup(fn) -> None:
    """Подключает проверку визового спонсора. fn(company)->{display,source}|None."""
    global visa_lookup
    visa_lookup = fn


def _scored_brand(inp: ScoringInput) -> dict:
    """Брендовый скоринг с кэшем по компании. Hit → пропуск дорогого вызова Perplexity.
    Кэш необязателен: если не подключён, всегда зовёт call_brand_scorer."""
    if brand_cache_get is not None:
        try:
            cached = brand_cache_get(inp.company)
        except Exception as exc:
            logger.warning("BRAND cache get failed company=%r error=%s", inp.company, exc)
            cached = None
        if cached:
            logger.info(
                "BRAND: cache hit company=%r tag=%s (пропуск Perplexity, vacancy_id=%d)",
                inp.company, cached.get("brand_tag"), inp.vacancy_id,
            )
            return {**cached, "cached": True}

    data = call_brand_scorer(inp)
    # Не кэшируем неуспешный fallback (error) — иначе зафиксируем нейтральный бренд.
    if brand_cache_put is not None and not data.get("error"):
        try:
            brand_cache_put(inp.company, data)
        except Exception as exc:
            logger.warning("BRAND cache put failed company=%r error=%s", inp.company, exc)
    return data


def _clean_company(company: str | None) -> str:
    """Отсекает hirify-плейсхолдер ('%hirify_global%') и любую утечку 'hirify',
    чтобы brand scorer не ресёрчил саму площадку вместо реального работодателя."""
    c = (company or "").strip()
    if not c or "hirify" in c.lower():
        return ""
    return c


def _neutral_brand() -> dict:
    """Бренд неизвестен (компания не определена) — без вызова Perplexity."""
    return {
        "brand_tag": "Неизвестный",
        "brand_boost": 0,
        "industry": "",
        "scale": "",
        "summary": "",
        "model_used": "",
        "latency_ms": 0,
    }


def _make_inp(vacancy: dict, vacancy_id: int) -> ScoringInput:
    return ScoringInput(
        vacancy_id=vacancy_id,
        title=vacancy.get("title", ""),
        company=_clean_company(vacancy.get("company")),
        description=vacancy.get("description", ""),
        location=vacancy.get("location"),
        work_format=vacancy.get("work_format"),
        salary_min=vacancy.get("salary_min"),
        salary_max=vacancy.get("salary_max"),
        currency=vacancy.get("currency"),
        is_ru=vacancy.get("channel") == "ru",
    )


def _score_local(vacancy: dict, vacancy_id: int) -> ScoringResult:
    """Для hh.ru: только досборка поста если неполный, без скоринга."""
    regex_score = check_post_completeness(vacancy)
    enrich = regex_score < _COMPLETENESS_THRESHOLD
    post_enrichment = None

    model_used = ""
    latency_ms = 0
    if enrich:
        inp = _make_inp(vacancy, vacancy_id)
        raw = call_llm_enrich_only(inp)
        model_used = raw.get("model_used", "")
        latency_ms = raw.get("latency_ms", 0)
        enrichment_data = raw.get("post_enrichment")
        if enrichment_data:
            post_enrichment = PostEnrichment(**enrichment_data)

    return ScoringResult(
        vacancy_id=vacancy_id,
        tier="B",
        action="main",
        score=0,
        score_breakdown={},
        visa_sponsorship="unclear",
        relocation_support="unclear",
        remote_policy="unclear",
        salary_min=vacancy.get("salary_min"),
        salary_max=vacancy.get("salary_max"),
        salary_currency=vacancy.get("currency"),
        experience_level="unclear",
        verbatim_evidence={},
        pre_filter_blocked=False,
        regex_completeness_score=regex_score,
        enrichment_used=enrich,
        completeness_score=1.0 if not enrich else 0.0,
        needs_enrichment=False,
        post_enrichment=post_enrichment,
        reason="",
        model_used=model_used,
        latency_ms=latency_ms,
    )


def score_vacancy(vacancy: dict) -> ScoringResult:
    vacancy_id: int = vacancy["id"]

    if vacancy.get("source") in _LOCAL_SOURCES:
        return _score_local(vacancy, vacancy_id)

    full_text = " ".join(filter(None, [
        vacancy.get("title", ""),
        vacancy.get("description", ""),
        vacancy.get("location", ""),
    ]))

    blocked, matched = pre_filter(full_text)
    if blocked:
        return ScoringResult(
            vacancy_id=vacancy_id,
            tier="C",
            action="skip",
            score=0,
            score_breakdown={},
            visa_sponsorship="unclear",
            relocation_support="unclear",
            remote_policy="unclear",
            salary_min=None,
            salary_max=None,
            salary_currency=None,
            experience_level="unclear",
            verbatim_evidence={},
            pre_filter_blocked=True,
            regex_completeness_score=0.0,
            enrichment_used=False,
            completeness_score=0.0,
            needs_enrichment=False,
            post_enrichment=None,
            reason=f"Заблокировано pre-filter: «{matched}»",
        )

    regex_score = check_post_completeness(vacancy)
    enrich = regex_score < _COMPLETENESS_THRESHOLD

    inp = _make_inp(vacancy, vacancy_id)
    raw = call_llm(inp, enrich=enrich)
    validated = validate_llm_output(raw, full_text, enrichment_used=enrich)

    if inp.company:
        brand_data = _scored_brand(inp)
    else:
        logger.info("BRAND: компания не определена (vacancy_id=%d) — пропуск brand scorer", vacancy_id)
        brand_data = _neutral_brand()

    # Зарплата — только из структурных полей парсера (джоб-борд), не из LLM.
    salary_disclosed = inp.salary_min is not None or inp.salary_max is not None

    visa_listed = False
    if visa_lookup is not None and inp.company:
        try:
            visa_listed = visa_lookup(inp.company) is not None
        except Exception as exc:
            logger.warning("VISA lookup failed company=%r error=%s", inp.company, exc)

    score, breakdown = combine_score(
        visa=validated["visa_sponsorship"],
        reloc=validated["relocation_support"],
        remote=validated["remote_policy"],
        brand_tag=brand_data.get("brand_tag"),
        salary_disclosed=salary_disclosed,
        experience_level=validated["experience_level"],
        research_maturity=validated["research_maturity"],
        vague_jd=validated["vague_jd"],
        visa_listed=visa_listed,
    )

    tier, action = map_tier(score)

    logger.info(
        "SCORE: vacancy_id=%d score=%d tier=%s breakdown=%s brand=%s",
        vacancy_id, score, tier, breakdown, brand_data.get("brand_tag"),
    )

    enrichment_data = validated.get("post_enrichment") if enrich else None
    post_enrichment = PostEnrichment(**enrichment_data) if enrichment_data else None

    return ScoringResult(
        vacancy_id=vacancy_id,
        tier=tier,
        action=action,
        score=score,
        score_breakdown=breakdown,
        visa_sponsorship=validated["visa_sponsorship"],
        relocation_support=validated["relocation_support"],
        remote_policy=validated["remote_policy"],
        salary_min=inp.salary_min,
        salary_max=inp.salary_max,
        salary_currency=inp.currency,
        experience_level=validated.get("experience_level", "unclear"),
        verbatim_evidence=validated.get("verbatim_evidence") or {},
        pre_filter_blocked=False,
        regex_completeness_score=regex_score,
        enrichment_used=enrich,
        completeness_score=validated["completeness_score"],
        needs_enrichment=validated["needs_enrichment"],
        post_enrichment=post_enrichment,
        reason=validated.get("reason", ""),
        model_used=raw.get("model_used", ""),
        latency_ms=raw.get("latency_ms", 0),
        brand_data=brand_data,
    )


__all__ = ["score_vacancy", "enable_brand_cache", "enable_visa_lookup", "PROMPT_VERSION", "ScoringInput", "ScoringResult", "PostEnrichment"]
