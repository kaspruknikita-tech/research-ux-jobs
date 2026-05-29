"""
Парсер Ashby Job Board API.
Публичный, без авторизации. Итерируется по списку компаний.
API: https://api.ashbyhq.com/posting-api/job-board/{board_token}?includeCompensation=true
"""

import logging

import requests

from parsers.base import BaseParser

logger = logging.getLogger(__name__)

API_URL = "https://api.ashbyhq.com/posting-api/job-board/{board_token}?includeCompensation=true"

# Верифицированные board_token компаний на Ashby (API возвращает 200).
# Токены регистрозависимы — берём как в jobs.ashbyhq.com/{token}.
COMPANIES = [
    # AI / ML / dev tools
    "OpenAI", "Linear", "posthog", "ramp", "lovable", "abridge",
    "matter-intelligence", "magicschool", "apify",
    # Продуктовые / B2B / SaaS
    "notion", "Superhuman Platform Inc", "patreon", "wetransfer",
    "Strava", "duck-duck-go", "parafin", "welltech", "sleeper",
    "atticus", "creditgenie", "cointracker", "dailypay",
    "handshake", "better-mortgage", "skydropx",
    # Прочее (вакансии активны/были активны)
    "ruby-labs", "intus", "suno", "Vetcove",
    "thatgamecompany", "mobbin.com",
    # Найдено через google site:jobs.ashbyhq.com (2026-05)
    "1password", "betterup", "photoroom", "kalshi", "trainline",
    "method", "liveflow", "seconddinner", "mazedesign", "jimdo.com",
    "contrast-security", "iacollaborative", "Fuel-Cycle", "M-KOPA",
    "generalintelligencecompany", "latamcent",
    # Расширенный гугл + TheirStack топ-10 (2026-05)
    "kraken.com", "super.com", "n8n", "multiverse", "suzy", "pebl",
    "listenlabs", "nexxen", "comity", "keyrock", "scientech-research",
    "blockhouse", "wincent", "monad.foundation", "wormholelabs",
    "rwazi", "strella", "global-x-etfs", "rallyuxr", "bettermile",
    "apron", "wokelo-ai", "airapps",
    "alan", "renuity", "directive",
]

WHITELIST = [
    "ux researcher", "ux research",
    "user researcher", "user research",
    "product researcher", "design researcher",
    "usability researcher", "usability research",
    "cx researcher", "cx research",
    "consumer insights", "user insights",
    "ux writer", "content designer",
    "usability", "user experience researcher",
]


def _is_relevant(title: str) -> bool:
    t = title.lower()
    return any(w in t for w in WHITELIST)


def _extract_work_format(job: dict) -> str:
    if job.get("isRemote"):
        return "Remote"
    wt = (job.get("workplaceType") or "").strip()
    if wt:
        return wt  # "Hybrid", "Onsite", etc.
    return ""


def _extract_salary(job: dict) -> tuple[int | None, int | None, str | None]:
    """Берёт первый Salary-компонент с заполненными min/max."""
    comp = job.get("compensation") or {}
    for c in comp.get("summaryComponents") or []:
        if c.get("compensationType") == "Salary" and c.get("minValue") and c.get("maxValue"):
            return c.get("minValue"), c.get("maxValue"), c.get("currencyCode")
    return None, None, None


class AshbyParser(BaseParser):
    source_name = "ashby"
    channel = "global"

    def fetch(self) -> list[dict]:
        result = []
        for board_token in COMPANIES:
            url = API_URL.format(board_token=board_token)
            try:
                resp = requests.get(url, timeout=30)
                if resp.status_code == 404:
                    continue
                resp.raise_for_status()
                data = resp.json()
            except requests.RequestException as e:
                logger.warning(
                    "[ashby] %s — ошибка: %s",
                    board_token,
                    getattr(getattr(e, "response", None), "status_code", str(e)),
                )
                continue

            for job in data.get("jobs", []):
                if not job.get("isListed", True):
                    continue
                title = (job.get("title") or "").strip()
                if not _is_relevant(title):
                    continue
                salary_min, salary_max, currency = _extract_salary(job)
                result.append({
                    "external_id": str(job.get("id", "")),
                    "title": title,
                    "company": board_token,
                    "salary_min": salary_min,
                    "salary_max": salary_max,
                    "currency": currency,
                    "location": job.get("location", "") or "",
                    "work_format": _extract_work_format(job),
                    "url": job.get("jobUrl", "") or job.get("applyUrl", ""),
                    "description": job.get("descriptionHtml", "") or job.get("descriptionPlain", ""),
                })

        return result
