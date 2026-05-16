"""
Парсер wantapply.com.
Next.js SSR — данные в window.__NEXT_DATA__, fallback на DOM.
Целевые страницы: /jobs/ux-researcher, /jobs/customer-support
"""

import logging

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

from parsers.base import BaseParser

logger = logging.getLogger(__name__)

TARGET_URLS = [
    "https://wantapply.com/jobs/ux-researcher",
    "https://wantapply.com/jobs/customer-support",
]

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


def _jobs_from_next_data(page) -> list[dict]:
    try:
        data = page.evaluate("() => window.__NEXT_DATA__ || null")
        if not data:
            return []
        props = data.get("props", {}).get("pageProps", {})
        for key in ("jobs", "vacancies", "listings", "items", "data", "results"):
            if isinstance(props.get(key), list):
                return props[key]
    except Exception:
        pass
    return []


def _get_description(page, url: str) -> str:
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=20_000)
        for sel in ("[class*='description']", "[class*='job-detail']", "[class*='content']", "article", "main"):
            el = page.query_selector(sel)
            if el:
                text = el.inner_text().strip()
                if len(text) > 100:
                    return text
    except Exception:
        logger.debug("[wantapply] Не удалось загрузить detail: %s", url)
    return ""


def _parse_card_dom(card, seen: set) -> dict | None:
    title = ""
    for sel in ("h2", "h3", "[class*='title']", "[class*='position']"):
        el = card.query_selector(sel)
        if el:
            title = el.inner_text().strip()
            break
    if not title or not _is_relevant(title):
        return None

    link = card.query_selector("a")
    url = link.get_attribute("href") if link else ""
    if url and not url.startswith("http"):
        url = "https://wantapply.com" + url
    if not url or url in seen:
        return None

    company = ""
    for sel in ("[class*='company']", "[class*='employer']", "[class*='org']"):
        el = card.query_selector(sel)
        if el:
            company = el.inner_text().strip()
            break

    location = ""
    for sel in ("[class*='location']", "[class*='geo']", "[class*='city']"):
        el = card.query_selector(sel)
        if el:
            location = el.inner_text().strip()
            break

    return {
        "external_id": "",
        "title": title,
        "company": company,
        "salary_min": None,
        "salary_max": None,
        "currency": None,
        "location": location,
        "work_format": None,
        "url": url,
        "description": "",
    }


class WantapplyParser(BaseParser):
    source_name = "wantapply"
    channel = "global"

    def fetch(self) -> list[dict]:
        result = []
        seen: set[str] = set()

        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            ctx = browser.new_context(user_agent=_UA)
            list_page = ctx.new_page()
            list_page.set_default_timeout(30_000)
            detail_page = ctx.new_page()

            for target_url in TARGET_URLS:
                logger.info("[wantapply] Загружаем: %s", target_url)
                try:
                    list_page.goto(target_url, wait_until="networkidle", timeout=30_000)
                except PWTimeout:
                    logger.warning("[wantapply] Таймаут: %s", target_url)
                    continue
                except Exception:
                    logger.exception("[wantapply] Ошибка загрузки: %s", target_url)
                    continue

                raw_jobs = _jobs_from_next_data(list_page)
                if raw_jobs:
                    logger.info("[wantapply] __NEXT_DATA__: %d записей с %s", len(raw_jobs), target_url)
                    for job in raw_jobs:
                        title = job.get("title") or job.get("position") or job.get("name") or ""
                        if not _is_relevant(title):
                            continue
                        url = job.get("url") or job.get("link") or job.get("href") or ""
                        if not url or url in seen:
                            continue
                        if not url.startswith("http"):
                            url = "https://wantapply.com" + url
                        seen.add(url)
                        desc = _get_description(detail_page, url)
                        result.append({
                            "external_id": str(job.get("id") or job.get("slug") or ""),
                            "title": title,
                            "company": job.get("company") or job.get("company_name") or "",
                            "salary_min": None,
                            "salary_max": None,
                            "currency": None,
                            "location": job.get("location") or "",
                            "work_format": None,
                            "url": url,
                            "description": desc,
                        })
                else:
                    logger.info("[wantapply] DOM fallback для %s", target_url)
                    cards = list_page.query_selector_all(
                        "article, [data-testid*='job'], [class*='job-card'], [class*='job_card'], li[class*='job']"
                    )
                    logger.info("[wantapply] Карточек в DOM: %d", len(cards))
                    for card in cards:
                        try:
                            parsed = _parse_card_dom(card, seen)
                            if not parsed:
                                continue
                            seen.add(parsed["url"])
                            parsed["description"] = _get_description(detail_page, parsed["url"])
                            result.append(parsed)
                        except Exception:
                            logger.debug("[wantapply] Ошибка разбора карточки", exc_info=True)

            browser.close()

        logger.info("[wantapply] Итого: %d вакансий", len(result))
        return result
