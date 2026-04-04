"""
Шаблоны постов для Telegram-каналов.
Формат: HTML (Telegram parse_mode="HTML").
"""


def _format_salary(vacancy: dict) -> str:
    """Красиво форматирует зарплатную вилку."""
    sal_min = vacancy.get("salary_min")
    sal_max = vacancy.get("salary_max")
    currency = vacancy.get("currency", "")

    if sal_min and sal_max:
        return f"{sal_min:,} – {sal_max:,} {currency}".replace(",", " ")
    if sal_min:
        return f"от {sal_min:,} {currency}".replace(",", " ")
    if sal_max:
        return f"до {sal_max:,} {currency}".replace(",", " ")
    return "не указана"


def format_ru(vacancy: dict) -> str:
    """Шаблон поста для РФ-канала (русский язык)."""
    salary = _format_salary(vacancy)
    location = vacancy.get("location") or "не указан"
    work_format = vacancy.get("work_format") or ""
    company = vacancy.get("company") or "—"

    lines = [
        f"🔍 <b>{vacancy['title']}</b>",
        f"🏢 {company}",
        f"💰 {salary}",
        f"📍 {location}",
    ]
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
    company = vacancy.get("company") or "—"

    lines = [
        f"🔍 <b>{vacancy['title']}</b>",
        f"🏢 {company}",
        f"💰 {salary}",
        f"📍 {location}",
        "",
        f"👉 <a href=\"{vacancy['url']}\">Apply</a>",
        "",
        f"#vacancy #{vacancy.get('source', 'unknown')}",
    ]

    return "\n".join(lines)
