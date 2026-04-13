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
from datetime import datetime, timedelta

from apscheduler.schedulers.background import BackgroundScheduler
from telegram.ext import Application, CallbackQueryHandler

import config
import database
from bot.handlers import handle_moderation
from bot.moderator import send_new_vacancies_to_moderation
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
    run_cycle()
    send_new_vacancies_to_moderation()


def main() -> None:
    database.init_db()

    # Фоновый планировщик — не блокирует основной поток
    scheduler = BackgroundScheduler(timezone="Europe/Moscow")

    # Первый цикл через 5 секунд после старта — бот уже слушает кнопки
    scheduler.add_job(
        full_cycle,
        "date",
        run_date=datetime.now() + timedelta(seconds=5),
        id="first_cycle",
    )
    # Затем каждые N минут
    scheduler.add_job(
        full_cycle,
        "interval",
        minutes=config.PARSE_INTERVAL_MINUTES,
        id="main_cycle",
        max_instances=1,
    )
    scheduler.start()
    logger.info("Планировщик запущен, интервал: %d мин", config.PARSE_INTERVAL_MINUTES)

    # Telegram-бот стартует сразу — не ждёт окончания первого цикла
    app = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CallbackQueryHandler(handle_moderation))
    logger.info("Бот запущен, слушаем кнопки модерации...")
    app.run_polling(allowed_updates=["callback_query"])


if __name__ == "__main__":
    main()
