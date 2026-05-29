from __future__ import annotations

import json
import logging
import os
import time

from openai import OpenAI

from .models import ScoringInput

logger = logging.getLogger(__name__)

MODEL = "perplexity/sonar"
MAX_TOKENS = 700


_client: OpenAI | None = None


def _get_client() -> OpenAI:
    """Ленивый module-level OpenAI клиент. Один httpx-pool на процесс."""
    global _client
    if _client is None:
        _client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.environ["OPENROUTER_API_KEY"],
        )
    return _client


def _extract_json(raw: str) -> dict:
    """Вытаскивает JSON-объект из ответа модели. Толерантен к markdown-fence,
    тексту до/после, и одному обрезанному хвосту."""
    raw = (raw or "").strip()
    if raw.startswith("```"):
        raw = raw.split("```", 2)[1]
        if raw.lstrip().startswith("json"):
            raw = raw.lstrip()[4:]
        raw = raw.rsplit("```", 1)[0]
    raw = raw.strip()
    start = raw.find("{")
    end = raw.rfind("}")
    if start == -1:
        raise ValueError("В ответе нет '{'")
    candidate = raw[start:end + 1] if end > start else raw[start:]
    return json.loads(candidate)

_SYSTEM_PROMPT = """Ты — Market Intelligence Analyst и Lead UX/CX Researcher.
Анализируешь вакансию и стоящий за ней IT-бренд для продуктовых исследователей,
социологов и антропологов из СНГ, которые ищут сильные компании для релокации или удалённой B2B-работы.

ОГРАНИЧЕНИЯ:
- ИГНОРИРУЙ фразу "Sorry, this job is not available in your region" — это баг парсера, не признак отсутствия релокации.
- Бренд — твоя база знаний и веб-поиск. Роль — только текст вакансии.
- Весь текст в полях на русском языке. Без markdown, без эмодзи, без воды.

ВНУТРЕННЕ ОЦЕНИ (в summary НЕ перечисляй рубрики, а сплавь в связный текст):
  1. Бренд и престиж — узнаваемость, инновационность, вес строчки в резюме.
  2. Зрелость роли по JD — стратегические инсайты vs базовое юзабилити; упоминание качественных/количественных методов, социологии, JTBD.
  3. Устойчивость и рынок — финансовая стабильность, отсутствие недавних массовых сокращений.
  4. Культура — тональность JD (живой язык vs булшит), известные отзывы о WLB.

brand_boost — влияние бренда на итоговый тир:
  2  — Tier 1: FAANG, глобально известные продуктовые (Google, Spotify, Notion, Figma...)
  1  — Tier 2: известные в IT (mid-size SaaS, B2B-платформы, growing scale-ups)
  0  — Нишевый: известны в вертикали, небольшой масштаб
 -1  — Неизвестный или серьёзные красные флаги (массовые сокращения, скандалы)

СТРОГО JSON, без markdown, без текста вне JSON:
{
  "brand_tag": "Tier 1 | Tier 2 | Нишевый | Неизвестный",
  "brand_boost": <integer: -1, 0, 1 or 2>,
  "industry": "<коротко: Enterprise SaaS, Legal Tech, FinTech>",
  "scale": "<коротко: ~5000 чел., публичная | Series C>",
  "summary": "<РОВНО 2-3 предложения. Сплавь: чем известны + зрелость роли + рынок/культура + краткий вердикт стоит ли откликаться. Без рубрик, без буллетов, без перечислений 'во-первых'. Конкретика вместо общих слов.>"
}"""


def _build_user_message(inp: ScoringInput) -> str:
    parts = [f"Компания: {inp.company}", f"Вакансия: {inp.title}"]
    if inp.location:
        parts.append(f"Локация: {inp.location}")
    parts.append(f"\nОписание:\n{inp.description}")
    return "\n".join(parts)


def call_brand_scorer(inp: ScoringInput) -> dict:
    """Возвращает dict с brand_boost и качественным анализом бренда.
    При ошибке возвращает нейтральный результат (brand_boost=0) без падения пайплайна."""
    client = _get_client()
    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": _build_user_message(inp)},
    ]

    t0 = time.monotonic()
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            max_tokens=MAX_TOKENS,
            temperature=0,
            timeout=20.0,
        )
        latency_ms = int((time.monotonic() - t0) * 1000)
        raw = response.choices[0].message.content
        logger.debug("[BRAND RAW] vacancy_id=%d content=%.500r", inp.vacancy_id, raw)

        data = _extract_json(raw)
        usage = response.usage
        total_tokens = (usage.prompt_tokens + usage.completion_tokens) if usage else 0
        logger.info(
            "BRAND: model=%s latency=%dms tokens=%d vacancy_id=%d tag=%s boost=%s",
            MODEL, latency_ms, total_tokens, inp.vacancy_id,
            data.get("brand_tag"), data.get("brand_boost"),
        )
        data["model_used"] = MODEL
        data["latency_ms"] = latency_ms
        # Clamp brand_boost to [-1, 2]
        data["brand_boost"] = max(-1, min(2, int(data.get("brand_boost", 0))))
        return data

    except Exception as exc:
        latency_ms = int((time.monotonic() - t0) * 1000)
        logger.warning("BRAND scorer failed vacancy_id=%d error=%s", inp.vacancy_id, exc)
        return {
            "brand_tag": "Неизвестный",
            "brand_boost": 0,
            "industry": "",
            "scale": "",
            "summary": "",
            "model_used": MODEL,
            "latency_ms": latency_ms,
            "error": str(exc),
        }
