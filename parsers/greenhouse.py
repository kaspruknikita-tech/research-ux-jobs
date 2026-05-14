"""
Парсер Greenhouse Job Board API.
Публичный, без авторизации. Итерируется по списку компаний.
API: https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs?content=true
"""

import logging

import requests

from parsers.base import BaseParser

logger = logging.getLogger(__name__)

API_URL = "https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs?content=true"

# Верифицированные board_token компаний на Greenhouse (API возвращает 200).
# Токены не всегда совпадают с названием компании.
COMPANIES = [
    # Крупные tech — активно нанимают исследователей
    "airbnb", "stripe", "figma", "twilio", "datadog",
    "duolingo", "gitlab", "instacart", "mixpanel", "robinhood",
    "reddit", "khanacademy", "upwork",
    # Продуктовые / B2B SaaS
    "airtable", "asana", "dropbox", "intercom", "brex",
    "carta", "checkr", "contentful", "faire", "gusto",
    "lattice", "modernhealth", "pendo", "toast", "vercel",
    "webflow", "gleanwork", "growtherapy", "connectwise",
    "betterhelpcom", "stratacareers",
    # Крупные компании (много вакансий, широкий поиск)
    "realtimeboardglobal",  # Miro
    "lucidmotors",          # Lucid
    "gongio",               # Gong
    "tripactions",          # Navan
    "dept", "wpp", "accenturefederalservices",
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


def _extract_location(job: dict) -> str:
    offices = job.get("offices", [])
    if offices:
        return offices[0].get("name", "")
    return ""


def _extract_work_format(job: dict) -> str:
    title_lower = job.get("title", "").lower()
    content = job.get("content", "").lower()
    if "remote" in title_lower or "remote" in content[:500]:
        return "Remote"
    return ""


class GreenhouseParser(BaseParser):
    source_name = "greenhouse"
    channel = "global"

    def fetch(self) -> list[dict]:
        result = []
        for board_token in COMPANIES:
            url = API_URL.format(board_token=board_token)
            try:
                resp = requests.get(url, timeout=15)
                if resp.status_code == 404:
                    continue
                resp.raise_for_status()
                data = resp.json()
            except requests.RequestException as e:
                logger.warning(
                    "[greenhouse] %s — ошибка: %s",
                    board_token,
                    getattr(getattr(e, "response", None), "status_code", str(e)),
                )
                continue

            for job in data.get("jobs", []):
                title = job.get("title", "")
                if not _is_relevant(title):
                    continue
                result.append({
                    "external_id": str(job.get("id", "")),
                    "title": title,
                    "company": board_token.capitalize(),
                    "salary_min": None,
                    "salary_max": None,
                    "currency": None,
                    "location": _extract_location(job),
                    "work_format": _extract_work_format(job),
                    "url": job.get("absolute_url", ""),
                    "description": job.get("content", ""),
                })

        return result
