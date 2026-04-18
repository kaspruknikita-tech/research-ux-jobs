"""
Конфигурация проекта.
Читает переменные окружения из .env и предоставляет их как атрибуты.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Корень проекта — папка, где лежит этот файл
BASE_DIR = Path(__file__).resolve().parent

# Загружаем .env из корня проекта
load_dotenv(BASE_DIR / ".env")


# --- Telegram ---
TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHANNEL_RU: str = os.getenv("TELEGRAM_CHANNEL_RU", "")
TELEGRAM_CHANNEL_GLOBAL: str = os.getenv("TELEGRAM_CHANNEL_GLOBAL", "")
TELEGRAM_MODERATION_CHAT: str = os.getenv("TELEGRAM_MODERATION_CHAT", "")
TELEGRAM_ALERT_CHAT: str = os.getenv("TELEGRAM_ALERT_CHAT", "")

# --- hh.ru ---
HH_USER_AGENT: str = os.getenv("HH_USER_AGENT", "VacancyParser/0.1")
HH_CLIENT_ID: str = os.getenv("HH_CLIENT_ID", "")
HH_CLIENT_SECRET: str = os.getenv("HH_CLIENT_SECRET", "")

# --- Планировщик ---
PARSE_INTERVAL_MINUTES: int = int(os.getenv("PARSE_INTERVAL_MINUTES", "30"))

# --- База данных ---
DATABASE_URL: str = os.getenv("DATABASE_URL", "")

# --- Логирование ---
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")


def validate() -> list[str]:
    """Проверяет, что все обязательные настройки заполнены.
    Возвращает список ошибок (пустой = всё ок)."""
    errors = []
    if not DATABASE_URL:
        errors.append("DATABASE_URL не задан в .env")
    if not GOOGLE_SHEET_ID:
        errors.append("GOOGLE_SHEET_ID не задан в .env")
    return errors

# --- Google Sheets ---
GOOGLE_CREDENTIALS_FILE: str = str(BASE_DIR / "google_credentials.json")
GOOGLE_SHEET_ID: str = os.getenv("GOOGLE_SHEET_ID", "")
GOOGLE_SHEET_NAME: str = "Vacancies"
