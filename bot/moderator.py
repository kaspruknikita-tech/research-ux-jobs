"""
Отправка вакансий в чат модерации и публикация одобренных в каналы.
Использует Telegram Bot API напрямую через requests (без asyncio).
"""

import time
import logging

import requests

import config
import database
from bot.templates import format_ru, format_global
from scoring import score_vacancy, PROMPT_VERSION
from scoring.models import PostEnrichment, ScoringResult

logger = logging.getLogger(__name__)

_SEND_DELAY = 3.5
_TIER_ICONS = {"S": "⭐", "A": "🔵", "B": "🟡", "C": "🔴"}


def _api(method: str, **kwargs) -> dict:
    url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/{method}"
    resp = requests.post(url, json=kwargs, timeout=10)
    data = resp.json()
    if not data.get("ok"):
        raise RuntimeError(f"Telegram API error [{method}]: {data.get('description')}")
    return data


def _get_enrichment(result: ScoringResult | None) -> dict | None:
    if result and result.post_enrichment:
        return result.post_enrichment.model_dump()
    return None


def _format(vacancy: dict, result: ScoringResult | None = None) -> str:
    enrichment = _get_enrichment(result)
    if vacancy.get("channel") == "ru":
        return format_ru(vacancy, enrichment=enrichment)
    return format_global(vacancy, enrichment=enrichment)


def _scoring_footer(result: ScoringResult) -> str:
    icon = _TIER_ICONS[result.tier]

    if result.pre_filter_blocked:
        return f"\n\n{icon} Tier {result.tier} · {result.reason}"

    parts = [f"{icon} Tier {result.tier}"]
    if result.score > 0:
        parts[0] += f" · {result.score}/10"

    if result.visa_sponsorship in ("yes", "implied"):
        parts.append("Виза ✓")
    if result.relocation_support in ("yes", "implied"):
        parts.append("Релокация ✓")

    lines = [" | ".join(parts)]
    if result.reason:
        lines.append(f"💬 {result.reason}")
    if result.needs_enrichment:
        lines.append("⚠️ Неполные данные, проверь вручную")

    return "\n\n" + "\n".join(lines)


def _keyboard(vacancy_id: int, channel: str) -> dict:
    return {
        "inline_keyboard": [[
            {"text": "✅ Опубликовать", "callback_data": f"approve:{vacancy_id}:{channel}"},
            {"text": "❌ Отклонить",    "callback_data": f"reject:{vacancy_id}"},
        ]]
    }


def _row_to_scoring_result(row: dict, vacancy_id: int) -> ScoringResult:
    """Восстанавливает ScoringResult из строки vacancy_scores."""
    enrich_data = row.get("post_enrichment")
    post_enrichment = PostEnrichment(**enrich_data) if enrich_data else None
    return ScoringResult(
        vacancy_id=vacancy_id,
        tier=row["tier"],
        action=row["action"],
        score=row["score"],
        score_breakdown=row.get("score_breakdown") or {},
        visa_sponsorship=row["visa_sponsorship"],
        relocation_support=row["relocation_support"],
        remote_policy=row.get("remote_policy", "unclear"),
        salary_min=row.get("salary_min"),
        salary_max=row.get("salary_max"),
        salary_currency=row.get("salary_currency"),
        experience_level=row.get("experience_level", "unclear"),
        verbatim_evidence=row.get("verbatim_evidence") or {},
        pre_filter_blocked=bool(row.get("pre_filter_blocked", False)),
        regex_completeness_score=0.0,
        enrichment_used=post_enrichment is not None,
        completeness_score=1.0,
        needs_enrichment=False,
        post_enrichment=post_enrichment,
        reason=row.get("reason", ""),
        model_used=row.get("model_used", ""),
        latency_ms=row.get("latency_ms", 0),
    )


def _get_or_score(vacancy: dict) -> ScoringResult | None:
    """Берёт скор из БД. Если нет — считает заново."""
    try:
        row = database.get_latest_vacancy_score(vacancy["id"])
        if row:
            return _row_to_scoring_result(row, vacancy["id"])
        result = score_vacancy(vacancy)
        database.save_vacancy_score(result, PROMPT_VERSION)
        return result
    except Exception:
        logger.warning("Скоринг не удался для вакансии %s", vacancy.get("id"))
        return None


def send_to_moderation(vacancy: dict, scoring_result: ScoringResult | None = None) -> bool:
    """Отправляет одну вакансию в чат модерации с кнопками. True = успешно."""
    try:
        if scoring_result is None:
            scoring_result = _get_or_score(vacancy)

        text = _format(vacancy, scoring_result)
        if scoring_result is not None:
            text += _scoring_footer(scoring_result)

        _api(
            "sendMessage",
            chat_id=config.TELEGRAM_MODERATION_CHAT,
            text=text,
            parse_mode="HTML",
            reply_markup=_keyboard(vacancy["id"], vacancy["channel"]),
            disable_web_page_preview=True,
        )
        database.mark_pending(vacancy["id"])
        return True
    except Exception:
        logger.exception("Не удалось отправить вакансию %s на модерацию", vacancy.get("id"))
        return False


def send_new_vacancies_to_moderation() -> int:
    """Берёт все 'new' вакансии из БД и отправляет в чат модерации."""
    if not config.TELEGRAM_BOT_TOKEN or not config.TELEGRAM_MODERATION_CHAT:
        logger.warning("Telegram не настроен, пропускаем отправку на модерацию")
        return 0

    vacancies = database.get_new_vacancies()
    if not vacancies:
        return 0

    sent = 0
    for v in vacancies:
        if send_to_moderation(v):
            sent += 1
        time.sleep(_SEND_DELAY)

    logger.info("Отправлено на модерацию: %d вакансий", sent)
    return sent
