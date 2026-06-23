"""
Планировщик: парсинг, фильтрация, БД, Google Sheets.
Постинг в Telegram пока отключён.
"""

import logging
from datetime import datetime, timezone

import requests
from apscheduler.schedulers.blocking import BlockingScheduler
from bs4 import BeautifulSoup

import config
import database
from scoring import score_vacancy, PROMPT_VERSION
from parsers.adzuna import AdzunaParser
from parsers.hh import HHParser
from parsers.telegram import TelegramChannelParser
from parsers.arbeitnow import ArbeitnowParser
from parsers.himalayas import HimalayasParser
from parsers.remotive import RemotiveParser
from parsers.remoteok import RemoteOKParser
from parsers.weworkremotely import WeWorkRemotelyParser
from parsers.workingnomads import WorkingNomadsParser
from parsers.greenhouse import GreenhouseParser
from parsers.ashby import AshbyParser
from parsers.lever import LeverParser
from parsers.wantapply import WantapplyParser
from parsers.hirify import HirifyParser
from parsers.designproject import DesignprojectParser
from parsers.userinterviews import UserInterviewsParser
from parsers.bebee import BebeeParser
from parsers.uxwork import UxworkParser
from parsers.fourdayjob import FourDayJobParser
from parsers.cryptojobslist import CryptoJobsListParser
from parsers.jobgether import JobgetherParser
from filters.stopwords import apply_filters
from filters.dedup import is_duplicate
from exporters.sheets import export_to_sheets, export_rejected_to_sheets
from bot.alerts import check_balances, daily_report

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
    RemoteOKParser(),
    WeWorkRemotelyParser(),
    WorkingNomadsParser(),
    GreenhouseParser(),
    AshbyParser(),
    LeverParser(),
    WantapplyParser(),
    HirifyParser(),
    DesignprojectParser(),
    UserInterviewsParser(),
    BebeeParser(),
    FourDayJobParser(),
    UxworkParser(),
    CryptoJobsListParser(),
    JobgetherParser(),
]


_ADZUNA_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}

_ADZUNA_SELECTORS = [
    "[class*='adp-body']",
    "[data-testid='ad-body']",
    "[class*='job-description']",
    "[class*='jobdescription']",
    "section.description",
]


def _enrich_adzuna(v: dict) -> None:
    url = v.get("url", "")
    if not url:
        return
    try:
        resp = requests.get(url, headers=_ADZUNA_HEADERS, timeout=10, allow_redirects=True)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        for selector in _ADZUNA_SELECTORS:
            el = soup.select_one(selector)
            if el and len(el.get_text(strip=True)) > len(v.get("description", "") or ""):
                v["description"] = str(el)
                logger.debug("[adzuna] Обогащено описание: %s", url)
                return
    except Exception:
        logger.debug("[adzuna] Не удалось получить полное описание: %s", url)


def run_cycle() -> dict:
    logger.info("=== Начало цикла: %s ===", datetime.now().strftime("%Y-%m-%d %H:%M"))

    run_ts = datetime.now(timezone.utc)
    total_parsed = 0
    total_saved = 0
    total_filtered = 0
    saved_vacancies = []
    rejected_vacancies = []
    stats: dict[str, dict] = {}

    for parser in ACTIVE_PARSERS:
        logger.info("Запускаем парсер: %s", parser.source_name)
        # run() = fetch() + prepare() (hash, source, channel, status, parsed_at) + обработка ошибок
        vacancies = parser.run()
        total_parsed += len(vacancies)
        logger.info("Получено: %d вакансий", len(vacancies))

        s = stats.setdefault(
            parser.source_name,
            {"parsed": 0, "duplicates": 0, "passed": 0, "rejected": 0},
        )
        s["parsed"] += len(vacancies)

        for v in vacancies:
            if is_duplicate(v):
                s["duplicates"] += 1
                continue

            if not apply_filters(v):
                total_filtered += 1
                v["status"] = "rejected"
                # Экспортируем в Rejected только если реально записали в БД.
                # Дубликат вернёт None — его уже экспортировали в прошлом цикле.
                if database.insert_vacancy(v):
                    s["rejected"] += 1
                    rejected_vacancies.append(v)
                continue

            if v.get("source") == "adzuna":
                _enrich_adzuna(v)

            new_id = database.insert_vacancy(v)
            if new_id:
                v["id"] = new_id
                try:
                    result = score_vacancy(v)
                    database.save_vacancy_score(result, PROMPT_VERSION)
                    v["_scoring"] = result.model_dump()
                except Exception:
                    logger.warning("Скоринг не удался для вакансии %s", new_id)
                s["passed"] += 1
                total_saved += 1
                saved_vacancies.append(v)

    try:
        database.record_parser_runs(run_ts, stats)
    except Exception:
        logger.exception("Не удалось записать статистику цикла в parser_runs")

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

    if rejected_vacancies:
        logger.info("Экспортируем %d отклонённых в Rejected...", len(rejected_vacancies))
        try:
            export_rejected_to_sheets(rejected_vacancies)
        except Exception:
            logger.exception("Экспорт rejected в Sheets упал, продолжаем")

    logger.info("=== Цикл завершён ===\n")
    return {"parsed": total_parsed, "saved": total_saved}


def start_scheduler() -> None:
    database.init_db()

    logger.info("Первый запуск цикла...")
    run_cycle()

    logger.info("Проверка балансов при старте...")
    check_balances()

    scheduler = BlockingScheduler(timezone="Europe/Moscow")
    scheduler.add_job(
        run_cycle,
        "interval",
        minutes=config.PARSE_INTERVAL_MINUTES,
        id="main_cycle",
        max_instances=1,
    )
    scheduler.add_job(
        check_balances,
        "interval",
        minutes=config.BALANCE_CHECK_INTERVAL_MINUTES,
        id="balance_check",
        max_instances=1,
    )
    scheduler.add_job(
        daily_report,
        "cron",
        hour=config.DAILY_REPORT_HOUR,
        minute=0,
        id="daily_report",
        max_instances=1,
    )
    logger.info(
        "Шедулер запущен. Интервал парсинга: %d мин. Проверка баланса: %d мин. "
        "Дневная сводка: %02d:00 МСК. Ctrl+C для остановки.",
        config.PARSE_INTERVAL_MINUTES,
        config.BALANCE_CHECK_INTERVAL_MINUTES,
        config.DAILY_REPORT_HOUR,
    )

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Шедулер остановлен")


if __name__ == "__main__":
    start_scheduler()
