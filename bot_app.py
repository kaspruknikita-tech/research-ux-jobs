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
from zoneinfo import ZoneInfo

from apscheduler.schedulers.background import BackgroundScheduler
from telegram.error import Conflict
from telegram.ext import Application, CallbackQueryHandler, MessageHandler, filters

import config
import database
import scoring
from bot.alerts import check_balances, daily_report, money_report, send_alert
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


def night_probe_cycle() -> None:
    """Ночной авто-харвест ATS-токенов по именам компаний из свежих вакансий."""
    try:
        from tools.ats_night_probe import run_night_probe
        found = run_night_probe(since_hours=24)
        total = sum(len(v) for v in found.values())
        if total:
            logger.info("Ночной probe: найдено %d новых ATS-токенов", total)
    except Exception:
        logger.exception("Ошибка ночного probe ATS-токенов")


def weekly_globalwork_cycle() -> None:
    """Еженедельный харвест ATS-токенов из globalwork.ai."""
    try:
        from tools.discover_ats_from_globalwork import run_discovery
        added = run_discovery()
        total = sum(len(v) for v in added.values())
        if total:
            logger.info("Globalwork discovery: найдено %d новых ATS-токенов", total)
    except Exception:
        logger.exception("Ошибка еженедельного globalwork discovery")


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
    # Кэш брендового скоринга по компании: повтор компании не зовёт Perplexity заново.
    scoring.enable_brand_cache(database.get_brand_cache, database.save_brand_cache)
    # Курируемый список визовых спонсоров: матч даёт +2 к score и подсветку в карточке.
    scoring.enable_visa_lookup(database.is_visa_sponsor)

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
    # Дневная сводка парсеров за прошедший день
    scheduler.add_job(
        daily_report,
        "cron",
        hour=config.DAILY_REPORT_HOUR,
        minute=0,
        id="daily_report",
        max_instances=1,
    )
    # Ночной probe ATS-токенов по именам компаний за день (03:30 МСК)
    scheduler.add_job(
        night_probe_cycle,
        "cron",
        hour=3,
        minute=30,
        id="night_probe",
        max_instances=1,
    )
    # Еженедельный харвест ATS-токенов из globalwork (воскресенье 04:00 МСК)
    scheduler.add_job(
        weekly_globalwork_cycle,
        "cron",
        day_of_week="sun",
        hour=4,
        minute=0,
        id="weekly_globalwork",
        max_instances=1,
    )
    # Проверка балансов OpenRouter / Railway (алерт при падении ниже порога)
    scheduler.add_job(
        check_balances,
        "interval",
        minutes=config.BALANCE_CHECK_INTERVAL_MINUTES,
        id="balance_check",
        max_instances=1,
    )
    # Ежедневная денежная сводка: остаток + траты
    scheduler.add_job(
        money_report,
        "cron",
        hour=config.DAILY_REPORT_HOUR,
        minute=5,
        id="money_report",
        max_instances=1,
    )
    # Разовая сводка за вчера сегодня в 15:00 МСК (исключение, удалить после)
    _oneshot = datetime(2026, 6, 9, 15, 0, tzinfo=ZoneInfo("Europe/Moscow"))
    if _oneshot > datetime.now(ZoneInfo("Europe/Moscow")):
        scheduler.add_job(
            daily_report,
            "date",
            run_date=_oneshot,
            id="daily_report_oneshot",
            misfire_grace_time=3600,
        )
        scheduler.add_job(
            money_report,
            "date",
            run_date=_oneshot,
            id="money_report_oneshot",
            misfire_grace_time=3600,
        )
    scheduler.start()
    logger.info("Планировщик запущен: каждые 2 часа с 10:00 до 21:00 МСК")

    async def on_error(update, context) -> None:
        if isinstance(context.error, Conflict):
            logger.error("Конфликт: запущен другой экземпляр бота. Завершаем процесс.")
            scheduler.shutdown(wait=False)
            logging.shutdown()
            # os._exit вместо sys.exit: внутри async error-handler PTB
            # SystemExit перехватывается event-loop'ом и процесс гаснет с кодом 0
            # (Railway видит "Completed" и не рестартит). os._exit даёт реальный
            # код 1 → срабатывает restartPolicyType=ON_FAILURE.
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
