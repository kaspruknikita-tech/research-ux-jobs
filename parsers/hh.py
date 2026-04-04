"""
Парсер вакансий с hh.ru через публичный API.
Документация: https://api.hh.ru/openapi/redoc#tag/Poisk-vakansij

Двухшаговая схема:
1. GET /vacancies?text=... — получаем список ID и сниппеты
2. GET /vacancies/{id} — получаем полную карточку с описанием и навыками
"""

import logging
import time

import requests

import config
from parsers.base import BaseParser

logger = logging.getLogger(__name__)

# === Поисковые запросы ===

# Точные — ищем по всему тексту вакансии
SEARCH_QUERIES = [
    # Английские
    "UX researcher",
    "User researcher",
    "Usability researcher",
    "CX researcher",
    "Product researcher",
    '"Customer Insight"',
    '"Consumer Insights"',
    '"Customer Journey Researcher"',
    "UX-researcher",
    "Head of Discovery",
    # Русские
    "UX исследователь",
    "UX-исследователь",
    "Исследователь пользовательского опыта",
    "Исследователь юзабилити",
    "Продуктовый исследователь",
    "Исследователь CX",
    "CX-исследователь",
    "CX исследователь",
    "Исследователь клиентского опыта",
    "Исследователь цифровых продуктов",
    "Исследователь интерфейсов",
    "Исследователь UX/UI",
    "Исследователь сервисного дизайна",
    "клиентский исследователь",
    "исследователь клиентского пути",
    
]

# Широкие — ищем ТОЛЬКО по заголовку (search_field=name)
TITLE_ONLY_QUERIES = [
    "клиентские исследования",
    "маркетинговые исследования",
    "количественные исследования",
    "качественные исследования",
    "качественный исследователь"
]

HH_API_URL = "https://api.hh.ru/vacancies"
DETAIL_REQUEST_DELAY = 0.3


class HHParser(BaseParser):
    source_name = "hh.ru"
    channel = "ru"

    def fetch(self) -> list[dict]:
        all_vacancies = []
        seen_ids: set[str] = set()

        for query in SEARCH_QUERIES:
            self._collect(query, seen_ids, all_vacancies)

        for query in TITLE_ONLY_QUERIES:
            self._collect(query, seen_ids, all_vacancies, search_field="name")

        return all_vacancies

    def _collect(self, query, seen_ids, result, search_field=None):
        """Забирает вакансии по запросу и добавляет новые в result."""
        items = self._search(query, search_field=search_field)
        for item in items:
            vid = str(item.get("id", ""))
            if vid and vid not in seen_ids:
                seen_ids.add(vid)
                base = self._parse_item(item)
                if not base:
                    continue
                detail = self._fetch_detail(vid)
                if detail:
                    base["description"] = detail.get("description", base["description"])
                    base["key_skills"] = detail.get("key_skills", [])
                result.append(base)

    def _search(self, query: str, per_page: int = 50, search_field: str = None) -> list[dict]:
        """Один поисковый запрос к API hh.ru."""
        headers = {"User-Agent": config.HH_USER_AGENT}
        params = {
            "text": query,
            "per_page": per_page,
            "page": 0,
            "order_by": "publication_time",
            "period": 7,
        }
        if search_field:
            params["search_field"] = search_field
        try:
            resp = requests.get(HH_API_URL, headers=headers, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            return data.get("items", [])
        except requests.RequestException:
            logger.exception("Ошибка запроса к hh.ru: query=%s", query)
            return []

    def _fetch_detail(self, vacancy_id: str) -> dict | None:
        """Запрашивает полную карточку вакансии по ID."""
        url = f"{HH_API_URL}/{vacancy_id}"
        headers = {"User-Agent": config.HH_USER_AGENT}
        try:
            time.sleep(DETAIL_REQUEST_DELAY)
            resp = requests.get(url, headers=headers, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            return {
                "description": data.get("description", ""),
                "key_skills": [
                    s.get("name", "") for s in data.get("key_skills", [])
                ],
            }
        except requests.RequestException:
            logger.warning("Не удалось получить карточку вакансии %s", vacancy_id)
            return None

    def _parse_item(self, item: dict) -> dict | None:
        """Преобразует элемент из списка в наш формат."""
        try:
            salary = item.get("salary") or {}
            return {
                "external_id": str(item["id"]),
                "title": item.get("name", ""),
                "company": (item.get("employer") or {}).get("name", ""),
                "salary_min": salary.get("from"),
                "salary_max": salary.get("to"),
                "currency": salary.get("currency"),
                "location": (item.get("area") or {}).get("name", ""),
                "work_format": self._extract_work_format(item),
                "url": item.get("alternate_url", ""),
                "description": (item.get("snippet") or {}).get("requirement", ""),
                "snippet": self._extract_snippet(item),
                "key_skills": [],
            }
        except (KeyError, TypeError):
            logger.exception("Не удалось распарсить вакансию: %s", item.get("id"))
            return None

    @staticmethod
    def _extract_snippet(item: dict) -> str:
        snippet = item.get("snippet") or {}
        parts = []
        if snippet.get("requirement"):
            parts.append(snippet["requirement"])
        if snippet.get("responsibility"):
            parts.append(snippet["responsibility"])
        return " | ".join(parts)

    @staticmethod
    def _extract_work_format(item: dict) -> str:
        schedule = item.get("schedule")
        if schedule and isinstance(schedule, dict):
            return schedule.get("name", "")
        return ""
