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


def _smart_bullet(text: str) -> str:
    return text


def _parse_sections(raw_html: str) -> dict:
    """Разбирает HTML на секции: intro + именованные разделы с буллетами.
    Если HTML-структуры нет (plain text) — возвращает текст как intro."""
    if not raw_html:
        return {}

    soup = BeautifulSoup(raw_html, "html.parser")

    # Adzuna оборачивает контент в <section> или <div> — заходим внутрь
    top_tags = [c for c in soup.children if hasattr(c, "name") and c.name]
    root = top_tags[0] if len(top_tags) == 1 and top_tags[0].name in ("section", "div", "article") else soup

    sections = {}
    current = None
    intro = ""

    for tag in root.children:
        if not hasattr(tag, "name"):
            continue

        # Текстовая нода — может быть заголовком (напр. "Highlights", "About the role")
        if tag.name is None:
            text = str(tag).strip()
            if text and len(text) < 80 and not text.endswith("?") and text not in sections:
                current = text.rstrip(":")
                sections[current] = []
            continue

        if tag.name == "p":
            strong = tag.find("strong") or tag.find("b")
            text = tag.get_text().strip()
            if not text:
                continue
            # Заголовок: короткий (<= 60 символов), не вопрос, есть bold или двоеточие в конце
            is_header = (strong and len(text) <= 60 and not text.endswith("?")) or text.endswith(":")
            if is_header:
                current = text.rstrip(":")
                sections[current] = []
            elif not strong and not intro:
                intro = _first_sentence(text)

        elif tag.name in ("strong", "b"):
            # Голый <strong> без <p> — тоже может быть заголовком раздела
            text = tag.get_text().strip().rstrip(":")
            if text and len(text) < 80:
                current = text
                sections[current] = []

        elif tag.name in ("ul", "ol") and current:
            for li in tag.find_all("li", recursive=False):
                text = li.get_text().strip()
                if text:
                    sections[current].append(text)

    if intro:
        sections["__intro__"] = intro
    elif not sections:
        # Plain text без HTML-структуры (например, Adzuna)
        plain = soup.get_text(" ", strip=True)
        if plain:
            sections["__intro__"] = _first_sentence(plain)

    return sections


def _fmt_bullets(items: list, n: int = 5) -> str:
    return "\n".join("— " + _smart_bullet(i) for i in items[:n])


def _fmt_conditions(items: list, n: int = 5) -> str:
    return ", ".join(i.split("(")[0].split(",")[0].strip().rstrip(";.") for i in items[:n])


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
                          any(w in k.lower() for w in [
                              "обязанност", "задач", "responsi", "duties",
                              "нужно будет делать", "будете делать", "нужно делать",
                              "что делать", "функции", "чем предстоит",
                              "what you'll do", "what you will do", "you will be responsible",
                              "role overview", "the role", "your role",
                          ])), None)
        reqs_key = next((k for k in sections if k != "__intro__" and k != tasks_key and
                         any(w in k.lower() for w in [
                             "требован", "require", "qualif", "опыт",
                             "нам важно", "для нас важно", "что важно",
                             "ожидаем", "ищем", "нам нужен", "нам нужна",
                             "what we're looking for", "what you'll need", "you'll need",
                             "to be successful", "about you", "who you are",
                         ])), None)
        cond_key = next((k for k in sections if k != "__intro__" and
                         any(w in k.lower() for w in [
                             "услови", "offer", "benefit", "мы предлага",
                             "предлагаем", "работа с нами", "у нас вы",
                             "что мы даём", "что даём", "что получите",
                             "what we offer", "perks", "compensation", "why join",
                             "highlights",
                         ])), None)

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
