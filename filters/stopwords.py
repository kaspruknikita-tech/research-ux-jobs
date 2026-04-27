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
    # Дизайнеры (не исследователи)
    "designer",
    "дизайнер",
    "copywriter",
    "UX редактор",
    "UX-редактор",
    # Менеджеры
    "program manager",
    "project manager",
    "product manager",
    # Инженеры / другие технические
    "Research Engineer",
    "Reverse Engineer",
    "инженер-исследователь",
    "ux engineer",
    "ui engineer",
    "ux/ui engineer",
    "ui/ux engineer",
    # Немецкие вакансии — гендерная нотация DE/AT/CH (все варианты)
    "(m/w/d)",
    "(w/m/d)",
    "(m/f/d)",
    "(f/m/d)",
    "(w|m|d)",
    "(d/w/m)",
    "(x,f,m)",
    "(x,m,f)",
    "w/m/div",
    "(gn)",
    "(all genders)",
    # Немецкие слова (стажировки, Werkstudent и т.п.)
    "werkstudent",
    "praktikum",
    "abschlussarbeit",
    "teamleiter",
    "abteilungsleitung",
    # Финансовые кванты (не UX-исследователи)
    "quant trader",
    "hedge fund",
    "systematic trading",
    # Учёные / другие исследователи не по теме
    "химик",
    # Спам
    "remote work from home market research. ideal for",
    # Прочий мусор
    "научный сотрудник",
    "пеший исследователь",
    "ИТ-ресечер",
    "IT-Researcher",
    "Packaging Specialist",
    "Рекрутер по поиску респондентов",
    "системному моделированию",
    "Агроном",
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
