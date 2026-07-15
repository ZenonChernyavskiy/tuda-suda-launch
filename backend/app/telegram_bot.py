import json
import logging
import urllib.error
import urllib.request

from .config import FRONTEND_URL, TELEGRAM_BOT_TOKEN


logger = logging.getLogger("tuda_suda.telegram_bot")
TELEGRAM_API_TIMEOUT_SECONDS = 8


def send_asset_gift_received_notification(
    chat_id: str,
    amount_display: str,
    asset_symbol: str = "TDSD",
) -> None:
    if not TELEGRAM_BOT_TOKEN:
        logger.warning("Telegram gift notification skipped: bot token is not configured")
        return

    normalized_chat_id = str(chat_id or "").strip()
    if not normalized_chat_id or normalized_chat_id.startswith("system:"):
        return

    payload = {
        "chat_id": normalized_chat_id,
        "text": f"Вам пришел подарок {amount_display} {asset_symbol}",
        "reply_markup": {
            "inline_keyboard": [
                [
                    {
                        "text": "Посмотреть",
                        "web_app": {
                            "url": FRONTEND_URL,
                        },
                    },
                ],
            ],
        },
    }
    request = urllib.request.Request(
        f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=TELEGRAM_API_TIMEOUT_SECONDS,
        ) as response:
            if response.status >= 400:
                logger.warning(
                    "Telegram gift notification failed chat_id=%s status=%s",
                    normalized_chat_id,
                    response.status,
                )
    except urllib.error.HTTPError as exc:
        logger.warning(
            "Telegram gift notification failed chat_id=%s status=%s",
            normalized_chat_id,
            exc.code,
        )
    except urllib.error.URLError as exc:
        logger.warning(
            "Telegram gift notification unavailable chat_id=%s reason=%s",
            normalized_chat_id,
            exc.reason,
        )
    except TimeoutError:
        logger.warning(
            "Telegram gift notification timed out chat_id=%s",
            normalized_chat_id,
        )
    except Exception as exc:
        logger.warning(
            "Telegram gift notification failed chat_id=%s exception_type=%s",
            normalized_chat_id,
            type(exc).__name__,
        )
