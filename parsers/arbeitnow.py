"""
Парсер Arbeitnow.com — будет реализован на этапе 2.
API: https://www.arbeitnow.com/api/job-board-api
"""

import logging

from parsers.base import BaseParser

logger = logging.getLogger(__name__)


class ArbeitnowParser(BaseParser):
    source_name = "arbeitnow"
    channel = "global"

    def fetch(self) -> list[dict]:
        # TODO: реализовать на этапе 2
        logger.info("[arbeitnow] Парсер ещё не реализован, пропускаем")
        return []
