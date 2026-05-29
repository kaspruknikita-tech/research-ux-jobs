"""
Парсер bebee.com/jobs (US-домен, англоязычные вакансии).
Публичного API нет — парсим SSR HTML листинга и JSON-LD JobPosting на детальной.

Листинг: https://bebee.com/us/jobs?q=<query>&page=<N>  (page 0-indexed).
Карточка: <article> с <a href="/us/jobs/<slug>">title</a>.
Детальная: <script type="application/ld+json"> со схемой JobPosting.
"""

import json
import logging
import re

import requests
from bs4 import BeautifulSoup

from parsers.base import BaseParser

logger = logging.getLogger(__name__)

BASE_URL = "https://bebee.com/us/jobs"
MAX_PAGES = 10
PAGE_TIMEOUT = 20

SEARCH_QUERIES = [
    "user research",
    "ux research",
    "design researcher",
    "usability",
    "service designer",
    "customer insights",
]

WHITELIST = [
    "researcher", "research", "ux", "cx", "usability",
    "service designer", "voice of customer", "ux strategist",
    "research ops", "customer experience", "insight",
]

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "en-US,en;q=0.9",
}

_EMPLOYMENT_MAP = {
    "FULL_TIME": "Full-time",
    "PART_TIME": "Part-time",
    "CONTRACTOR": "Contract",
    "TEMPORARY": "Temporary",
    "INTERN": "Internship",
    "VOLUNTEER": "Volunteer",
    "PER_DIEM": "Per diem",
    "OTHER": None,
}

_SALARY_MULTIPLIER = {
    "HOUR": 2080,
    "DAY": 260,
    "WEEK": 52,
    "MONTH": 12,
    "YEAR": 1,
}

_HTML_TAG_RE = re.compile(r"<[^>]+>")


def _is_relevant(title: str) -> bool:
    t = title.lower()
    return any(w in t for w in WHITELIST)


def _strip_html(s: str) -> str:
    return _HTML_TAG_RE.sub(" ", s or "").strip()


def _to_int(v) -> int | None:
    if v is None:
        return None
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return None


def _normalize_salary(base: dict) -> tuple[int | None, int | None, str | None]:
    """JSON-LD baseSalary → (min_year, max_year, currency)."""
    if not isinstance(base, dict):
        return None, None, None
    currency = base.get("currency")
    val = base.get("value") or {}
    smin = _to_int(val.get("minValue"))
    smax = _to_int(val.get("maxValue"))
    unit = (val.get("unitText") or "YEAR").upper()
    mult = _SALARY_MULTIPLIER.get(unit, 1)
    if smin is not None:
        smin *= mult
    if smax is not None:
        smax *= mult
    return smin, smax, currency


def _format_location(loc) -> str:
    """JSON-LD jobLocation → 'City, Country'. Может быть dict или list."""
    if isinstance(loc, list):
        loc = loc[0] if loc else None
    if not isinstance(loc, dict):
        return ""
    addr = loc.get("address") or {}
    if not isinstance(addr, dict):
        return ""
    raw_parts = [
        addr.get("addressLocality"),
        addr.get("addressRegion"),
        addr.get("addressCountry"),
    ]
    seen: set[str] = set()
    parts: list[str] = []
    for p in raw_parts:
        if not p:
            continue
        key = p.strip().lower()
        if key in seen:
            continue
        seen.add(key)
        parts.append(p.strip())
    return ", ".join(parts)


def _parse_listing(html: str) -> list[str]:
    """Возвращает список slug'ов с одной страницы листинга."""
    soup = BeautifulSoup(html, "html.parser")
    slugs = []
    seen = set()
    for a in soup.select('a.hover\\:no-underline[href^="/us/jobs/"]'):
        href = a.get("href", "")
        slug = href.removeprefix("/us/jobs/")
        if not slug or "/" in slug or slug in seen:
            continue
        seen.add(slug)
        slugs.append(slug)
    return slugs


def _parse_detail(html: str, slug: str) -> dict | None:
    """JSON-LD JobPosting → нормализованный dict вакансии."""
    soup = BeautifulSoup(html, "html.parser")
    posting = None
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.get_text())
        except (ValueError, TypeError):
            continue
        items = data if isinstance(data, list) else [data]
        for item in items:
            if isinstance(item, dict) and item.get("@type") == "JobPosting":
                posting = item
                break
        if posting:
            break
    if not posting:
        return None

    title = (posting.get("title") or "").strip()
    if not title:
        return None

    org = posting.get("hiringOrganization") or {}
    company = (org.get("name") or "").strip() if isinstance(org, dict) else ""

    identifier = posting.get("identifier") or {}
    ext_id = ""
    if isinstance(identifier, dict):
        ext_id = str(identifier.get("value") or "").strip()
    if not ext_id:
        ext_id = slug

    smin, smax, currency = _normalize_salary(posting.get("baseSalary"))
    location = _format_location(posting.get("jobLocation"))

    emp_type = posting.get("employmentType")
    if isinstance(emp_type, list):
        emp_type = emp_type[0] if emp_type else None
    work_format = _EMPLOYMENT_MAP.get((emp_type or "").upper())

    description = _strip_html(posting.get("description") or "")

    return {
        "external_id": ext_id,
        "title": title,
        "company": company,
        "salary_min": smin,
        "salary_max": smax,
        "currency": currency,
        "location": location,
        "work_format": work_format,
        "url": f"https://bebee.com/us/jobs/{slug}",
        "description": description,
    }


class BebeeParser(BaseParser):
    source_name = "bebee"
    channel = "global"

    def fetch(self) -> list[dict]:
        session = requests.Session()
        session.headers.update(_HEADERS)

        slugs: list[str] = []
        seen: set[str] = set()

        for query in SEARCH_QUERIES:
            for page in range(MAX_PAGES):
                try:
                    resp = session.get(
                        BASE_URL,
                        params={"q": query, "page": page},
                        timeout=PAGE_TIMEOUT,
                    )
                    resp.raise_for_status()
                except requests.RequestException:
                    logger.exception(
                        "[bebee] Ошибка листинга q=%r стр=%d", query, page
                    )
                    break

                page_slugs = _parse_listing(resp.text)
                if not page_slugs:
                    logger.debug("[bebee] q=%r стр %d пуста, стоп", query, page)
                    break

                added = 0
                for s in page_slugs:
                    if s in seen:
                        continue
                    seen.add(s)
                    slugs.append(s)
                    added += 1
                logger.debug(
                    "[bebee] q=%r стр %d: +%d новых slug'ов",
                    query, page, added,
                )
                if added == 0:
                    break

        logger.info("[bebee] Уникальных slug'ов: %d", len(slugs))

        result: list[dict] = []
        for slug in slugs:
            url = f"{BASE_URL}/{slug}"
            try:
                resp = session.get(url, timeout=PAGE_TIMEOUT)
                resp.raise_for_status()
            except requests.RequestException:
                logger.warning("[bebee] Не удалось скачать детальную %s", slug)
                continue

            vacancy = _parse_detail(resp.text, slug)
            if not vacancy:
                logger.debug("[bebee] JSON-LD не найден: %s", slug)
                continue

            if not _is_relevant(vacancy["title"]):
                continue

            result.append(vacancy)

        logger.info("[bebee] Итого после whitelist: %d вакансий", len(result))
        return result
