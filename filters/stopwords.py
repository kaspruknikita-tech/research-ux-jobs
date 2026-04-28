"""
Фильтрация вакансий.

Подход: БЕЛЫЙ СПИСОК — вакансия проходит, только если в заголовке
есть хотя бы одно из разрешённых слов. Всё остальное — мусор.
Проще и надёжнее, чем бесконечный список стоп-фраз.
"""

import logging

from langdetect import detect, LangDetectException

logger = logging.getLogger(__name__)

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
    "account manager",
    # Инженеры / другие технические
    "Research Engineer",
    "Reverse Engineer",
    "инженер-исследователь",
    "ux engineer",
    "ui engineer",
    "ux/ui engineer",
    "ui/ux engineer",
    "design engineer",
    "api engineer",
    # Академические / научные исследователи
    "postdoctoral",
    "postdoc",
    "research fellow",
    "research officer",
    "research scientist",
    "data scientist",
    # Финансовые кванты (не UX-исследователи)
    "quant trader",
    "hedge fund",
    "systematic trading",
    # Маркетологи
    "маркетолог",
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

COMPANY_BLACKLIST: set[str] = set()


def _is_allowed_language(vacancy: dict) -> bool:
    text = " ".join(filter(None, [
        vacancy.get("title", ""),
        vacancy.get("snippet", ""),
        vacancy.get("description", ""),
    ]))
    if not text or len(text) < 20:
        return True
    try:
        lang = detect(text)
        # hh.ru возвращает русский текст — пропускаем, Adzuna/прочие — только английский
        return lang in ("en", "ru")
    except LangDetectException:
        return True


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
            break
    else:
        logger.debug("Не прошёл белый список: %s", vacancy.get("title"))
        return False

    # 3. Язык — только английский
    if not _is_allowed_language(vacancy):
        logger.debug("Не английский язык: %s", vacancy.get("title"))
        return False

    return True
