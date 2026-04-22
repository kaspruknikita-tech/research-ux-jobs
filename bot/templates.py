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


def _first_sentence(text: str, max_len: int = 200) -> str:
    cut = text[:max_len]
    dot = cut.rfind(". ")
    if dot > 60:
        return cut[:dot + 1]
    return cut


def _smart_bullet(text: str, max_len: int = 65) -> str:
    if ":" in text:
        label = text.split(":")[0].strip()
        if len(label) <= max_len:
            return label
    if len(text) > max_len and "," in text:
        before_comma = text.split(",")[0].strip()
        if 20 <= len(before_comma) <= max_len:
            return before_comma
    return text if len(text) <= max_len else text[:max_len].rsplit(" ", 1)[0] + "…"


def _parse_sections(raw_html: str) -> dict:
    """Разбирает HTML на секции: intro + именованные разделы с буллетами."""
    if not raw_html:
        return {}

    soup = BeautifulSoup(raw_html, "html.parser")
    sections = {}
    current = None
    intro = ""

    for tag in soup.children:
        if not hasattr(tag, "name") or tag.name is None:
            continue

        if tag.name == "p":
            strong = tag.find("strong") or tag.find("b")
            text = tag.get_text().strip()
            if not text:
                continue
            if strong or text.endswith(":"):
                current = text.rstrip(":")
                sections[current] = []
            elif not intro:
                intro = _first_sentence(text)

        elif tag.name in ("ul", "ol") and current:
            for li in tag.find_all("li", recursive=False):
                text = li.get_text().strip()
                if text:
                    sections[current].append(text)

    if intro:
        sections["__intro__"] = intro
    return sections


def _fmt_bullets(items: list, n: int = 5) -> str:
    return "\n".join("— " + _smart_bullet(i) for i in items[:n])


def _fmt_conditions(items: list, n: int = 5) -> str:
    return ", ".join(i.split("(")[0].split(",")[0].strip() for i in items[:n])


def _build_post(vacancy: dict, apply_label: str, is_ru: bool) -> str:
    title = html.escape(vacancy.get("title") or "")
    company = html.escape(vacancy.get("company") or "")
    location = html.escape(vacancy.get("location") or "")
    work_format = vacancy.get("work_format") or ""

    header = f"<b>{title}</b>"
    if company:
        header += f" в {company}" if is_ru else f" at {company}"

    lines = [header, ""]

    info_parts = [p for p in [work_format, location] if p]
    if info_parts:
        lines.append("📍 " + " · ".join(info_parts))

    salary = _format_salary(vacancy)
    if salary:
        lines.append(f"💰 {salary}")

    description = vacancy.get("description") or ""
    snippet = vacancy.get("snippet") or ""

    if description:
        sections = _parse_sections(description)

        intro = sections.get("__intro__")
        if intro:
            lines += ["", "<b>О роли</b>", html.escape(intro)]

        tasks_key = next((k for k in sections if k != "__intro__" and
                          any(w in k.lower() for w in ["обязанност", "задач", "responsi", "duties"])), None)
        reqs_key = next((k for k in sections if k != "__intro__" and
                         any(w in k.lower() for w in ["требован", "require", "qualif", "опыт"])), None)
        cond_key = next((k for k in sections if k != "__intro__" and
                         any(w in k.lower() for w in ["услови", "offer", "benefit", "мы предлага"])), None)

        if tasks_key and sections[tasks_key]:
            lines += ["", f"<b>{'Задачи' if is_ru else 'Responsibilities'}</b>",
                      html.escape(_fmt_bullets(sections[tasks_key]))]

        if reqs_key and sections[reqs_key]:
            lines += ["", f"<b>{'Требования' if is_ru else 'Requirements'}</b>",
                      html.escape(_fmt_bullets(sections[reqs_key]))]

        if cond_key and sections[cond_key]:
            lines += ["", f"<b>{'Условия' if is_ru else 'Benefits'}</b>",
                      html.escape(_fmt_conditions(sections[cond_key]))]

    elif snippet:
        lines += ["", html.escape(snippet)]

    lines += ["", f'🔗 <a href="{vacancy["url"]}">{apply_label}</a>']

    return "\n".join(lines)


def format_ru(vacancy: dict) -> str:
    return _build_post(vacancy, "Откликнуться на hh.ru", is_ru=True)


def format_global(vacancy: dict) -> str:
    return _build_post(vacancy, "Apply", is_ru=False)
