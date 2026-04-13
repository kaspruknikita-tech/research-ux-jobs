"""
Шаблоны постов для Telegram-каналов.
Формат: HTML (Telegram parse_mode="HTML").
"""

import html
import re

# hh.ru обрезает сниппеты на своей стороне — длину не контролируем.
# Иногда возвращают несколько точек подряд (......) — нормализуем.
_DOTS_RE = re.compile(r"\.{2,}")

CURRENCY_SYMBOLS = {
    "RUR": "₽",
    "RUB": "₽",
    "USD": "$",
    "EUR": "€",
    "KZT": "₸",
    "BYR": "Br",
    "BYN": "Br",
    "UAH": "₴",
    "GEL": "₾",
}


def _format_salary(vacancy: dict) -> str | None:
    sal_min = vacancy.get("salary_min")
    sal_max = vacancy.get("salary_max")
    currency_code = (vacancy.get("currency") or "").upper()
    currency = CURRENCY_SYMBOLS.get(currency_code, currency_code)

    def fmt(n: int) -> str:
        return f"{n:,}".replace(",", " ")

    if sal_min and sal_max:
        return f"{fmt(sal_min)} — {fmt(sal_max)} {currency}".strip()
    if sal_min:
        return f"от {fmt(sal_min)} {currency}".strip()
    if sal_max:
        return f"до {fmt(sal_max)} {currency}".strip()
    return None


def format_ru(vacancy: dict) -> str:
    """Шаблон поста для РФ-канала."""
    title = html.escape(vacancy.get("title") or "")
    company = html.escape(vacancy.get("company") or "")
    location = html.escape(vacancy.get("location") or "")
    work_format = vacancy.get("work_format") or ""

    # Заголовок: "Title в Компания"
    header = f"<b>{title}</b>"
    if company:
        header += f" в {company}"

    lines = [header, ""]

    # Инфо-строка: формат · город (пропускаем если оба пустые)
    info_parts = [p for p in [work_format, location] if p]
    if info_parts:
        lines.append("🔹 " + " · ".join(info_parts))

    # Зарплата (пропускаем если не указана)
    salary = _format_salary(vacancy)
    if salary:
        lines.append(f"🔹 {salary}")

    # Сниппет — хранится как "requirement | responsibility"
    # Текст обрывается на стороне hh.ru, длину не контролируем
    snippet = vacancy.get("snippet") or ""
    if snippet:
        parts = [p.strip() for p in snippet.split(" | ", 1) if p.strip()]
        cleaned = [_DOTS_RE.sub("…", p) for p in parts]
        lines.append("")
        lines.append("\n".join(html.escape(p) for p in cleaned))

    lines.append("")
    lines.append(f'👀 <a href="{vacancy["url"]}">Откликнуться на hh.ru</a>')

    return "\n".join(lines)


def format_global(vacancy: dict) -> str:
    """Шаблон поста для глобального канала (английский)."""
    title = html.escape(vacancy.get("title") or "")
    company = html.escape(vacancy.get("company") or "")
    location = html.escape(vacancy.get("location") or "")
    work_format = vacancy.get("work_format") or ""

    header = f"<b>{title}</b>"
    if company:
        header += f" at {company}"

    lines = [header, ""]

    info_parts = [p for p in [work_format, location] if p]
    if info_parts:
        lines.append("🔹 " + " · ".join(info_parts))

    salary = _format_salary(vacancy)
    if salary:
        lines.append(f"🔹 {salary}")

    snippet = vacancy.get("snippet") or ""
    if snippet:
        parts = [p.strip() for p in snippet.split(" | ", 1) if p.strip()]
        cleaned = [_DOTS_RE.sub("…", p) for p in parts]
        lines.append("")
        lines.append("\n".join(html.escape(p) for p in cleaned))

    lines.append("")
    lines.append(f'👀 <a href="{vacancy["url"]}">Apply</a>')

    return "\n".join(lines)
