"""
Отправка вакансий в Telegram-каналы.
Использует python-telegram-bot (async).
"""

import asyncio
import logging

from telegram import Bot
from telegram.constants import ParseMode

import config
import database
from bot.templates import format_ru, format_global

logger = logging.getLogger(__name__)

# Telegram ограничивает: ~20 сообщений в минуту в один чат
DELAY_BETWEEN_POSTS = 3.5  # секунд между постами


def _get_bot() -> Bot:
    return Bot(token=config.TELEGRAM_BOT_TOKEN)


def _get_channel_id(channel: str) -> str:
    if channel == "ru":
        return config.TELEGRAM_CHANNEL_RU
    return config.TELEGRAM_CHANNEL_GLOBAL


def _format(vacancy: dict) -> str:
    if vacancy["channel"] == "ru":
        return format_ru(vacancy)
    return format_global(vacancy)


async def _post_vacancies(channel: str) -> int:
    """Публикует все новые вакансии для канала. Возвращает кол-во опубликованных."""
    bot = _get_bot()
    chat_id = _get_channel_id(channel)
    vacancies = database.get_pending_vacancies(channel)

    if not vacancies:
        logger.info("[poster] Нет новых вакансий для канала '%s'", channel)
        return 0

    posted = 0
    for v in vacancies:
        text = _format(v)
        try:
            await bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True,
            )
            database.mark_posted(v["id"])
            posted += 1
            logger.info("Опубликована: [%s] %s", channel, v["title"])
        except Exception:
            logger.exception("Ошибка при отправке вакансии id=%s", v["id"])

        # Пауза между сообщениями, чтобы не словить лимит
        await asyncio.sleep(DELAY_BETWEEN_POSTS)

    return posted


def post_all() -> dict[str, int]:
    """Синхронная обёртка: публикует вакансии в оба канала.
    Возвращает {"ru": N, "global": M}."""
    results = {}
    for channel in ("ru", "global"):
        count = asyncio.run(_post_vacancies(channel))
        results[channel] = count
    return results
