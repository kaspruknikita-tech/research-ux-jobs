from __future__ import annotations

_POSITIVE = {"yes", "implied"}

# Бренд → очки. Источник — brand_tag от Perplexity (см. brand_scorer.py).
_BRAND_POINTS = {
    "Tier 1": 4,
    "Tier 2": 2,
    "Нишевый": 0,
    "Неизвестный": 0,
}


def _access_points(visa: str, reloc: str, remote: str) -> tuple[int, str]:
    """Доступ — максимум, не сумма. Виза/релок и ремоут взаимозаменяемы.
    Возвращает (баллы, метка_сигнала_для_breakdown)."""
    has_visa = visa in _POSITIVE
    has_reloc = reloc in _POSITIVE

    if remote == "global":
        bonus = 1 if (has_visa or has_reloc) else 0
        label = "remote_global+visa" if bonus else "remote_global"
        return 5 + bonus, label
    if has_visa and has_reloc:
        return 5, "visa+relocation"
    if has_visa:
        return 4, "visa"
    if has_reloc:
        return 4, "relocation"
    if remote == "eu":
        return 3, "remote_eu"
    if remote == "us_only":
        # Для СНГ-аудитории "Remote US" без визы недоступно, но мягче чем on_site
        # (можно искать визу/EAD удалённо). Полный on_site = -3, us_only = -1.
        return -1, "us_only_no_visa"
    if remote == "hybrid":
        return 1, "hybrid"
    if remote == "on_site":
        return -3, "on_site_no_visa"
    return 0, "unclear_access"


def _brand_points(brand_tag: str | None) -> int:
    return _BRAND_POINTS.get(brand_tag or "", 0)


def combine_score(
    *,
    visa: str,
    reloc: str,
    remote: str,
    brand_tag: str | None,
    salary_disclosed: bool,
    experience_level: str,
    research_maturity: bool,
    vague_jd: bool,
    visa_listed: bool = False,
) -> tuple[int, dict[str, int]]:
    """Собирает итоговый score 0-10 и breakdown.

    Логика:
    - Доступ берётся максимумом (ремоут ИЛИ виза — равноценны).
    - Бренд — отдельный блок, реально вытаскивает on-site в B при сильной зп.
    - Качество — мелкие плюсы и vague_jd как минус.
    """
    breakdown: dict[str, int] = {}

    access_pts, access_label = _access_points(visa, reloc, remote)
    if access_pts != 0:
        breakdown[access_label] = access_pts

    brand_pts = _brand_points(brand_tag)
    if brand_pts != 0:
        breakdown[f"brand_{brand_tag}"] = brand_pts

    # Компания в курируемом списке визовых спонсоров (ellis/h1bdata/myvisajobs) —
    # сильный независимый сигнал, что виза реальна. Усиливает доступ-блок.
    if visa_listed:
        breakdown["visa_sponsor_listed"] = 2

    if salary_disclosed:
        breakdown["salary_disclosed"] = 1
    if experience_level in ("mid", "senior", "lead"):
        breakdown["senior_level"] = 1
    if research_maturity:
        breakdown["research_maturity"] = 1
    if vague_jd:
        breakdown["vague_jd"] = -2

    raw = sum(breakdown.values())
    score = max(0, min(10, raw))
    return score, breakdown
