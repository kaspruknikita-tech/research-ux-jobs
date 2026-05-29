"""
Парсер Lever Postings API.
Публичный, без авторизации. Итерируется по списку компаний.
API: https://api.lever.co/v0/postings/{board_token}?mode=json
"""

import logging

import requests

from parsers.base import BaseParser

logger = logging.getLogger(__name__)

API_URL = "https://api.lever.co/v0/postings/{board_token}?mode=json"

# Верифицированные board_token на Lever (jobs.lever.co/{token}).
# Регистр важен (есть Huckleberrylabs, court-avenue и т.п.).
COMPANIES = [
    # Найдено через google site:jobs.lever.co (2026-05)
    "outreach", "Huckleberrylabs", "colibrigroup", "zoox", "articulate",
    "fyusion", "jobgether", "prosper", "brevo",
    "xero", "wetransfer", "pointclickcare", "wmg", "valgenesis",
    "blinkux", "elevatelabs", "spotify",
    "researchinnovations.com", "waabi", "convergentresearch", "grantstreet",
    "apolloresearch", "hopelab", "whoop",
    "crowdriff", "ro", "viget", "rover", "finix", "fantasy",
    "court-avenue", "lodgify",
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
    cats = job.get("categories") or {}
    return (cats.get("location") or "").strip()


def _extract_work_format(job: dict) -> str:
    wt = (job.get("workplaceType") or "").strip()
    if wt:
        return wt.capitalize()  # "remote" -> "Remote"
    return ""


def _extract_salary(job: dict) -> tuple[int | None, int | None, str | None]:
    sr = job.get("salaryRange") or {}
    return sr.get("min"), sr.get("max"), sr.get("currency")


class LeverParser(BaseParser):
    source_name = "lever"
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
            except (requests.RequestException, ValueError) as e:
                logger.warning(
                    "[lever] %s — ошибка: %s",
                    board_token,
                    getattr(getattr(e, "response", None), "status_code", str(e)),
                )
                continue

            for job in data:
                title = (job.get("text") or "").strip()
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
                    "location": _extract_location(job),
                    "work_format": _extract_work_format(job),
                    "url": job.get("hostedUrl") or job.get("applyUrl", ""),
                    "description": job.get("description", ""),
                })

        return result
