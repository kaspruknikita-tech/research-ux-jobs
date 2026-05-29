from __future__ import annotations

import logging

from .brand_scorer import call_brand_scorer
from .llm_scorer import PROMPT_VERSION, call_llm, call_llm_enrich_only
from .models import PostEnrichment, ScoringInput, ScoringResult
from .pre_filter import check_post_completeness, pre_filter
from .tier_mapper import map_tier
from .validator import validate_llm_output

logger = logging.getLogger(__name__)

_LOCAL_SOURCES = {"hh.ru"}
_COMPLETENESS_THRESHOLD = 1.0


def _clean_company(company: str | None) -> str:
    """Отсекает hirify-плейсхолдер ('%hirify_global%') и любую утечку 'hirify',
    чтобы brand scorer не ресёрчил саму площадку вместо реального работодателя."""
    c = (company or "").strip()
    if not c or "hirify" in c.lower():
        return ""
    return c


def _neutral_brand() -> dict:
    """Бренд неизвестен (компания не определена) — без вызова Perplexity, нулевой boost."""
    return {
        "brand_tag": "Неизвестный",
        "brand_boost": 0,
        "about_company": "",
        "industry": "",
        "scale": "",
        "green_flags": [],
        "red_flags": [],
        "role_fact_check": "",
        "verdict": "",
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

    # Hard gate — blacklist
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
    logger.debug("[SCORER NORMALIZED] vacancy_id=%d score=%s tier_inputs=(visa=%s reloc=%s remote=%s)",
                 vacancy_id, validated.get("score"), validated.get("visa_sponsorship"),
                 validated.get("relocation_support"), validated.get("remote_policy"))

    # Бренд скорим только если компания реально определена. Иначе Perplexity
    # домысливает работодателя из обрывков (раньше так попадал 'hirify.global').
    if inp.company:
        brand_data = call_brand_scorer(inp)
    else:
        logger.info("BRAND: компания не определена (vacancy_id=%d) — пропуск brand scorer", vacancy_id)
        brand_data = _neutral_brand()
    brand_boost = brand_data.get("brand_boost", 0)
    effective_score = max(0, min(10, validated["score"] + brand_boost))
    logger.info("BRAND BOOST: vacancy_id=%d base_score=%d boost=%d effective=%d tag=%s",
                vacancy_id, validated["score"], brand_boost, effective_score, brand_data.get("brand_tag"))

    tier, action = map_tier(
        effective_score,
        validated["visa_sponsorship"],
        validated["relocation_support"],
    )

    enrichment_data = validated.get("post_enrichment") if enrich else None
    post_enrichment = PostEnrichment(**enrichment_data) if enrichment_data else None

    return ScoringResult(
        vacancy_id=vacancy_id,
        tier=tier,
        action=action,
        score=validated["score"],
        score_breakdown=validated.get("score_breakdown") or {},
        visa_sponsorship=validated["visa_sponsorship"],
        relocation_support=validated["relocation_support"],
        remote_policy=validated["remote_policy"],
        salary_min=validated.get("salary_min"),
        salary_max=validated.get("salary_max"),
        salary_currency=validated.get("salary_currency"),
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


__all__ = ["score_vacancy", "PROMPT_VERSION", "ScoringInput", "ScoringResult", "PostEnrichment"]
