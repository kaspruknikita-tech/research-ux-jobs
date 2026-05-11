from __future__ import annotations

_ACTIONS: dict[str, str] = {
    "S": "curated_plus",
    "A": "curated",
    "B": "main",
    "C": "skip",
}

_POSITIVE = {"yes", "implied"}

# tier_table[has_visa][has_reloc] = list of (min_score, tier) descending
_TIER_TABLE = {
    (True, True):   [(8, "S"), (5, "A"), (3, "A"), (0, "B")],
    (True, False):  [(8, "A"), (5, "A"), (3, "B"), (0, "C")],
    (False, True):  [(8, "A"), (5, "A"), (3, "B"), (0, "C")],
    (False, False): [(8, "B"), (5, "B"), (3, "B"), (0, "C")],
}


def map_tier(score: int, visa: str, reloc: str) -> tuple[str, str]:
    key = (visa in _POSITIVE, reloc in _POSITIVE)
    for min_score, tier in _TIER_TABLE[key]:
        if score >= min_score:
            return tier, _ACTIONS[tier]
    return "C", _ACTIONS["C"]
