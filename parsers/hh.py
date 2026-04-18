"""
Парсер вакансий с hh.ru через публичный API.
Документация: https://api.hh.ru/openapi/redoc#tag/Poisk-vakansij

Двухшаговая схема:
1. GET /vacancies?text=... — получаем список ID и сниппеты
2. GET /vacancies/{id} — получаем полную карточку с описанием и навыками
"""

import logging
import re
import time

import requests

import config
from parsers.base import BaseParser

logger = logging.getLogger(__name__)

# === OAuth токен ===
_token: str | None = None
_token_expires_at: float = 0


def _get_token() -> str | None:
    """Возвращает актуальный OAuth-токен. Обновляет если истёк."""
    global _token, _token_expires_at

    if not config.HH_CLIENT_ID or not config.HH_CLIENT_SECRET:
        return None

    if _token and time.time() < _token_expires_at - 60:
        return _token

    try:
        resp = requests.post(
            "https://hh.ru/oauth/token",
            data={
                "grant_type": "client_credentials",
                "client_id": config.HH_CLIENT_ID,
                "client_secret": config.HH_CLIENT_SECRET,
            },
            headers={"User-Agent": config.HH_USER_AGENT},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        _token = data["access_token"]
        _token_expires_at = time.time() + data.get("expires_in", 86400)
        logger.info("hh.ru OAuth токен получен")
        return _token
    except Exception:
        logger.exception("Не удалось получить OAuth токен hh.ru")
        return None


def _headers() -> dict:
    headers = {"User-Agent": config.HH_USER_AGENT}
    token = _get_token()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


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
HIGHLIGHT_TAG_RE = re.compile(r"</?highlighttext>")


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
                    base["work_format_raw"] = detail.get("work_format_raw", [])
                    base["schedule"] = detail.get("schedule", {})
                base["work_format"] = self._map_work_format(base)
                result.append(base)

    def _search(self, query: str, per_page: int = 50, search_field: str = None) -> list[dict]:
        """Один поисковый запрос к API hh.ru."""
        headers = _headers()
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
        headers = _headers()
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
                "work_format_raw": data.get("work_format") or [],
                "schedule": data.get("schedule") or {},
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
                "work_format": None,  # заполняется после _fetch_detail в _collect
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
        text = " | ".join(parts)
        return HIGHLIGHT_TAG_RE.sub("", text)

    @staticmethod
    def _map_work_format(vacancy: dict) -> str | None:
        """Определяет формат работы: Удалёнка / Офис / Гибрид / None.

        Приоритет: новое поле work_format из детальки (массив id),
        fallback — старое поле schedule.name.
        """
        work_format = vacancy.get("work_format_raw") or []
        ids = {item.get("id") for item in work_format if isinstance(item, dict)}

        if "REMOTE" in ids:
            return "Удалёнка"
        if "HYBRID" in ids:
            return "Гибрид"
        if "ON_SITE" in ids:
            return "Офис"

        # Fallback: старое поле schedule
        schedule = vacancy.get("schedule") or {}
        schedule_id = schedule.get("id") if isinstance(schedule, dict) else None
        if schedule_id == "remote":
            return "Удалёнка"

        return None

