"""
Отправка вакансий в чат модерации и публикация одобренных в каналы.
Использует Telegram Bot API напрямую через requests (без asyncio).
"""

import time
import logging

import requests

import config
import database
from bot.templates import format_ru, format_global

logger = logging.getLogger(__name__)

# Задержка между сообщениями — чтобы не словить rate limit Telegram
_SEND_DELAY = 0.5


def _api(method: str, **kwargs) -> dict:
    """Вызов Telegram Bot API. Возвращает тело ответа или бросает исключение."""
    url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/{method}"
    resp = requests.post(url, json=kwargs, timeout=10)
    data = resp.json()
    if not data.get("ok"):
        raise RuntimeError(f"Telegram API error [{method}]: {data.get('description')}")
    return data


def _format(vacancy: dict) -> str:
    if vacancy.get("channel") == "ru":
        return format_ru(vacancy)
    return format_global(vacancy)


def _keyboard(vacancy_id: int, channel: str) -> dict:
    return {
        "inline_keyboard": [[
            {"text": "✅ Опубликовать", "callback_data": f"approve:{vacancy_id}:{channel}"},
            {"text": "❌ Отклонить",    "callback_data": f"reject:{vacancy_id}"},
        ]]
    }


def send_to_moderation(vacancy: dict) -> bool:
    """Отправляет одну вакансию в чат модерации с кнопками. True = успешно."""
    try:
        _api(
            "sendMessage",
            chat_id=config.TELEGRAM_MODERATION_CHAT,
            text=_format(vacancy),
            parse_mode="HTML",
            reply_markup=_keyboard(vacancy["id"], vacancy["channel"]),
            disable_web_page_preview=True,
        )
        database.mark_pending(vacancy["id"])
        return True
    except Exception:
        logger.exception("Не удалось отправить вакансию %s на модерацию", vacancy.get("id"))
        return False


def send_new_vacancies_to_moderation() -> int:
    """Берёт все 'new' вакансии из БД и отправляет в чат модерации.
    Возвращает количество отправленных."""
    if not config.TELEGRAM_BOT_TOKEN or not config.TELEGRAM_MODERATION_CHAT:
        logger.warning("Telegram не настроен, пропускаем отправку на модерацию")
        return 0

    vacancies = database.get_new_vacancies()
    if not vacancies:
        return 0

    sent = 0
    for v in vacancies:
        if send_to_moderation(v):
            sent += 1
        time.sleep(_SEND_DELAY)

    logger.info("Отправлено на модерацию: %d вакансий", sent)
    return sent
