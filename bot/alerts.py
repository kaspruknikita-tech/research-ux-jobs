"""
Алерты в Telegram-группу мониторинга.
"""

import logging

import requests

import config

logger = logging.getLogger(__name__)

ALERT_MENTION = "@pashagots"


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


def _check_openrouter_balance() -> None:
    if not config.OPENROUTER_API_KEY:
        return
    try:
        resp = requests.get(
            "https://openrouter.ai/api/v1/auth/key",
            headers={"Authorization": f"Bearer {config.OPENROUTER_API_KEY}"},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json().get("data", {})
        limit = data.get("limit")
        usage = data.get("usage", 0.0)
        if limit is None:
            return
        remaining = round(limit - usage, 4)
        if remaining < config.OPENROUTER_BALANCE_THRESHOLD:
            send_alert(
                f"[OPENROUTER] Баланс заканчивается!\n"
                f"Осталось: ${remaining:.2f} (порог: ${config.OPENROUTER_BALANCE_THRESHOLD})\n"
                f"{ALERT_MENTION}"
            )
            logger.warning("OpenRouter баланс низкий: $%.4f", remaining)
        else:
            logger.info("OpenRouter баланс OK: $%.4f", remaining)
    except Exception:
        logger.exception("Не удалось проверить баланс OpenRouter")


def _check_railway_balance() -> None:
    if not config.RAILWAY_API_TOKEN:
        return
    try:
        query = "{ me { creditBalance } }"
        resp = requests.post(
            "https://backboard.railway.app/graphql/v2",
            json={"query": query},
            headers={
                "Authorization": f"Bearer {config.RAILWAY_API_TOKEN}",
                "Content-Type": "application/json",
            },
            timeout=10,
        )
        resp.raise_for_status()
        payload = resp.json()
        errors = payload.get("errors")
        if errors:
            logger.warning("Railway API errors: %s", errors)
            return
        balance_cents = payload.get("data", {}).get("me", {}).get("creditBalance")
        if balance_cents is None:
            logger.warning("Railway: creditBalance не найден в ответе: %s", payload)
            return
        # Railway возвращает баланс в центах
        balance_usd = balance_cents / 100.0
        if balance_usd < config.RAILWAY_BALANCE_THRESHOLD:
            send_alert(
                f"[RAILWAY] Баланс заканчивается!\n"
                f"Осталось: ${balance_usd:.2f} (порог: ${config.RAILWAY_BALANCE_THRESHOLD})\n"
                f"{ALERT_MENTION}"
            )
            logger.warning("Railway баланс низкий: $%.2f", balance_usd)
        else:
            logger.info("Railway баланс OK: $%.2f", balance_usd)
    except Exception:
        logger.exception("Не удалось проверить баланс Railway")


def check_balances() -> None:
    _check_openrouter_balance()
    _check_railway_balance()
