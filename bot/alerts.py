"""
Алерты в Telegram-группу мониторинга.
"""

import logging

import requests

import config

logger = logging.getLogger(__name__)


def _api(method: str, **kwargs) -> dict:
    url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/{method}"
    resp = requests.post(url, json=kwargs, timeout=10)
    data = resp.json()
    if not data.get("ok"):
        raise RuntimeError(f"Telegram API error [{method}]: {data.get('description')}")
    return data


def send_alert(text: str) -> None:
    if not config.TELEGRAM_ALERT_CHAT or not config.TELEGRAM_BOT_TOKEN:
        return
    try:
        _api("sendMessage", chat_id=config.TELEGRAM_ALERT_CHAT, text=text)
    except Exception:
        logger.exception("Не удалось отправить алерт")
