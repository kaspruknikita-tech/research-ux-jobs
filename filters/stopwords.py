"""
Фильтрация вакансий.

Подход: БЕЛЫЙ СПИСОК — вакансия проходит, только если в заголовке
есть хотя бы одно из разрешённых слов. Всё остальное — мусор.
Проще и надёжнее, чем бесконечный список стоп-фраз.
"""

import logging

logger = logging.getLogger(__name__)

# Если ХОТЯ БЫ ОДНО из этих слов есть в заголовке (без учёта регистра) —
# вакансия проходит. Иначе — отсеивается.
WHITELIST = [
    "исследователь",
    "исследования",
    "researcher",
    "research",
    "ux",
    "cx",
    "insight",
    "insights",
    "usability",
    "юзабилити",
]

# Даже если слово из белого списка есть — эти фразы всё равно мусор.
# Держим этот список КОРОТКИМ — только то, что реально проскакивает.
BLACKLIST = [
    "инженер-исследователь",
    "научный сотрудник",
    "пеший исследователь",
    "ИТ-ресечер",
    "IT-Researcher",
    "UX/UI-дизайнер",
    "UX/UI дизайнер",
    "UI/UX дизайнер",
    "UX-дизайнер",
    "UX редактор",
    "UX-редактор",
    "Дизайнер UI/UX",
    "Senior UX/UI",
    "Research Engineer",
    "Packaging Specialist",
    "Reverse Engineer",
    "Рекрутер по поиску респондентов",
    "системному моделированию",
    "Агроном",
    "UX/UI Designer",
]

# Чёрный список компаний
COMPANY_BLACKLIST: set[str] = set()


def apply_filters(vacancy: dict) -> bool:
    """True = вакансия прошла фильтр."""
    title = (vacancy.get("title") or "").lower()

    # 1. Чёрный список — проверяем первым
    for phrase in BLACKLIST:
        if phrase.lower() in title:
            logger.debug("Чёрный список '%s': %s", phrase, vacancy.get("title"))
            return False

    # 2. Белый список — должно быть хотя бы одно слово
    for word in WHITELIST:
        if word.lower() in title:
            return True

    logger.debug("Не прошёл белый список: %s", vacancy.get("title"))
    return False
