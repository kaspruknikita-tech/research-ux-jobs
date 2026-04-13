"""
Экспорт вакансий в Google Sheets.
"""

import os
import json
import logging
import gspread
from datetime import datetime
from google.oauth2.service_account import Credentials
import config

logger = logging.getLogger(__name__)

HEADERS = [
    "external_id", "Источник", "Название", "Компания",
    "Зарплата мин", "Зарплата макс", "Валюта",
    "Локация", "Формат работы", "Канал", "Статус", "Ссылка", "Дата парсинга"
]

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


def _get_sheet():
    # Пробуем сначала переменную окружения (Railway),
    # если нет - читаем из файла (локально)
    creds_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
    if creds_json:
        creds_dict = json.loads(creds_json)
        creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
        gc = gspread.authorize(creds)
    else:
        gc = gspread.service_account(filename=config.GOOGLE_CREDENTIALS_FILE)

    spreadsheet = gc.open_by_key(config.GOOGLE_SHEET_ID)
    try:
        sheet = spreadsheet.worksheet(config.GOOGLE_SHEET_NAME)
    except gspread.WorksheetNotFound:
        sheet = spreadsheet.add_worksheet(
            title=config.GOOGLE_SHEET_NAME,
            rows=2000,
            cols=len(HEADERS)
        )
        sheet.append_row(HEADERS)
        logger.info("Создан лист: %s", config.GOOGLE_SHEET_NAME)
    return sheet


def _ensure_headers(sheet):
    first_row = sheet.row_values(1)
    if first_row != HEADERS:
        sheet.insert_row(HEADERS, index=1)


def _to_row(v: dict) -> list:
    return [
        v.get("external_id", ""),
        v.get("source", "hh.ru"),
        v.get("title", ""),
        v.get("company", ""),
        v.get("salary_min", "") or "",
        v.get("salary_max", "") or "",
        v.get("currency", "") or "",
        v.get("location", ""),
        v.get("work_format", ""),
        v.get("channel", ""),
        v.get("status", "new"),
        v.get("url", ""),
        v.get("parsed_at", datetime.now().isoformat()),
    ]


def export_to_sheets(vacancies: list[dict]) -> None:
    if not vacancies:
        logger.info("Нет вакансий для экспорта в Sheets")
        return

    try:
        sheet = _get_sheet()
        _ensure_headers(sheet)

        existing_urls = set(sheet.col_values(12))

        new_rows = []
        for v in vacancies:
            url = v.get("url", "")
            if url and url not in existing_urls:
                new_rows.append(_to_row(v))
                existing_urls.add(url)

        if new_rows:
            sheet.append_rows(new_rows, value_input_option="USER_ENTERED")
            logger.info("Добавлено в Sheets: %d вакансий", len(new_rows))
        else:
            logger.info("Все вакансии уже есть в таблице")

    except Exception as e:
        logger.error("Ошибка экспорта в Sheets: %s", e)
