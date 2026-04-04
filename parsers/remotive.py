"""
Парсер Remotive.com — будет реализован на этапе 2.
API: https://remotive.com/api/remote-jobs
"""

import logging

from parsers.base import BaseParser

logger = logging.getLogger(__name__)


class RemotiveParser(BaseParser):
    source_name = "remotive"
    channel = "global"

    def fetch(self) -> list[dict]:
        # TODO: реализовать на этапе 2
        logger.info("[remotive] Парсер ещё не реализован, пропускаем")
        return []
