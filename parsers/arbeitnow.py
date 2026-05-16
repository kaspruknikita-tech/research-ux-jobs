"""
Парсер Arbeitnow.com.
API: https://www.arbeitnow.com/api/job-board-api
Публичный, без ключей. Возвращает JSON с массивом data, поддерживает пагинацию.
"""

import logging

import requests

from parsers.base import BaseParser

logger = logging.getLogger(__name__)

API_URL = "https://www.arbeitnow.com/api/job-board-api"
MAX_PAGES = 15

WHITELIST = [
    "researcher", "research", "ux", "cx",
    "insight", "usability",
    "service designer", "voice of customer",
    "ux strategist", "research ops",
    "cx analyst", "customer experience",
]


def _is_relevant(title: str) -> bool:
    t = title.lower()
    return any(w in t for w in WHITELIST)


class ArbeitnowParser(BaseParser):
    source_name = "arbeitnow"
    channel = "global"

    def fetch(self) -> list[dict]:
        result = []
        for page in range(1, MAX_PAGES + 1):
            try:
                resp = requests.get(API_URL, params={"page": page}, timeout=15)
                resp.raise_for_status()
                jobs = resp.json().get("data", [])
            except requests.RequestException:
                logger.exception("[arbeitnow] Ошибка запроса, страница %d", page)
                break

            if not jobs:
                break

            for job in jobs:
                title = job.get("title", "")
                if not _is_relevant(title):
                    continue
                result.append({
                    "external_id": str(job.get("slug", "")),
                    "title": title,
                    "company": job.get("company_name", ""),
                    "salary_min": None,
                    "salary_max": None,
                    "currency": None,
                    "location": job.get("location", ""),
                    "work_format": None,
                    "url": job.get("url", ""),
                    "description": job.get("description", ""),
                })

        return result
