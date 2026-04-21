"""
Парсер Remotive.com.
API: https://remotive.com/api/remote-jobs
Публичный, без ключей. Поддерживает search= (полнотекстовый поиск по title+description).
"""

import logging
import time

import requests

from parsers.base import BaseParser

logger = logging.getLogger(__name__)

API_URL = "https://remotive.com/api/remote-jobs"
REQUEST_DELAY = 1.0

SEARCH_QUERIES = [
    "ux researcher",
    "user researcher",
    "cx researcher",
    "customer researcher",
    "insights researcher",
    "usability researcher",
    "design researcher",
]


class RemotiveParser(BaseParser):
    source_name = "remotive"
    channel = "global"

    def fetch(self) -> list[dict]:
        result = []
        seen_ids: set[str] = set()

        for query in SEARCH_QUERIES:
            jobs = self._search(query)
            for job in jobs:
                vid = str(job.get("id", ""))
                if not vid or vid in seen_ids:
                    continue
                seen_ids.add(vid)
                result.append({
                    "external_id": vid,
                    "title": job.get("title", ""),
                    "company": job.get("company_name", ""),
                    "salary_min": None,
                    "salary_max": None,
                    "currency": None,
                    "location": job.get("candidate_required_location", ""),
                    "work_format": "Remote",
                    "url": job.get("url", ""),
                    "description": job.get("description", ""),
                })
            time.sleep(REQUEST_DELAY)

        return result

    def _search(self, query: str) -> list[dict]:
        try:
            resp = requests.get(API_URL, params={"search": query}, timeout=15)
            resp.raise_for_status()
            return resp.json().get("jobs", [])
        except requests.RequestException:
            logger.exception("[remotive] Ошибка запроса: query=%s", query)
            return []
