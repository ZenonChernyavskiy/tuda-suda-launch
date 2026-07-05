from pathlib import Path
from decimal import Decimal
import logging
import os

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'tuda_suda.db'}")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
ALLOW_MOCK_AUTH = os.getenv("ALLOW_MOCK_AUTH", "true").lower() == "true"
APP_ENV = os.getenv("APP_ENV", "development").lower()
IS_PRODUCTION = APP_ENV == "production"
AUTO_INIT_DB = os.getenv("AUTO_INIT_DB", "false" if IS_PRODUCTION else "true").lower() == "true"
AUTH_TOKEN_SECRET = os.getenv("AUTH_TOKEN_SECRET", "dev-secret-change-me")
AUTH_TOKEN_TTL_HOURS = int(os.getenv("AUTH_TOKEN_TTL_HOURS", "720"))
TELEGRAM_INIT_DATA_MAX_AGE_SECONDS = int(
    os.getenv("TELEGRAM_INIT_DATA_MAX_AGE_SECONDS", "86400")
)
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "")
INITIAL_BALANCE = int(os.getenv("INITIAL_BALANCE", "100"))
DAILY_SEND_LIMIT = int(os.getenv("DAILY_SEND_LIMIT", "20"))
GIFT_FEE_BPS = int(os.getenv("GIFT_FEE_BPS", "0"))
TREASURY_USER_ID = os.getenv("TREASURY_USER_ID")
TREASURY_USER_ID = int(TREASURY_USER_ID) if TREASURY_USER_ID else None
PURCHASE_FEE_PERCENT = Decimal(
    os.getenv("PURCHASE_FEE_PERCENT", os.getenv("BUY_COMMISSION_PERCENT", "1"))
)
BUY_COMMISSION_PERCENT = PURCHASE_FEE_PERCENT
TRANSFER_COMMISSION_PERCENT = Decimal(os.getenv("TRANSFER_COMMISSION_PERCENT", "10"))
TDSD_FIXED_PRICE_TON = Decimal(os.getenv("TDSD_FIXED_PRICE_TON", "0.1"))
TREASURY_WALLET_ADDRESS = os.getenv(
    "TREASURY_WALLET_ADDRESS",
    "UQAOgQnt-ZMtAsMWtnL9zFs1Id27b8L3gc35pvQZA4dmUZg6",
).strip()
HOT_WALLET_ADDRESS = os.getenv(
    "HOT_WALLET_ADDRESS",
    "UQCaKtJZrSwLgcYwGYSG9Qijyn73oRdXIinxx-zBQ752TXxo",
).strip()
HOT_WALLET_MNEMONIC = os.getenv("HOT_WALLET_MNEMONIC", "").strip()
HOT_WALLET_JETTON_TRANSFER_GAS_TON = Decimal(
    os.getenv("HOT_WALLET_JETTON_TRANSFER_GAS_TON", "0.08")
)
TON_NETWORK = os.getenv("TON_NETWORK", "testnet")
PROJECT_TON_WALLET = os.getenv("PROJECT_TON_WALLET", HOT_WALLET_ADDRESS).strip()
TONCENTER_API_URL = os.getenv(
    "TONCENTER_API_URL",
    "https://testnet.toncenter.com/api/v2",
).rstrip("/")
TONCENTER_API_KEY = os.getenv("TONCENTER_API_KEY", "")
TONCENTER_TX_LIMIT = int(os.getenv("TONCENTER_TX_LIMIT", "100"))
MIN_DEPOSIT_TON = Decimal(os.getenv("MIN_DEPOSIT_TON", "0.05"))
MAX_DEPOSIT_TON = Decimal(os.getenv("MAX_DEPOSIT_TON", "5"))
DEPOSIT_CONFIRMATION_TIMEOUT_MINUTES = int(
    os.getenv("DEPOSIT_CONFIRMATION_TIMEOUT_MINUTES", "30")
)
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
APP_VERSION = os.getenv("APP_VERSION", "0.8.0")
PUBLIC_APP_URL = os.getenv("PUBLIC_APP_URL", "")
PUBLIC_API_URL = os.getenv("PUBLIC_API_URL", "")
TDSD_ASSET_SYMBOL = os.getenv("TDSD_ASSET_SYMBOL", "TDSD").strip().upper()
TDSD_ASSET_NAME = os.getenv("TDSD_ASSET_NAME", "Tuda Suda Token").strip()
TDSD_DECIMALS = int(os.getenv("TDSD_DECIMALS", "9"))
TDSD_NETWORK = os.getenv("TDSD_NETWORK", "ton_testnet").strip()
TDSD_JETTON_MASTER_ADDRESS = os.getenv(
    "TDSD_JETTON_MASTER_ADDRESS",
    "EQBZkfdol6WOj-GXByKLeRlo70ktYIQnTA5Hq_gT6KVYvY3n",
).strip()
TDSD_PROJECT_JETTON_WALLET = os.getenv("TDSD_PROJECT_JETTON_WALLET", "").strip()
TDSD_DEPOSITS_ENABLED = os.getenv("TDSD_DEPOSITS_ENABLED", "false").lower() == "true"
SEED_TDSD_ASSET = os.getenv("SEED_TDSD_ASSET", "true").lower() == "true"
REFERRALS_ENABLED = os.getenv("REFERRALS_ENABLED", "true").lower() == "true"
REFERRAL_REWARD_PERCENT = Decimal(os.getenv("REFERRAL_REWARD_PERCENT", "10"))
REFERRAL_REWARD_ASSET_SYMBOL = os.getenv(
    "REFERRAL_REWARD_ASSET_SYMBOL",
    TDSD_ASSET_SYMBOL,
).strip().upper()
TELEGRAM_BOT_USERNAME = os.getenv("TELEGRAM_BOT_USERNAME", "tudasuda_tdsd_bot").strip().lstrip("@")
TELEGRAM_MINI_APP_SHORT_NAME = os.getenv("TELEGRAM_MINI_APP_SHORT_NAME", "").strip()
FRONTEND_URL = os.getenv("FRONTEND_URL", PUBLIC_APP_URL or "https://app.tudasuda.tech").strip()

raw_origins = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173",
)
CORS_ORIGINS = [origin.strip() for origin in raw_origins.split(",") if origin.strip()]


def configure_logging() -> None:
    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL, logging.INFO),
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )


def validate_production_settings() -> None:
    errors: list[str] = []
    from .ton import TonAddressValidationError, normalize_ton_wallet_address

    if IS_PRODUCTION:
        if DATABASE_URL.startswith("sqlite"):
            errors.append("DATABASE_URL must use PostgreSQL in production")
        if ALLOW_MOCK_AUTH:
            errors.append("ALLOW_MOCK_AUTH must be false in production")
        if not TELEGRAM_BOT_TOKEN:
            errors.append("TELEGRAM_BOT_TOKEN is required in production")
        if AUTH_TOKEN_SECRET in {"", "dev-secret-change-me", "change-me-for-local-demo"}:
            errors.append("AUTH_TOKEN_SECRET must be changed in production")
        if not ADMIN_API_KEY:
            errors.append("ADMIN_API_KEY is required in production")
        if not CORS_ORIGINS or "*" in CORS_ORIGINS:
            errors.append("CORS_ORIGINS must be explicit in production")
        if any(
            origin.startswith(("http://localhost", "http://127.", "http://0.0.0.0"))
            for origin in CORS_ORIGINS
        ):
            errors.append("CORS_ORIGINS must not contain local origins in production")
        if any(not origin.startswith("https://") for origin in CORS_ORIGINS):
            errors.append("CORS_ORIGINS must use HTTPS in production")
        if not PUBLIC_APP_URL.startswith("https://"):
            errors.append("PUBLIC_APP_URL must be HTTPS in production")
        if not PUBLIC_API_URL.startswith("https://"):
            errors.append("PUBLIC_API_URL must be HTTPS in production")
    if GIFT_FEE_BPS < 0 or GIFT_FEE_BPS > 10000:
        errors.append("GIFT_FEE_BPS must be between 0 and 10000")
    for env_name, value in (
        ("PURCHASE_FEE_PERCENT", PURCHASE_FEE_PERCENT),
        ("TRANSFER_COMMISSION_PERCENT", TRANSFER_COMMISSION_PERCENT),
        ("REFERRAL_REWARD_PERCENT", REFERRAL_REWARD_PERCENT),
    ):
        if value < 0 or value >= 100:
            errors.append(f"{env_name} must be between 0 and 100")
    if TDSD_FIXED_PRICE_TON <= 0:
        errors.append("TDSD_FIXED_PRICE_TON must be greater than 0")
    if HOT_WALLET_JETTON_TRANSFER_GAS_TON <= 0:
        errors.append("HOT_WALLET_JETTON_TRANSFER_GAS_TON must be greater than 0")
    if not REFERRAL_REWARD_ASSET_SYMBOL:
        errors.append("REFERRAL_REWARD_ASSET_SYMBOL is required")
    if REFERRALS_ENABLED and IS_PRODUCTION and not TELEGRAM_BOT_USERNAME:
        errors.append("TELEGRAM_BOT_USERNAME is required when referrals are enabled in production")
    if TDSD_DECIMALS < 0 or TDSD_DECIMALS > 18:
        errors.append("TDSD_DECIMALS must be between 0 and 18")
    for env_name, value in (
        ("PROJECT_TON_WALLET", PROJECT_TON_WALLET),
        ("TREASURY_WALLET_ADDRESS", TREASURY_WALLET_ADDRESS),
        ("HOT_WALLET_ADDRESS", HOT_WALLET_ADDRESS),
        ("TDSD_JETTON_MASTER_ADDRESS", TDSD_JETTON_MASTER_ADDRESS),
        ("TDSD_PROJECT_JETTON_WALLET", TDSD_PROJECT_JETTON_WALLET),
    ):
        if not value:
            continue
        try:
            normalize_ton_wallet_address(value)
        except TonAddressValidationError as exc:
            errors.append(f"{env_name} is invalid: {exc}")
    if TDSD_DEPOSITS_ENABLED and (
        not TDSD_JETTON_MASTER_ADDRESS or not TDSD_PROJECT_JETTON_WALLET
    ):
        errors.append(
            "TDSD_JETTON_MASTER_ADDRESS and TDSD_PROJECT_JETTON_WALLET are required when TDSD_DEPOSITS_ENABLED=true"
        )
    if not TDSD_DEPOSITS_ENABLED and not PROJECT_TON_WALLET:
        errors.append("PROJECT_TON_WALLET is required when TDSD_DEPOSITS_ENABLED=false")
    if errors:
        raise RuntimeError("Invalid production settings: " + "; ".join(errors))
