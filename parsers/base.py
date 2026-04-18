"""
Базовый класс для всех парсеров.
Каждый новый источник наследуется от BaseParser и реализует fetch().
"""

import hashlib
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class BaseParser(ABC):
    """Общий интерфейс парсера вакансий."""

    source_name: str = "unknown"  # переопределяется в наследнике
    channel: str = "ru"            # "ru" или "global"

    @abstractmethod
    def fetch(self) -> list[dict]:
        """Получает список сырых вакансий из источника.
        Каждая вакансия — dict с полями:
            external_id, title, company, salary_min, salary_max,
            currency, location, work_format, url, description
        """
        ...

    def make_hash(self, title: str, company: str, url: str) -> str:
        """Генерирует хэш для дедупликации."""
        raw = f"{title}|{company}|{url}".lower().strip()
        return hashlib.sha256(raw.encode()).hexdigest()

    def prepare(self, raw: dict) -> dict:
        """Дополняет сырую вакансию служебными полями перед сохранением."""
        return {
            "snippet": None,
            **raw,
            "source": self.source_name,
            "channel": self.channel,
            "hash": self.make_hash(
                raw.get("title", ""),
                raw.get("company", ""),
                raw.get("url", ""),
            ),
            "status": "new",
            "parsed_at": datetime.now(timezone.utc).isoformat(),
        }

    def run(self) -> list[dict]:
        """Полный цикл: забрать → подготовить. Возвращает список готовых dict'ов."""
        logger.info("[%s] Запуск парсера...", self.source_name)
        try:
            raw_vacancies = self.fetch()
        except Exception:
            logger.exception("[%s] Ошибка при парсинге", self.source_name)
            return []
        prepared = [self.prepare(v) for v in raw_vacancies]
        logger.info("[%s] Получено вакансий: %d", self.source_name, len(prepared))
        return prepared
