"""
Парсер hirify.me (DOM-скрапинг через Playwright).
Если заданы HIRIFY_EMAIL/HIRIFY_PASSWORD — логинится для получения названий компаний.
"""

import logging

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

import config
from parsers.base import BaseParser

logger = logging.getLogger(__name__)

BASE_URL = "https://hirify.me"

SEARCH_QUERIES = [
    "ux researcher",
    "user researcher",
    "cx researcher",
    "service designer",
    "usability researcher",
    "research ops",
]

_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


def _login(page) -> bool:
    try:
        page.goto(BASE_URL, wait_until="domcontentloaded", timeout=20_000)
        page.wait_for_timeout(1500)

        login_btn = page.query_selector("a[href*='login'], a[href*='sign'], button:has-text('Войти'), a:has-text('Войти')")
        if login_btn:
            login_btn.click()
            page.wait_for_timeout(2000)

        page.fill("input[type='email']", config.HIRIFY_EMAIL)
        page.fill("input[type='password']", config.HIRIFY_PASSWORD)
        page.click("button[type='submit']")
        page.wait_for_timeout(3000)

        content = page.content().lower()
        logged_in = "войти" not in content or page.query_selector("[class*='avatar'], [class*='user-menu'], [class*='profile']") is not None
        if logged_in:
            logger.info("[hirify] Логин успешен")
        else:
            logger.warning("[hirify] Логин мог не сработать")
        return logged_in
    except Exception:
        logger.exception("[hirify] Ошибка при логине")
        return False


def _get_description(page, url: str) -> str:
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=20_000)
        page.wait_for_timeout(1500)
        for sel in ("[class*='description']", "[class*='vacancy-body']", "[class*='content']", "main"):
            el = page.query_selector(sel)
            if el:
                text = el.inner_text().strip()
                if len(text) > 100:
                    return text
    except Exception:
        logger.debug("[hirify] Не удалось загрузить detail: %s", url)
    return ""


class HirifyParser(BaseParser):
    source_name = "hirify"
    channel = "global"

    def fetch(self) -> list[dict]:
        result = []
        seen: set[str] = set()
        use_auth = bool(config.HIRIFY_EMAIL and config.HIRIFY_PASSWORD)

        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            ctx = browser.new_context(user_agent=_UA)
            list_page = ctx.new_page()
            detail_page = ctx.new_page()

            if use_auth:
                _login(list_page)

            for query in SEARCH_QUERIES:
                search_url = f"{BASE_URL}/?search={query.replace(' ', '+')}"
                logger.info("[hirify] Поиск: %s", query)

                try:
                    list_page.goto(search_url, wait_until="domcontentloaded", timeout=20_000)
                    list_page.wait_for_timeout(2000)
                except PWTimeout:
                    logger.warning("[hirify] Таймаут: %s", query)
                    continue
                except Exception:
                    logger.exception("[hirify] Ошибка загрузки: %s", query)
                    continue

                links = list_page.query_selector_all("a.vacancy-card-link")
                logger.info("[hirify] Найдено карточек: %d", len(links))

                for link in links:
                    try:
                        href = link.get_attribute("href") or ""
                        if not href or href in seen:
                            continue
                        seen.add(href)

                        title_el = link.query_selector("h3.title")
                        title = title_el.inner_text().strip() if title_el else ""
                        if not title:
                            continue

                        company_el = link.query_selector(".company-name")
                        company_text = company_el.inner_text().strip() if company_el else ""
                        company = "" if "hidden" in company_text.lower() else company_text

                        url = BASE_URL + href
                        desc = _get_description(detail_page, url)

                        slug = href.split("/")[-1]
                        external_id = slug.split("-")[0] if slug else ""

                        result.append({
                            "external_id": external_id,
                            "title": title,
                            "company": company,
                            "salary_min": None,
                            "salary_max": None,
                            "currency": None,
                            "location": "",
                            "work_format": None,
                            "url": url,
                            "description": desc,
                        })
                    except Exception:
                        logger.debug("[hirify] Ошибка разбора карточки", exc_info=True)

            browser.close()

        logger.info("[hirify] Итого: %d вакансий", len(result))
        return result
