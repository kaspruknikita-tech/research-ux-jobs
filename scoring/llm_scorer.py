from __future__ import annotations

import json
import logging
import os
import time

from openai import OpenAI

from .models import ScoringInput

logger = logging.getLogger(__name__)

PROMPT_VERSION = "v2"


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

MODELS = [
    {"id": "google/gemini-2.5-flash-lite", "max_tokens": 2000, "priority": 1},
    {"id": "mistralai/mistral-small-3.2-24b-instruct", "max_tokens": 2000, "priority": 2},
    {"id": "meta-llama/llama-3.3-70b-instruct", "max_tokens": 2000, "priority": 3},
]

_SCORING_INSTRUCTIONS = """
## EXTRACTION TASK

Extract these fields from the job posting. Only assign a value if evidence is explicitly or implicitly in the text. Do NOT calculate any score — scoring is done separately by the system.

- visa_sponsorship: "yes" (explicitly offered), "implied" (e.g. "open worldwide", "will help with work authorization"), "no" (explicitly denied), "unclear"
- relocation_support: "yes", "implied" (hints at relocation package), "no", "unclear"
- remote_policy: ONE of:
  - "global" — remote with NO geo restriction (worldwide, anywhere)
  - "eu" — remote but EU/EMEA only
  - "us_only" — remote but US-only ("Remote US", "Remote — United States", "must be located in the US") — NOT global
  - "hybrid" — partial office presence required
  - "on_site" — full-time office
  - "unclear" — not specified
- experience_level: "junior" (<2y), "mid" (2–5y), "senior" (5+y), "lead", "unclear"

- research_maturity: true if posting explicitly mentions mature research practice — mixed methods, research ops, JTBD, longitudinal studies, ethnography, Dovetail/Maze/dscout, quantitative + qualitative combined. false otherwise.

- vague_jd: true if posting uses buzzwords ("rockstar", "ninja", "wear many hats") OR lists 5+ unrelated duties without specifics OR is mostly fluff. false if concrete and structured.

- verbatim_evidence: for visa_sponsorship, relocation_support, remote_policy — exact quote from text (≤ 20 words). Omit the key if value is "unclear" or "no".

- reason: 1-2 sentences in Russian for the moderator. What this role is, main pros/cons.
"""

_ENRICH_INSTRUCTIONS = """
## STEP 3: ENRICH (fill missing post fields)

The job post is missing some fields needed to publish it. Extract or infer them from the text.
Use the same language as the job posting for all fields (English for English jobs).

- post_enrichment.summary: 1–2 sentences — who they're looking for and why (no "TL;DR", "Summary:" or other labels)
- post_enrichment.key_tasks: 3–5 bullet points — main responsibilities/duties
- post_enrichment.key_requirements: 3–5 bullet points — required skills/qualifications
- post_enrichment.key_benefits: 2–4 bullet points — remote/visa/salary/relocation perks
- post_enrichment.formatted_salary: formatted string like "$90k–$130k" or null if not mentioned
- post_enrichment.seniority_label: "Junior", "Mid-level", "Senior", "Lead", or "Not specified"
"""

_ENRICH_RU_INSTRUCTIONS = """
## STEP 3: ДОСБОРКА ПОСТА

В вакансии недостаточно информации для публикации. Извлеки или выведи из текста:

- post_enrichment.summary: 1–2 предложения на русском — кто нужен и зачем
- post_enrichment.key_tasks: 3–5 основных задач, на русском языке
- post_enrichment.key_requirements: 3–5 требований, на русском языке
- post_enrichment.key_benefits: 2–4 пункта об условиях (зарплата, формат, бонусы)
- post_enrichment.formatted_salary: строка вида "120 000–180 000 ₽" или null
- post_enrichment.seniority_label: "Junior", "Middle", "Senior", "Lead" или "Не указан"
"""

_OUTPUT_SCORE_ONLY = """{
  "visa_sponsorship": "yes|implied|no|unclear",
  "relocation_support": "yes|implied|no|unclear",
  "remote_policy": "global|eu|us_only|hybrid|on_site|unclear",
  "experience_level": "junior|mid|senior|lead|unclear",
  "research_maturity": <true|false>,
  "vague_jd": <true|false>,
  "verbatim_evidence": {
    "visa_sponsorship": "<exact quote ≤ 20 words, omit key if unclear/no>",
    "relocation_support": "<exact quote ≤ 20 words, omit key if unclear/no>",
    "remote_policy": "<exact quote ≤ 20 words, omit key if unclear/no>"
  },
  "reason": "<1-2 sentences in Russian for the moderator>"
}"""

_OUTPUT_WITH_ENRICH = """{
  "visa_sponsorship": "yes|implied|no|unclear",
  "relocation_support": "yes|implied|no|unclear",
  "remote_policy": "global|eu|us_only|hybrid|on_site|unclear",
  "experience_level": "junior|mid|senior|lead|unclear",
  "research_maturity": <true|false>,
  "vague_jd": <true|false>,
  "verbatim_evidence": {
    "visa_sponsorship": "<exact quote ≤ 20 words, omit key if unclear/no>",
    "relocation_support": "<exact quote ≤ 20 words, omit key if unclear/no>",
    "remote_policy": "<exact quote ≤ 20 words, omit key if unclear/no>"
  },
  "reason": "<1-2 sentences in Russian for the moderator>",
  "post_enrichment": {
    "summary": "<1-2 sentences in posting language>",
    "key_tasks": ["<main responsibility>", "..."],
    "key_requirements": ["<requirement>", "..."],
    "key_benefits": ["<benefit in Russian>", "..."],
    "formatted_salary": "<string or null>",
    "seniority_label": "<label>"
  }
}"""

_OUTPUT_ENRICH_ONLY = """{
  "post_enrichment": {
    "summary": "<1-2 предложения на русском>",
    "key_tasks": ["<основная задача>", "..."],
    "key_requirements": ["<требование>", "..."],
    "key_benefits": ["<условие>", "..."],
    "formatted_salary": "<строка или null>",
    "seniority_label": "<уровень>"
  }
}"""

_BASE_SYSTEM_PROMPT = """You are an extraction assistant for UX/CX researcher job postings.

TARGET AUDIENCE: UX and CX researchers from CIS countries seeking remote work, visa sponsorship, or relocation support.

ROLE CHECK: If the vacancy is for a designer, product manager, data analyst, or any non-researcher role — set all extraction fields to "unclear"/null/false, omit post_enrichment, and explain in reason why it is not a researcher role.

All signals must have evidence in the text. Do not invent data.
Strict JSON only. No markdown. No text outside JSON."""

_BASE_RU_SYSTEM_PROMPT = """Ты помощник по досборке постов о вакансиях для UX/CX-исследователей.

Твоя задача — извлечь из текста недостающую информацию для публикации.
Не придумывай то, чего нет в тексте.
Отвечай строго JSON, без markdown и лишнего текста."""


_LANG_EN = (
    "\n\nLANGUAGE RULE: The job posting is in English. "
    "ALL text in post_enrichment fields (summary, key_tasks, key_requirements, key_benefits) "
    "MUST be written in English only. Do NOT use Russian or any other language."
)
_LANG_RU = (
    "\n\nПРАВИЛО ЯЗЫКА: Вакансия на русском языке. "
    "ВСЕ поля post_enrichment (summary, key_tasks, key_requirements, key_benefits) "
    "ДОЛЖНЫ быть написаны только на русском языке."
)


def _make_system_prompt(enrich: bool, is_ru: bool = False) -> str:
    lang_rule = (_LANG_RU if is_ru else _LANG_EN) if enrich else ""
    # Языковая директива идёт ПЕРВОЙ — мелкие модели не дочитывают до конца
    steps = lang_rule + "\n\n" + _BASE_SYSTEM_PROMPT + "\n" + _SCORING_INSTRUCTIONS
    if enrich:
        steps += "\n" + _ENRICH_INSTRUCTIONS
    steps += "\n\n## OUTPUT FORMAT\n\n"
    steps += _OUTPUT_WITH_ENRICH if enrich else _OUTPUT_SCORE_ONLY
    return steps


def _build_user_message(inp: ScoringInput) -> str:
    parts = [f"Title: {inp.title}", f"Company: {inp.company}"]
    if inp.location:
        parts.append(f"Location: {inp.location}")
    if inp.work_format:
        parts.append(f"Work format: {inp.work_format}")
    if inp.salary_min or inp.salary_max:
        parts.append(f"Salary: {inp.salary_min or '?'}–{inp.salary_max or '?'} {inp.currency or ''}")
    parts.append(f"\nDescription:\n{inp.description}")
    return "\n".join(parts)


def call_with_fallback(messages: list[dict], vacancy_id: int, label: str) -> dict:
    client = _get_client()
    # DEBUG: log scorer input — remove before release
    logger.debug("[SCORER INPUT] vacancy_id=%d label=%s prompt_chars=%d",
                 vacancy_id, label, sum(len(m.get("content", "")) for m in messages))

    last_exc: Exception | None = None
    for model in sorted(MODELS, key=lambda m: m["priority"]):
        t0 = time.monotonic()
        try:
            response = client.chat.completions.create(
                model=model["id"],
                messages=messages,
                max_tokens=model["max_tokens"],
                temperature=0,
                response_format={"type": "json_object"},
                timeout=15.0,
            )
            latency_ms = int((time.monotonic() - t0) * 1000)
            usage = response.usage
            total_tokens = (usage.prompt_tokens + usage.completion_tokens) if usage else 0
            logger.info(
                "LLM: model=%s latency=%dms tokens=%d vacancy_id=%d mode=%s",
                model["id"], latency_ms, total_tokens, vacancy_id, label,
            )
            raw_content = response.choices[0].message.content
            # DEBUG: log raw AI response — remove before release
            logger.debug("[SCORER RAW RESPONSE] model=%s vacancy_id=%d content=%.500r",
                         model["id"], vacancy_id, raw_content)

            parsed = json.loads(raw_content)
            if not isinstance(parsed, dict):
                raise ValueError(f"LLM returned non-dict JSON: {type(parsed).__name__} (value={raw_content!r:.100})")

            # DEBUG: log parsed keys — remove before release
            logger.debug("[SCORER PARSED] vacancy_id=%d keys=%s", vacancy_id, list(parsed.keys()))

            parsed["model_used"] = model["id"]
            parsed["latency_ms"] = latency_ms
            return parsed
        except Exception as exc:
            logger.warning(
                "LLM fallback: model=%s error=%s vacancy_id=%d",
                model["id"], exc, vacancy_id,
            )
            last_exc = exc

    raise RuntimeError(f"All LLM models failed for vacancy_id={vacancy_id}") from last_exc


def call_llm(inp: ScoringInput, enrich: bool = False) -> dict:
    label = "score+enrich" if enrich else "score"
    messages = [
        {"role": "system", "content": _make_system_prompt(enrich, is_ru=inp.is_ru)},
        {"role": "user", "content": _build_user_message(inp)},
    ]
    return call_with_fallback(messages, inp.vacancy_id, label)


def call_llm_enrich_only(inp: ScoringInput) -> dict:
    system = _BASE_RU_SYSTEM_PROMPT + "\n\n## ЧТО НУЖНО СДЕЛАТЬ\n" + _ENRICH_RU_INSTRUCTIONS
    system += "\n\n## ФОРМАТ ОТВЕТА\n\n" + _OUTPUT_ENRICH_ONLY
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": _build_user_message(inp)},
    ]
    return call_with_fallback(messages, inp.vacancy_id, "enrich_only")
