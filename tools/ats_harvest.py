"""
Авто-сбор ATS-токенов из произвольного списка URL.
Вызывается парсерами курируемых досок (userinterviews и т.п.):
   harvest_ats_tokens(["https://jobs.ashbyhq.com/foo/...", ...])

Что делает:
1. Регулярками вытаскивает токены greenhouse/ashby/lever из URL.
2. Отсеивает уже известные (parsers/{ats}.COMPANIES).
3. Валидирует через API (200 OK = борд жив).
4. Дописывает в parsers/{ats}.py через append_to_parser.
5. Мутирует in-memory COMPANIES, чтобы в том же цикле следующий ATS-парсер уже видел новые токены.

Намеренно не фильтруем по индустрии — whitelist отсеивает на уровне вакансий.
"""

import importlib
import logging

from tools.discover_ats_by_name import append_to_parser
from tools.discover_ats_from_repo import (
    ATS_PATTERNS,
    _looks_like_token,
    validate_ashby,
    validate_gh,
    validate_lever,
)

logger = logging.getLogger(__name__)

_VALIDATORS = {
    "ashby": validate_ashby,
    "greenhouse": validate_gh,
    "lever": validate_lever,
}
_MODULES = {
    "ashby": "parsers.ashby",
    "greenhouse": "parsers.greenhouse",
    "lever": "parsers.lever",
}


def _extract_tokens(urls: list[str]) -> dict[str, set[str]]:
    found: dict[str, set[str]] = {ats: set() for ats in _VALIDATORS}
    for url in urls:
        for ats, pat in ATS_PATTERNS.items():
            if ats not in _VALIDATORS:
                continue
            for m in pat.findall(url):
                if _looks_like_token(m):
                    found[ats].add(m)
    return found


def harvest_ats_tokens(urls: list[str], source_label: str = "harvest") -> dict[str, list[str]]:
    """Извлекает + валидирует + дописывает токены. Возвращает {ats: [добавленные]}."""
    found = _extract_tokens(urls)
    added: dict[str, list[str]] = {ats: [] for ats in _VALIDATORS}

    for ats, tokens in found.items():
        if not tokens:
            continue
        mod = importlib.import_module(_MODULES[ats])
        existing = {t.lower() for t in mod.COMPANIES}
        new_tokens = sorted(t for t in tokens if t.lower() not in existing)
        if not new_tokens:
            continue

        logger.info("[%s] %s: кандидатов %d, валидирую...", source_label, ats, len(new_tokens))
        validator = _VALIDATORS[ats]
        valid = [t for t in new_tokens if validator(t)]
        if not valid:
            logger.info("[%s] %s: новых валидных нет", source_label, ats)
            continue

        # In-memory: чтобы следующий парсер в цикле уже видел токены.
        mod.COMPANIES.extend(valid)
        # На диск: чтобы пережить рестарт процесса.
        ok, msg = append_to_parser(ats, valid)
        if ok:
            logger.info("[%s] %s: +%d токенов: %s", source_label, ats, len(valid), ", ".join(valid))
        else:
            logger.warning("[%s] %s: запись в файл не удалась — %s", source_label, ats, msg)
        added[ats] = valid

    return added
