from __future__ import annotations

_EVIDENCE_FIELDS = ("visa_sponsorship", "relocation_support", "remote_policy")
_POSITIVE_VALUES = {"yes", "implied"}

# remote_policy: грунтуем только «позитивные» заявки, которые модель склонна
# выдумывать чтобы поднять вакансию. on_site/hybrid — консервативный дефолт от
# локации (цитата не нужна), грунтовка их сносила бы верный штраф за офис.
_REMOTE_NEEDS_QUOTE = {"global", "eu", "us_only"}

# Цитата должна содержать слово по теме поля — иначе модель прикрутила
# нерелевантное предложение (напр. visa=no обоснован цитатой про релокацию).
_FIELD_KEYWORDS = {
    "visa_sponsorship": ("visa", "sponsor", "authoriz", "work permit", "right to work",
                         "immigration", "h-1b", "h1b", "eligible to work", "legally authorized"),
    "relocation_support": ("relocat", "moving expense", "moving cost", "relo package"),
    # для remote: «located in <город>» НЕ ключевое — иначе эхо локации сходит за
    # доказательство формата (как было с «Location: ...» и «Full-time»).
    "remote_policy": ("remote", "hybrid", "on-site", "on site", "onsite", "in-office",
                      "in office", "office", "work from home", "wfh", "worldwide",
                      "anywhere", "distributed"),
}

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
    "research_maturity": False,
    "vague_jd": False,
    "reason": "",
    "verbatim_evidence": {},
}

_VALID_REMOTE_POLICY = {"global", "eu", "us_only", "hybrid", "on_site", "unclear"}
_VALID_SPONSORSHIP = {"yes", "implied", "no", "unclear"}
_VALID_EXPERIENCE = {"junior", "mid", "senior", "lead", "unclear"}

_BOOL_FIELDS = ("research_maturity", "vague_jd")


def _enrich_val(raw: dict, dotpath: str):
    enrich = raw.get("post_enrichment") or {}
    key = dotpath.split(".")[1]
    return enrich.get(key)


def _to_bool(v) -> bool:
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        return v.lower() in ("true", "yes", "1")
    return bool(v)


def validate_llm_output(raw: dict | None, full_text: str, enrichment_used: bool) -> dict:
    """
    - Нормализует None/не-dict входные данные в safe dict
    - Заполняет отсутствующие поля дефолтами
    - Проверяет verbatim-цитаты: если цитата не найдена в тексте → поле в "unclear"
    - Приводит булевы поля к bool
    - Считает completeness_score и выставляет needs_enrichment

    Score НЕ считается здесь — это делает score_combiner поверх извлечённых полей.
    """
    if not isinstance(raw, dict):
        raw = {}

    for key, default in _FIELD_DEFAULTS.items():
        raw.setdefault(key, default)

    if raw["remote_policy"] not in _VALID_REMOTE_POLICY:
        raw["remote_policy"] = "unclear"
    if raw["visa_sponsorship"] not in _VALID_SPONSORSHIP:
        raw["visa_sponsorship"] = "unclear"
    if raw["relocation_support"] not in _VALID_SPONSORSHIP:
        raw["relocation_support"] = "unclear"
    if raw["experience_level"] not in _VALID_EXPERIENCE:
        raw["experience_level"] = "unclear"

    for field in _BOOL_FIELDS:
        raw[field] = _to_bool(raw.get(field))

    if not isinstance(raw["reason"], str):
        raw["reason"] = str(raw["reason"]) if raw["reason"] else ""

    evidence = raw.get("verbatim_evidence") or {}
    if not isinstance(evidence, dict):
        evidence = {}

    for field in _EVIDENCE_FIELDS:
        val = raw.get(field)
        quote = evidence.get(field, "")

        # Качество цитаты: дословно в тексте И по теме поля. Иначе не показываем
        # (ловит эхо локации и мусорные токены вроде «Full-time» в роли remote).
        quote_ok = bool(quote) and quote in full_text
        if quote_ok and field in _FIELD_KEYWORDS:
            ql = quote.lower()
            quote_ok = any(kw in ql for kw in _FIELD_KEYWORDS[field])
        if not quote_ok:
            evidence.pop(field, None)

        # Значение-«доступ» (remote global/eu/us_only, visa/reloc yes/implied)
        # без валидной цитаты → unclear. on_site/hybrid/no — дефолт, цитата не нужна.
        if field == "remote_policy":
            needs_grounding = val in _REMOTE_NEEDS_QUOTE
        else:
            needs_grounding = val in _POSITIVE_VALUES
        if needs_grounding and not quote_ok:
            raw[field] = "unclear"

    raw["verbatim_evidence"] = evidence

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
