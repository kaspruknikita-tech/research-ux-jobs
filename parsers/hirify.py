"""
Парсер hirify.me.
Nuxt.js — перехватываем XHR к api.hirify.me, воспроизводим через requests.
Fallback: DOM-скрапинг через Playwright.
"""

import logging

import requests as req_lib
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

from parsers.base import BaseParser

logger = logging.getLogger(__name__)

BASE_URL = "https://hirify.me"
API_HOST = "api.hirify.me"
MAX_PAGES = 20

TITLE_WHITELIST = [
    "researcher", "research", "ux", "cx", "usability",
    "service designer", "voice of customer", "ux strategist",
    "research ops", "cx analyst", "customer experience",
]

_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


def _is_relevant(title: str) -> bool:
    t = title.lower()
    return any(w in t for w in TITLE_WHITELIST)


def _normalize_job(job: dict) -> dict:
    title = job.get("title") or job.get("name") or job.get("position") or ""
    url = job.get("url") or job.get("link") or ""
    if url and not url.startswith("http"):
        url = "https://hirify.me" + url
    return {
        "external_id": str(job.get("id") or job.get("slug") or ""),
        "title": title,
        "company": job.get("company") or job.get("company_name") or "",
        "salary_min": None,
        "salary_max": None,
        "currency": None,
        "location": job.get("location") or job.get("city") or "",
        "work_format": None,
        "url": url,
        "description": job.get("description") or job.get("body") or "",
    }


def _intercept_and_capture(browser) -> tuple[str, dict] | None:
    """Открывает hirify.me, перехватывает запрос к api.hirify.me."""
    captured: dict = {}
    ctx = browser.new_context(user_agent=_UA)
    page = ctx.new_page()

    def on_request(request):
        if API_HOST in request.url and not captured.get("url"):
            # берём первый подходящий запрос (список вакансий)
            url = request.url
            if any(k in url for k in ("vacanc", "job", "position", "listing")):
                captured["url"] = url
                captured["headers"] = dict(request.headers)
                logger.info("[hirify] Перехвачен API: %s", url)

    page.on("request", on_request)

    try:
        page.goto(BASE_URL, wait_until="networkidle", timeout=30_000)
    except PWTimeout:
        logger.warning("[hirify] Таймаут при перехвате")
    except Exception:
        logger.exception("[hirify] Ошибка при перехвате")

    page.close()
    ctx.close()

    if "url" in captured:
        return captured["url"], captured["headers"]
    return None


def _fetch_via_api(api_url: str, headers: dict) -> list[dict]:
    result = []
    base = api_url.split("?")[0]

    for page_num in range(1, MAX_PAGES + 1):
        try:
            resp = req_lib.get(base, params={"page": page_num}, headers=headers, timeout=15)
            resp.raise_for_status()
            data = resp.json()
        except Exception:
            logger.exception("[hirify] API-запрос упал, страница %d", page_num)
            break

        jobs = []
        if isinstance(data, list):
            jobs = data
        elif isinstance(data, dict):
            for key in ("data", "jobs", "vacancies", "items", "results"):
                if isinstance(data.get(key), list):
                    jobs = data[key]
                    break

        if not jobs:
            break

        for job in jobs:
            title = job.get("title") or job.get("name") or job.get("position") or ""
            if not _is_relevant(title):
                continue
            result.append(_normalize_job(job))

    return result


def _scrape_dom(browser) -> list[dict]:
    result = []
    ctx = browser.new_context(user_agent=_UA)
    page = ctx.new_page()

    try:
        page.goto(BASE_URL, wait_until="networkidle", timeout=30_000)
    except PWTimeout:
        logger.warning("[hirify] DOM: таймаут загрузки")
    except Exception:
        logger.exception("[hirify] DOM: ошибка загрузки")
        page.close()
        ctx.close()
        return result

    cards = page.query_selector_all(
        "article, [class*='vacancy'], [class*='job-card'], [class*='job_card'], li[class*='job']"
    )
    logger.info("[hirify] DOM: найдено карточек %d", len(cards))

    seen: set[str] = set()
    for card in cards:
        try:
            title = ""
            for sel in ("h2", "h3", "[class*='title']", "[class*='position']"):
                el = card.query_selector(sel)
                if el:
                    title = el.inner_text().strip()
                    break
            if not title or not _is_relevant(title):
                continue

            link = card.query_selector("a")
            url = link.get_attribute("href") if link else ""
            if url and not url.startswith("http"):
                url = "https://hirify.me" + url
            if not url or url in seen:
                continue
            seen.add(url)

            company = ""
            for sel in ("[class*='company']", "[class*='employer']"):
                el = card.query_selector(sel)
                if el:
                    company = el.inner_text().strip()
                    break

            result.append({
                "external_id": "",
                "title": title,
                "company": company,
                "salary_min": None,
                "salary_max": None,
                "currency": None,
                "location": "",
                "work_format": None,
                "url": url,
                "description": "",
            })
        except Exception:
            logger.debug("[hirify] Ошибка разбора карточки", exc_info=True)

    page.close()
    ctx.close()
    return result


class HirifyParser(BaseParser):
    source_name = "hirify"
    channel = "global"

    def fetch(self) -> list[dict]:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)

            api_result = _intercept_and_capture(browser)
            if api_result:
                api_url, headers = api_result
                jobs = _fetch_via_api(api_url, headers)
                if jobs:
                    logger.info("[hirify] API-режим: %d вакансий", len(jobs))
                    browser.close()
                    return jobs
                logger.warning("[hirify] API найден, но данных нет — DOM fallback")
            else:
                logger.warning("[hirify] API не перехвачен — DOM fallback")

            jobs = _scrape_dom(browser)
            browser.close()

        logger.info("[hirify] DOM-режим: %d вакансий", len(jobs))
        return jobs
