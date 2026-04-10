"""
Шаблоны постов для Telegram-каналов.
Формат: HTML (Telegram parse_mode="HTML").
"""

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
    """Красиво форматирует зарплатную вилку."""
    sal_min = vacancy.get("salary_min")
    sal_max = vacancy.get("salary_max")
    currency_code = (vacancy.get("currency") or "").upper()
    currency = CURRENCY_SYMBOLS.get(currency_code, currency_code)

    def fmt(n: int) -> str:
        return f"{n:,}".replace(",", " ")

    if sal_min and sal_max:
        return f"{fmt(sal_min)} – {fmt(sal_max)} {currency}".strip()
    if sal_min:
        return f"от {fmt(sal_min)} {currency}".strip()
    if sal_max:
        return f"до {fmt(sal_max)} {currency}".strip()
    return None


def format_ru(vacancy: dict) -> str:
    """Шаблон поста для РФ-канала (русский язык)."""
    salary = _format_salary(vacancy)
    location = vacancy.get("location") or "не указан"
    work_format = vacancy.get("work_format") or ""
    company = vacancy.get("company") or "—"

    lines = [
        f"🔍 <b>{vacancy['title']}</b>",
        f"🏢 {company}",
    ]
    if salary:
        lines.append(f"💰 {salary}")
    lines.append(f"📍 {location}")
    if work_format:
        lines.append(f"🏠 {work_format}")
    lines.append("")
    lines.append(f"👉 <a href=\"{vacancy['url']}\">Откликнуться</a>")
    lines.append("")
    lines.append(f"#вакансия #{vacancy.get('source', 'unknown')}")

    return "\n".join(lines)


def format_global(vacancy: dict) -> str:
    """Шаблон поста для глобального канала (английский)."""
    salary = _format_salary(vacancy)
    location = vacancy.get("location") or "Remote"
    work_format = vacancy.get("work_format") or ""
    company = vacancy.get("company") or "—"

    lines = [
        f"🔍 <b>{vacancy['title']}</b>",
        f"🏢 {company}",
    ]
    if salary:
        lines.append(f"💰 {salary}")
    lines.append(f"📍 {location}")
    if work_format:
        lines.append(f"🏠 {work_format}")
    lines.append("")
    lines.append(f"👉 <a href=\"{vacancy['url']}\">Apply</a>")
    lines.append("")
    lines.append(f"#vacancy #{vacancy.get('source', 'unknown')}")

    return "\n".join(lines)
