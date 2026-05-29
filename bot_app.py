"""
Точка входа для продакшна.
Запускает планировщик в фоне и Telegram-бот для модерации.

Цикл каждые N минут:
  1. Парсим hh.ru → фильтруем → сохраняем в БД
  2. Новые вакансии отправляем в чат модерации с кнопками

Бот слушает нажатия кнопок:
  ✅ Опубликовать → постит в канал, помечает 'posted'
  ❌ Отклонить    → помечает 'rejected'
"""

import logging
import os
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from telegram.error import Conflict
from telegram.ext import Application, CallbackQueryHandler, MessageHandler, filters

import config
import database
from bot.alerts import send_alert
from bot.handlers import handle_edit_reply, handle_moderation
from bot.moderator import publish_due_scheduled, send_new_vacancies_to_moderation
from scheduler import run_cycle

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
# httpx логирует полные URL с токеном — отключаем
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


def full_cycle() -> None:
    """Полный цикл: парсинг + отправка новых вакансий на модерацию."""
    try:
        stats = run_cycle()
        sent = send_new_vacancies_to_moderation()
        parsed = stats.get("parsed", 0)
        saved = stats.get("saved", 0)
        if parsed == 0:
            send_alert("Внимание: парсер вернул 0 вакансий")
        else:
            send_alert(f"Цикл завершён: найдено {parsed}, новых {saved}, отправлено на модерацию {sent}")
    except Exception as e:
        logger.exception("Ошибка цикла")
        send_alert(f"Ошибка цикла: {type(e).__name__}: {e}")


def scheduled_publish_cycle() -> None:
    """Публикует вакансии у которых наступило scheduled_at."""
    try:
        published = publish_due_scheduled()
        if published:
            logger.info("Опубликовано запланированных вакансий: %d", published)
    except Exception:
        logger.exception("Ошибка публикации запланированных вакансий")


def main() -> None:
    database.init_db()

    # Фоновый планировщик — не блокирует основной поток
    scheduler = BackgroundScheduler(timezone="Europe/Moscow")

    # Первый цикл через 60 секунд — даём время умереть старому экземпляру
    # чтобы не получить 403 от hh.ru при двух OAuth-запросах подряд с одного IP
    scheduler.add_job(
        full_cycle,
        "date",
        run_date=datetime.now(timezone.utc) + timedelta(seconds=60),
        id="first_cycle",
    )
    # Каждые 2 часа с 10 до 21 по Москве
    scheduler.add_job(
        full_cycle,
        "cron",
        hour="10-20/2",
        minute=0,
        id="main_cycle",
        max_instances=1,
    )
    scheduler.add_job(
        scheduled_publish_cycle,
        "interval",
        minutes=5,
        id="scheduled_publish",
        max_instances=1,
    )
    scheduler.start()
    logger.info("Планировщик запущен: каждые 2 часа с 10:00 до 21:00 МСК")

    async def on_error(update, context) -> None:
        if isinstance(context.error, Conflict):
            logger.error("Конфликт: запущен другой экземпляр бота. Завершаем процесс.")
            scheduler.shutdown(wait=False)
            os._exit(1)
        logger.exception("Необработанная ошибка бота", exc_info=context.error)

    # Telegram-бот стартует сразу — не ждёт окончания первого цикла
    app = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()
    app.add_error_handler(on_error)
    app.add_handler(CallbackQueryHandler(handle_moderation))

    def _chat_filter(chat_id_str: str):
        if not chat_id_str:
            return None
        return (
            filters.Chat(int(chat_id_str)) if chat_id_str.lstrip("-").isdigit()
            else filters.Chat(username=chat_id_str.lstrip("@"))
        )

    ru_filter = _chat_filter(config.TELEGRAM_MODERATION_CHAT_RU)
    gl_filter = _chat_filter(config.TELEGRAM_MODERATION_CHAT_GLOBAL)
    if ru_filter and gl_filter and config.TELEGRAM_MODERATION_CHAT_RU != config.TELEGRAM_MODERATION_CHAT_GLOBAL:
        mod_filter = ru_filter | gl_filter
    elif ru_filter:
        mod_filter = ru_filter
    elif gl_filter:
        mod_filter = gl_filter
    else:
        mod_filter = filters.Chat([])

    app.add_handler(MessageHandler(
        filters.TEXT & filters.REPLY & mod_filter,
        handle_edit_reply,
    ))
    logger.info("Бот запущен, слушаем кнопки модерации...")
    app.run_polling(
        allowed_updates=["callback_query", "message"],
        drop_pending_updates=True,
        bootstrap_retries=5,
    )


if __name__ == "__main__":
    main()
