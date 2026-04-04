"""
Парсер Himalayas.app — будет реализован на этапе 2.
API: https://himalayas.app/api
"""

import logging

from parsers.base import BaseParser

logger = logging.getLogger(__name__)


class HimalayasParser(BaseParser):
    source_name = "himalayas"
    channel = "global"

    def fetch(self) -> list[dict]:
        # TODO: реализовать на этапе 2
        logger.info("[himalayas] Парсер ещё не реализован, пропускаем")
        return []
