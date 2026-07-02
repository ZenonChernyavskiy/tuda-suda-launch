from datetime import datetime
from decimal import Decimal, ROUND_DOWN
import secrets
import string

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import models
from .config import (
    FRONTEND_URL,
    REFERRAL_REWARD_ASSET_SYMBOL,
    REFERRAL_REWARD_PERCENT,
    REFERRALS_ENABLED,
    TELEGRAM_BOT_USERNAME,
    TELEGRAM_MINI_APP_SHORT_NAME,
)


REFERRAL_PREFIX = "ref_"
REFERRAL_CODE_ALPHABET = string.ascii_uppercase + string.digits
REFERRAL_CODE_LENGTH = 8


def clean_referral_code(code: str | None) -> str | None:
    if not code:
        return None
    cleaned = code.strip()
    if cleaned.startswith(REFERRAL_PREFIX):
        cleaned = cleaned[len(REFERRAL_PREFIX) :]
    cleaned = cleaned.upper()
    if not cleaned or len(cleaned) > 16:
        return None
    if not all(char in REFERRAL_CODE_ALPHABET for char in cleaned):
        return None
    return cleaned


def generate_referral_code(db: Session) -> str:
    for _ in range(24):
        code = "".join(
            secrets.choice(REFERRAL_CODE_ALPHABET)
            for _ in range(REFERRAL_CODE_LENGTH)
        )
        exists = db.scalar(select(models.User.id).where(models.User.referral_code == code))
        if not exists:
            return code
    raise RuntimeError("Не удалось создать уникальный referral code")


def ensure_referral_code(db: Session, user: models.User) -> str:
    if user.referral_code:
        return user.referral_code
    user.referral_code = generate_referral_code(db)
    db.flush()
    return user.referral_code


def build_referral_link(referral_code: str) -> str:
    code = clean_referral_code(referral_code) or referral_code
    ref_param = f"{REFERRAL_PREFIX}{code}"
    if TELEGRAM_BOT_USERNAME and TELEGRAM_MINI_APP_SHORT_NAME:
        return (
            f"https://t.me/{TELEGRAM_BOT_USERNAME}/"
            f"{TELEGRAM_MINI_APP_SHORT_NAME}?startapp={ref_param}"
        )
    if TELEGRAM_BOT_USERNAME:
        return f"https://t.me/{TELEGRAM_BOT_USERNAME}?start={ref_param}"
    base_url = FRONTEND_URL.rstrip("/")
    return f"{base_url}?ref={ref_param}"


def apply_referral_on_first_login(
    db: Session,
    user: models.User,
    referral_param: str | None,
) -> models.User | None:
    if not REFERRALS_ENABLED or user.referred_by_user_id:
        return None

    referral_code = clean_referral_code(referral_param)
    if not referral_code:
        return None

    referrer = db.scalar(
        select(models.User).where(models.User.referral_code == referral_code)
    )
    if not referrer or referrer.id == user.id:
        return None

    user.referred_by_user_id = referrer.id
    user.referred_at = datetime.utcnow()
    return referrer


def calculate_referral_reward_units(purchase_amount_units: int) -> int:
    reward_units = (
        Decimal(int(purchase_amount_units))
        * REFERRAL_REWARD_PERCENT
        / Decimal("100")
    ).to_integral_value(rounding=ROUND_DOWN)
    return int(reward_units)


def _get_or_create_balance(
    db: Session,
    user_id: int,
    asset_id: int,
) -> models.AssetBalance:
    balance = db.scalar(
        select(models.AssetBalance).where(
            models.AssetBalance.user_id == user_id,
            models.AssetBalance.asset_id == asset_id,
        )
    )
    if balance:
        return balance

    balance = models.AssetBalance(user_id=user_id, asset_id=asset_id, balance_units=0)
    db.add(balance)
    db.flush()
    return balance


def credit_referral_reward_for_purchase(
    db: Session,
    buyer: models.User,
    asset: models.Asset,
    purchase_id: int,
    purchase_amount_units: int,
) -> models.ReferralReward | None:
    if not REFERRALS_ENABLED:
        return None
    if asset.symbol.upper() != REFERRAL_REWARD_ASSET_SYMBOL:
        return None
    if not buyer.referred_by_user_id or buyer.referred_by_user_id == buyer.id:
        return None

    existing_reward = db.scalar(
        select(models.ReferralReward).where(
            models.ReferralReward.purchase_id == purchase_id
        )
    )
    if existing_reward:
        return existing_reward

    referrer = db.get(models.User, buyer.referred_by_user_id)
    if not referrer:
        return None

    reward_amount_units = calculate_referral_reward_units(purchase_amount_units)
    if reward_amount_units <= 0:
        return None

    reward = models.ReferralReward(
        referrer_user_id=referrer.id,
        referred_user_id=buyer.id,
        purchase_id=purchase_id,
        purchase_amount_tdsd=int(purchase_amount_units),
        reward_amount_tdsd=reward_amount_units,
        reward_percent=REFERRAL_REWARD_PERCENT,
        status="pending",
    )
    db.add(reward)
    db.flush()

    balance = _get_or_create_balance(db, referrer.id, asset.id)
    balance.balance_units = int(balance.balance_units or 0) + reward_amount_units
    balance.updated_at = datetime.utcnow()
    db.add(
        models.AssetLedgerEntry(
            user_id=referrer.id,
            asset_id=asset.id,
            entry_type="referral_reward_credit",
            amount_units=reward_amount_units,
            direction="credit",
            related_entity_type="referral_reward",
            related_entity_id=reward.id,
            balance_after_units=balance.balance_units,
            comment=(
                f"Referral reward from user #{buyer.id} "
                f"for {asset.symbol} purchase #{purchase_id}"
            ),
        )
    )
    reward.status = "credited"
    reward.credited_at = datetime.utcnow()
    return reward
