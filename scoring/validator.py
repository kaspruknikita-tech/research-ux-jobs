from __future__ import annotations

_EVIDENCE_FIELDS = ("visa_sponsorship", "relocation_support", "remote_policy")
_POSITIVE_VALUES = {"yes", "implied"}

_LLM_FIELDS = [
    ("visa_sponsorship", lambda v: v != "unclear"),
    ("relocation_support", lambda v: v != "unclear"),
    ("remote_policy", lambda v: v not in ("unclear", "on_site")),
    ("experience_level", lambda v: v != "unclear"),
]
_ENRICH_FIELDS = [
    ("post_enrichment.summary", lambda v: bool(v)),
    ("post_enrichment.key_requirements", lambda v: bool(v)),
    ("post_enrichment.key_benefits", lambda v: bool(v)),
]

_FIELD_DEFAULTS: dict = {
    "visa_sponsorship": "unclear",
    "relocation_support": "unclear",
    "remote_policy": "unclear",
    "experience_level": "unclear",
    "salary_min": None,
    "salary_max": None,
    "salary_currency": None,
    "score": 0,
    "score_breakdown": {},
    "reason": "",
    "verbatim_evidence": {},
}

_VALID_REMOTE_POLICY = {"global", "eu", "hybrid", "on_site", "unclear"}
_VALID_SPONSORSHIP = {"yes", "implied", "no", "unclear"}
_VALID_EXPERIENCE = {"junior", "mid", "senior", "lead", "unclear"}


def _enrich_val(raw: dict, dotpath: str):
    enrich = raw.get("post_enrichment") or {}
    key = dotpath.split(".")[1]
    return enrich.get(key)


def validate_llm_output(raw: dict | None, full_text: str, enrichment_used: bool) -> dict:
    """
    - Нормализует None/не-dict входные данные в safe dict
    - Заполняет отсутствующие поля дефолтами
    - Проверяет verbatim-цитаты: если цитата не найдена в тексте → поле в "unclear"
    - Клampует score в [0, 10]
    - Считает completeness_score и выставляет needs_enrichment
    """
    if not isinstance(raw, dict):
        raw = {}

    for key, default in _FIELD_DEFAULTS.items():
        raw.setdefault(key, default)

    # Нормализуем enum-поля до допустимых значений
    if raw["remote_policy"] not in _VALID_REMOTE_POLICY:
        raw["remote_policy"] = "unclear"
    if raw["visa_sponsorship"] not in _VALID_SPONSORSHIP:
        raw["visa_sponsorship"] = "unclear"
    if raw["relocation_support"] not in _VALID_SPONSORSHIP:
        raw["relocation_support"] = "unclear"
    if raw["experience_level"] not in _VALID_EXPERIENCE:
        raw["experience_level"] = "unclear"

    # reason должен быть строкой
    if not isinstance(raw["reason"], str):
        raw["reason"] = str(raw["reason"]) if raw["reason"] else ""

    evidence = raw.get("verbatim_evidence") or {}
    if not isinstance(evidence, dict):
        evidence = {}

    for field in _EVIDENCE_FIELDS:
        if raw.get(field) in _POSITIVE_VALUES:
            quote = evidence.get(field, "")
            if not quote or quote not in full_text:
                raw[field] = "unclear"
                evidence.pop(field, None)

    raw["verbatim_evidence"] = evidence
    raw["score"] = max(0, min(10, int(raw.get("score") or 0)))

    filled = sum(1 for field, check in _LLM_FIELDS if check(raw.get(field, "unclear")))
    total = len(_LLM_FIELDS)

    if enrichment_used:
        for dotpath, check in _ENRICH_FIELDS:
            total += 1
            if check(_enrich_val(raw, dotpath)):
                filled += 1

    raw["completeness_score"] = round(filled / total, 2)
    raw["needs_enrichment"] = raw["completeness_score"] < 0.8

    return raw
