from __future__ import annotations

_ACTIONS: dict[str, str] = {
    "S": "curated_plus",
    "A": "curated",
    "B": "main",
    "C": "skip",
}

# Score → tier. Прямое отображение, без hard gate по визе/релоку.
# Доступ/виза/бренд уже учтены в score через score_combiner.
_THRESHOLDS: list[tuple[int, str]] = [
    (9, "S"),
    (7, "A"),
    (4, "B"),
    (0, "C"),
]


def map_tier(score: int) -> tuple[str, str]:
    for min_score, tier in _THRESHOLDS:
        if score >= min_score:
            return tier, _ACTIONS[tier]
    return "C", _ACTIONS["C"]
