"""
Парсер Telegram-каналов через Telethon — будет реализован на этапе 3.
Требует отдельную Telegram API app (api_id, api_hash).
"""

import logging

from parsers.base import BaseParser

logger = logging.getLogger(__name__)


class TelegramChannelParser(BaseParser):
    source_name = "telegram"
    channel = "ru"  # может быть и global, зависит от канала-источника

    def fetch(self) -> list[dict]:
        # TODO: реализовать на этапе 3 (Telethon)
        logger.info("[telegram] Парсер ещё не реализован, пропускаем")
        return []
