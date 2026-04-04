"""
Дедупликация вакансий.
Проверяет хэш (title+company+url) по базе. Если уже есть — пропускаем.
"""

import logging

import database

logger = logging.getLogger(__name__)


def is_duplicate(vacancy: dict) -> bool:
    """Возвращает True, если вакансия уже есть в базе."""
    hash_value = vacancy.get("hash", "")
    if not hash_value:
        return False
    exists = database.vacancy_exists(hash_value)
    if exists:
        logger.debug("Дубликат: %s (%s)", vacancy.get("title"), vacancy.get("company"))
    return exists
