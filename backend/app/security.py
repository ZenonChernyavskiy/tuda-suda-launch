import base64
import hashlib
import hmac
import json
import time
from urllib.parse import parse_qsl

from fastapi import HTTPException, status

from .config import (
    AUTH_TOKEN_SECRET,
    AUTH_TOKEN_TTL_HOURS,
    TELEGRAM_INIT_DATA_MAX_AGE_SECONDS,
)


def _b64encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _b64decode(raw: str) -> bytes:
    padding = "=" * (-len(raw) % 4)
    return base64.urlsafe_b64decode(raw + padding)


def create_access_token(telegram_id: str) -> str:
    payload = {
        "telegram_id": telegram_id,
        "exp": int(time.time()) + AUTH_TOKEN_TTL_HOURS * 3600,
    }
    payload_raw = json.dumps(payload, separators=(",", ":")).encode()
    payload_part = _b64encode(payload_raw)
    signature = hmac.new(
        AUTH_TOKEN_SECRET.encode(),
        payload_part.encode(),
        hashlib.sha256,
    ).digest()
    return f"{payload_part}.{_b64encode(signature)}"


def decode_access_token(token: str) -> str:
    try:
        payload_part, signature_part = token.split(".", 1)
        expected_signature = hmac.new(
            AUTH_TOKEN_SECRET.encode(),
            payload_part.encode(),
            hashlib.sha256,
        ).digest()
        actual_signature = _b64decode(signature_part)
        if not hmac.compare_digest(expected_signature, actual_signature):
            raise ValueError("bad signature")
        payload = json.loads(_b64decode(payload_part))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный токен авторизации",
        ) from exc

    if int(payload.get("exp", 0)) < int(time.time()):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Токен авторизации истек",
        )

    telegram_id = payload.get("telegram_id")
    if not telegram_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный токен авторизации",
        )
    return str(telegram_id)


def parse_telegram_init_data(init_data: str, bot_token: str) -> dict:
    if not bot_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Для проверки Telegram initData укажите TELEGRAM_BOT_TOKEN",
        )

    parsed_data = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = parsed_data.pop("hash", None)
    if not received_hash:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="В initData нет hash",
        )

    data_check_string = "\n".join(
        f"{key}={value}" for key, value in sorted(parsed_data.items())
    )
    # Проверка подписи соответствует алгоритму Telegram WebApp initData.
    secret_key = hmac.new(
        b"WebAppData",
        bot_token.encode(),
        hashlib.sha256,
    ).digest()
    calculated_hash = hmac.new(
        secret_key,
        data_check_string.encode(),
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(calculated_hash, received_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Telegram initData не прошел проверку",
        )

    try:
        auth_date = int(parsed_data.get("auth_date", "0"))
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Некорректный auth_date в initData",
        ) from exc

    if TELEGRAM_INIT_DATA_MAX_AGE_SECONDS > 0:
        now = int(time.time())
        if auth_date <= 0 or now - auth_date > TELEGRAM_INIT_DATA_MAX_AGE_SECONDS:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Telegram initData устарел",
            )

    user_raw = parsed_data.get("user")
    if not user_raw:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="В initData нет данных пользователя",
        )

    try:
        user = json.loads(user_raw)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Некорректные данные пользователя Telegram",
        ) from exc

    if "id" not in user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="В данных пользователя Telegram нет id",
        )

    return {
        "telegram_id": str(user["id"]),
        "username": user.get("username"),
        "first_name": user.get("first_name"),
        "photo_url": user.get("photo_url"),
        "start_param": parsed_data.get("start_param") or parsed_data.get("startapp"),
    }
