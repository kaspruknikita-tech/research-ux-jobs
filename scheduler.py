"""
Планировщик: парсинг, фильтрация, БД, Google Sheets.
Постинг в Telegram пока отключён.
"""

import logging
from datetime import datetime

from apscheduler.schedulers.blocking import BlockingScheduler

import config
import database
from parsers.adzuna import AdzunaParser
from parsers.hh import HHParser
from parsers.telegram import TelegramChannelParser
from parsers.arbeitnow import ArbeitnowParser
from parsers.himalayas import HimalayasParser
from parsers.remotive import RemotiveParser
from parsers.weworkremotely import WeWorkRemotelyParser
from parsers.workingnomads import WorkingNomadsParser
from filters.stopwords import apply_filters
from filters.dedup import is_duplicate
from exporters.sheets import export_to_sheets

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

ACTIVE_PARSERS = [
    HHParser(),
    AdzunaParser(),
    TelegramChannelParser(),
    ArbeitnowParser(),
    HimalayasParser(),
    RemotiveParser(),
    WeWorkRemotelyParser(),
    WorkingNomadsParser(),
]


def run_cycle() -> dict:
    logger.info("=== Начало цикла: %s ===", datetime.now().strftime("%Y-%m-%d %H:%M"))

    total_parsed = 0
    total_saved = 0
    total_filtered = 0
    saved_vacancies = []

    for parser in ACTIVE_PARSERS:
        logger.info("Запускаем парсер: %s", parser.source_name)
        # run() = fetch() + prepare() (hash, source, channel, status, parsed_at) + обработка ошибок
        vacancies = parser.run()
        total_parsed += len(vacancies)
        logger.info("Получено: %d вакансий", len(vacancies))

        for v in vacancies:
            if is_duplicate(v):
                continue

            if not apply_filters(v):
                total_filtered += 1
                v["status"] = "rejected"
                database.insert_vacancy(v)
                continue

            new_id = database.insert_vacancy(v)
            if new_id:
                total_saved += 1
                saved_vacancies.append(v)

    logger.info(
        "Итого: получено=%d, сохранено=%d, отфильтровано=%d",
        total_parsed, total_saved, total_filtered,
    )

    if saved_vacancies:
        logger.info("Экспортируем %d новых вакансий в Sheets...", len(saved_vacancies))
        try:
            export_to_sheets(saved_vacancies)
        except Exception:
            logger.exception("Экспорт в Sheets упал, продолжаем")

    logger.info("=== Цикл завершён ===\n")
    return {"parsed": total_parsed, "saved": total_saved}


def start_scheduler() -> None:
    database.init_db()

    logger.info("Первый запуск цикла...")
    run_cycle()

    scheduler = BlockingScheduler(timezone="Europe/Moscow")
    scheduler.add_job(
        run_cycle,
        "interval",
        minutes=config.PARSE_INTERVAL_MINUTES,
        id="main_cycle",
        max_instances=1,
    )
    logger.info(
        "Шедулер запущен. Интервал: %d мин. Ctrl+C для остановки.",
        config.PARSE_INTERVAL_MINUTES,
    )

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Шедулер остановлен")


if __name__ == "__main__":
    start_scheduler()
