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


def _gc():
    creds_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
    if creds_json:
        creds_dict = json.loads(creds_json)
        creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
        return gspread.authorize(creds)
    return gspread.service_account(filename=config.GOOGLE_CREDENTIALS_FILE)


def _get_sheet(name: str = None):
    sheet_name = name or config.GOOGLE_SHEET_NAME
    spreadsheet = _gc().open_by_key(config.GOOGLE_SHEET_ID)
    try:
        sheet = spreadsheet.worksheet(sheet_name)
    except gspread.WorksheetNotFound:
        sheet = spreadsheet.add_worksheet(
            title=sheet_name,
            rows=2000,
            cols=len(HEADERS),
        )
        sheet.append_row(HEADERS)
        logger.info("Создан лист: %s", sheet_name)
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


def _export(vacancies: list[dict], sheet_name: str) -> None:
    if not vacancies:
        return

    try:
        sheet = _get_sheet(sheet_name)
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
            logger.info("Добавлено в '%s': %d вакансий", sheet_name, len(new_rows))

    except Exception as e:
        logger.error("Ошибка экспорта в '%s': %s", sheet_name, e)


def export_to_sheets(vacancies: list[dict]) -> None:
    _export(vacancies, config.GOOGLE_SHEET_NAME)


def export_rejected_to_sheets(vacancies: list[dict]) -> None:
    _export(vacancies, "Rejected")
