"""
Обработчики Telegram-бота.
handle_moderation — реагирует на нажатия кнопок ✅/❌ в чате модерации.
"""

import logging

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

import config
import database
from bot.templates import format_ru, format_global

logger = logging.getLogger(__name__)


def _get_channel_id(channel: str) -> str:
    return config.TELEGRAM_CHANNEL_RU if channel == "ru" else config.TELEGRAM_CHANNEL_GLOBAL


def _format(vacancy: dict) -> str:
    return format_ru(vacancy) if vacancy.get("channel") == "ru" else format_global(vacancy)


async def handle_moderation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает нажатие кнопки Опубликовать / Отклонить."""
    query = update.callback_query
    await query.answer()

    parts = query.data.split(":")
    action = parts[0]
    vacancy_id = int(parts[1])
    actor = query.from_user.first_name or "модератор"

    vacancy = database.get_vacancy_by_id(vacancy_id)
    if not vacancy:
        await query.edit_message_reply_markup(reply_markup=None)
        return

    if action == "approve":
        channel_id = _get_channel_id(vacancy["channel"])
        try:
            await context.bot.send_message(
                chat_id=channel_id,
                text=_format(vacancy),
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True,
            )
            database.mark_posted(vacancy_id)
            # Убираем кнопки и добавляем статус отдельным сообщением
            await query.edit_message_reply_markup(reply_markup=None)
            await query.message.reply_text(f"✅ Опубликовано — {actor}")
            logger.info("Опубликована вакансия id=%s (%s)", vacancy_id, actor)
        except Exception:
            logger.exception("Ошибка публикации вакансии id=%s", vacancy_id)
            await query.answer("Ошибка при публикации — проверь логи", show_alert=True)

    elif action == "reject":
        database.mark_rejected(vacancy_id)
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text(f"❌ Отклонено — {actor}")
        logger.info("Отклонена вакансия id=%s (%s)", vacancy_id, actor)
