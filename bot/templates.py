"""
Шаблоны постов для Telegram-каналов.
Формат: HTML (Telegram parse_mode="HTML").
"""

import html
from bs4 import BeautifulSoup

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

# Telegram ограничивает длину сообщения 4096 символами.
# Оставляем запас на заголовок, зарплату и ссылку.
_MAX_DESCRIPTION_CHARS = 3000


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


def _parse_description(raw_html: str) -> str:
    """Конвертирует HTML-описание вакансии в чистый текст с разметкой Telegram.

    hh.ru возвращает описание как HTML со структурой:
      <p><strong>Обязанности:</strong></p><ul><li>...</li></ul>

    Превращаем в:
      <b>Обязанности:</b>
      — пункт 1
      — пункт 2
    """
    if not raw_html:
        return ""

    soup = BeautifulSoup(raw_html, "html.parser")
    lines = []

    for tag in soup.children:
        if not hasattr(tag, "name") or tag.name is None:
            continue

        if tag.name == "p":
            text = tag.get_text().strip()
            if not text:
                continue
            # Заголовок секции — жирный или заканчивается на ":"
            strong = tag.find("strong") or tag.find("b")
            if strong or text.endswith(":"):
                label = text.rstrip(":")
                lines.append(f"\n<b>{html.escape(label)}:</b>")
            else:
                lines.append(html.escape(text))

        elif tag.name in ("ul", "ol"):
            for li in tag.find_all("li", recursive=False):
                text = li.get_text().strip()
                if text:
                    lines.append(f"— {html.escape(text)}")

    result = "\n".join(lines).strip()

    # Обрезаем если слишком длинный
    if len(result) > _MAX_DESCRIPTION_CHARS:
        result = result[:_MAX_DESCRIPTION_CHARS].rsplit("\n", 1)[0] + "\n…"

    return result


def _build_post(vacancy: dict, apply_label: str) -> str:
    title = html.escape(vacancy.get("title") or "")
    company = html.escape(vacancy.get("company") or "")
    location = html.escape(vacancy.get("location") or "")
    work_format = vacancy.get("work_format") or ""

    header = f"<b>{title}</b>"
    if company:
        header += f" в {company}" if apply_label == "Откликнуться на hh.ru" else f" at {company}"

    lines = [header, ""]

    info_parts = [p for p in [work_format, location] if p]
    if info_parts:
        lines.append("🔹 " + " · ".join(info_parts))

    salary = _format_salary(vacancy)
    if salary:
        lines.append(f"🔹 {salary}")

    # Описание: полный текст если есть, иначе сниппет
    description = vacancy.get("description") or ""
    snippet = vacancy.get("snippet") or ""

    if description:
        body = _parse_description(description)
        if body:
            lines.append("")
            lines.append(body)
    elif snippet:
        lines.append("")
        lines.append(html.escape(snippet))

    lines.append("")
    lines.append(f'👀 <a href="{vacancy["url"]}">{apply_label}</a>')

    return "\n".join(lines)


def format_ru(vacancy: dict) -> str:
    return _build_post(vacancy, "Откликнуться на hh.ru")


def format_global(vacancy: dict) -> str:
    return _build_post(vacancy, "Apply")
