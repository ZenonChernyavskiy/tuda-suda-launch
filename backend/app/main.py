from datetime import datetime, timedelta
from decimal import Decimal, ROUND_DOWN
import hmac
import json
import logging
import secrets
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import desc, func, not_, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from . import models, schemas
from .asset_gift_service import get_or_create_treasury_user, send_random_asset_gift
from .config import (
    ALLOW_MOCK_AUTH,
    ADMIN_API_KEY,
    APP_VERSION,
    APP_ENV,
    AUTO_INIT_DB,
    BUY_COMMISSION_PERCENT,
    CORS_ORIGINS,
    DAILY_SEND_LIMIT,
    DEPOSIT_CONFIRMATION_TIMEOUT_MINUTES,
    INITIAL_BALANCE,
    IS_PRODUCTION,
    MAX_DEPOSIT_TON,
    MIN_DEPOSIT_TON,
    HOT_WALLET_ADDRESS,
    REFERRAL_REWARD_ASSET_SYMBOL,
    REFERRAL_REWARD_PERCENT,
    REFERRALS_ENABLED,
    TELEGRAM_BOT_TOKEN,
    TDSD_ASSET_SYMBOL,
    TDSD_DEPOSITS_ENABLED,
    TDSD_FIXED_PRICE_TON,
    TDSD_JETTON_MASTER_ADDRESS,
    TDSD_PROJECT_JETTON_WALLET,
    TON_NETWORK,
    TRANSFER_COMMISSION_PERCENT,
    TREASURY_WALLET_ADDRESS,
    configure_logging,
    get_tdsd_payment_wallet_address,
    validate_production_settings,
)
from .database import get_db
from .fee_service import (
    calculate_buy_commission,
    calculate_purchase_fee,
    calculate_tdsd_fixed_price_quote,
    calculate_transfer_fee,
    decimal_label,
)
from .hot_wallet_payout import (
    PUBLIC_SEND_FAILED_MESSAGE,
    PUBLIC_UNAVAILABLE_MESSAGE,
    HotWalletPayoutFailed,
    HotWalletPayoutUnavailable,
    send_tdsd_from_hot_wallet,
)
from .migrations import init_db
from .providers import ProviderError, get_provider_for_asset
from .referral_service import (
    apply_referral_on_first_login,
    build_referral_link,
    credit_referral_reward_for_purchase,
    ensure_referral_code,
)
from .security import create_access_token, decode_access_token, parse_telegram_init_data
from .ton import TonAddressValidationError, normalize_ton_wallet_address
from .ton_service import TonCenterError, verify_deposit


configure_logging()
validate_production_settings()
logger = logging.getLogger("tuda_suda.api")
if AUTO_INIT_DB:
    init_db()

app = FastAPI(title="Туда-Сюда API", version=APP_VERSION)
NANO_PER_TON = 1_000_000_000
TON_ASSET_SYMBOL = "TON"

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    logger.exception("Unhandled error for %s %s", request.method, request.url.path)
    detail = "Внутренняя ошибка сервера" if IS_PRODUCTION else str(exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": detail},
    )


def get_rank(karma: int) -> str:
    if karma >= 1000:
        return "Титан"
    if karma >= 500:
        return "Легенда"
    if karma >= 200:
        return "Меценат"
    if karma >= 50:
        return "Добряк"
    return "Новичок"


def user_ton_balance_nano(user: models.User) -> int:
    return int(user.ton_balance_nano or 0)


def nano_to_ton_float(amount_nano: int | None) -> float:
    return int(amount_nano or 0) / NANO_PER_TON


def sync_legacy_ton_balance(user: models.User) -> None:
    # Compatibility only: calculations use ton_balance_nano.
    user.ton_balance = Decimal(user_ton_balance_nano(user)) / Decimal(NANO_PER_TON)


def sync_legacy_ton_balance_units(user: models.User, balance_units: int) -> None:
    # AssetBalance is the source of truth; legacy fields mirror TON for old API/UI code.
    user.ton_balance_nano = int(balance_units)
    user.ton_balance = Decimal(int(balance_units)) / Decimal(NANO_PER_TON)


def format_asset_units(amount_units: int | None, decimals: int) -> str:
    amount = int(amount_units or 0)
    sign = "-" if amount < 0 else ""
    amount = abs(amount)
    if decimals <= 0:
        return f"{sign}{amount}"

    scale = 10**decimals
    whole = amount // scale
    fraction = str(amount % scale).rjust(decimals, "0").rstrip("0")
    return f"{sign}{whole}.{fraction}" if fraction else f"{sign}{whole}"


def get_asset_by_symbol(db: Session, symbol: str) -> models.Asset | None:
    return db.scalar(
        select(models.Asset).where(models.Asset.symbol == symbol.upper())
    )


def get_ton_asset(db: Session) -> models.Asset:
    asset = get_asset_by_symbol(db, TON_ASSET_SYMBOL)
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="TON asset не инициализирован",
        )
    return asset


def get_or_create_asset_balance(
    db: Session,
    user_id: int,
    asset_id: int,
    initial_units: int = 0,
) -> models.AssetBalance:
    balance = db.scalar(
        select(models.AssetBalance).where(
            models.AssetBalance.user_id == user_id,
            models.AssetBalance.asset_id == asset_id,
        )
    )
    if balance:
        return balance

    balance = models.AssetBalance(
        user_id=user_id,
        asset_id=asset_id,
        balance_units=int(initial_units),
    )
    db.add(balance)
    db.flush()
    return balance


def get_asset_balance_units(db: Session, user_id: int, asset_id: int) -> int:
    balance = db.scalar(
        select(models.AssetBalance).where(
            models.AssetBalance.user_id == user_id,
            models.AssetBalance.asset_id == asset_id,
        )
    )
    return int(balance.balance_units or 0) if balance else 0


def get_ton_balance_units(db: Session, user: models.User) -> int:
    asset = get_ton_asset(db)
    balance = db.scalar(
        select(models.AssetBalance).where(
            models.AssetBalance.user_id == user.id,
            models.AssetBalance.asset_id == asset.id,
        )
    )
    if balance:
        return int(balance.balance_units or 0)
    return user_ton_balance_nano(user)


def ensure_user_ton_asset_balance(
    db: Session,
    user: models.User,
) -> models.AssetBalance:
    asset = get_ton_asset(db)
    return get_or_create_asset_balance(
        db=db,
        user_id=user.id,
        asset_id=asset.id,
        initial_units=user_ton_balance_nano(user),
    )


def credit_asset_balance(
    db: Session,
    user: models.User,
    asset: models.Asset,
    amount_units: int,
    entry_type: str,
    related_entity_type: str | None = None,
    related_entity_id: int | None = None,
    comment: str | None = None,
) -> models.AssetBalance:
    amount_units = int(amount_units)
    if amount_units <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Сумма asset operation должна быть больше нуля",
        )

    balance = get_or_create_asset_balance(db, user.id, asset.id)
    balance.balance_units = int(balance.balance_units or 0) + amount_units
    balance.updated_at = datetime.utcnow()
    db.add(
        models.AssetLedgerEntry(
            user_id=user.id,
            asset_id=asset.id,
            entry_type=entry_type,
            amount_units=amount_units,
            direction="credit",
            related_entity_type=related_entity_type,
            related_entity_id=related_entity_id,
            balance_after_units=balance.balance_units,
            comment=comment,
        )
    )
    return balance


def serialize_user(
    user: models.User,
    db: Session | None = None,
) -> schemas.UserPublic:
    ton_balance_nano = (
        get_ton_balance_units(db, user) if db is not None else user_ton_balance_nano(user)
    )
    return schemas.UserPublic(
        id=user.id,
        telegram_id=user.telegram_id,
        username=user.username,
        first_name=user.first_name,
        photo_url=user.photo_url,
        balance=user.balance,
        karma=user.karma,
        reputation=int(user.reputation or 0),
        community_weight=int(user.community_weight or 0),
        total_sent=user.total_sent,
        total_received=user.total_received,
        ton_balance_nano=ton_balance_nano,
        ton_balance=nano_to_ton_float(ton_balance_nano),
        ton_wallet_address=user.ton_wallet_address,
        ton_wallet_connected_at=user.ton_wallet_connected_at,
        referral_code=user.referral_code,
        referred_by_user_id=user.referred_by_user_id,
        referred_at=user.referred_at,
        rank=get_rank(user.karma),
        created_at=user.created_at,
        last_active_at=user.last_active_at,
    )


def update_user_trust_metrics(user: models.User) -> None:
    reputation = int(user.reputation or 0)
    karma = int(user.karma or 0)
    age_bonus = 0
    if user.created_at:
        age_bonus = max(0, (datetime.utcnow() - user.created_at).days // 7)
    user.community_weight = max(0, reputation + karma // 10 + age_bonus - int(user.risk_score or 0))


def add_reputation_event(
    db: Session,
    user: models.User,
    event_type: str,
    karma_delta: int = 0,
    reputation_delta: int = 0,
    risk_delta: int = 0,
    related_entity_type: str | None = None,
    related_entity_id: int | None = None,
    comment: str | None = None,
) -> None:
    user.karma += int(karma_delta)
    user.reputation = max(0, int(user.reputation or 0) + int(reputation_delta))
    user.risk_score = max(0, int(user.risk_score or 0) + int(risk_delta))
    update_user_trust_metrics(user)
    db.add(
        models.ReputationEvent(
            user_id=user.id,
            event_type=event_type,
            karma_delta=karma_delta,
            reputation_delta=reputation_delta,
            risk_delta=risk_delta,
            related_entity_type=related_entity_type,
            related_entity_id=related_entity_id,
            comment=comment,
        )
    )


def serialize_leaderboard_user(user: models.User) -> schemas.LeaderboardUser:
    return schemas.LeaderboardUser(
        id=user.id,
        username=user.username,
        first_name=user.first_name,
        karma=user.karma,
        total_sent=user.total_sent,
        total_received=user.total_received,
        rank=get_rank(user.karma),
    )


def serialize_transaction(
    transaction: models.Transaction,
    current_user_id: int,
) -> schemas.TransactionPublic:
    direction = "sent" if transaction.sender_id == current_user_id else "received"
    return schemas.TransactionPublic(
        id=transaction.id,
        amount=transaction.amount,
        message=transaction.message,
        created_at=transaction.created_at,
        type=direction,
    )


def parse_wallet_address_or_400(wallet_address: object) -> str:
    try:
        return normalize_ton_wallet_address(wallet_address)
    except TonAddressValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


def serialize_ton_deposit(deposit: models.TonDeposit) -> schemas.TonDepositPublic:
    tx_hash = deposit.tx_hash
    if tx_hash and tx_hash.startswith("pending:"):
        tx_hash = None
    return schemas.TonDepositPublic(
        id=deposit.id,
        wallet_address=deposit.wallet_address,
        target_wallet_address=deposit.target_wallet_address,
        network=deposit.network,
        amount_ton=float(deposit.amount_ton),
        amount_nano=deposit.amount_nano,
        tx_hash=tx_hash,
        comment=deposit.comment,
        status=deposit.status,
        failed_reason=deposit.failed_reason,
        created_at=deposit.created_at,
        confirmed_at=deposit.confirmed_at,
    )


def serialize_asset_deposit(
    deposit: models.AssetDeposit,
) -> schemas.AssetDepositPublic:
    tx_hash = deposit.tx_hash
    if tx_hash and tx_hash.startswith("pending:"):
        tx_hash = None
    payout_tx_hash = deposit.payout_tx_hash
    if payout_tx_hash and payout_tx_hash.startswith("pending:"):
        payout_tx_hash = None
    fixed_price_quote = None
    if deposit.provider == "tdsd_fixed_price":
        fixed_price_quote = calculate_tdsd_fixed_price_quote(
            int(deposit.amount_units or 0),
            deposit.asset.decimals,
        )
    return schemas.AssetDepositPublic(
        id=deposit.id,
        asset_id=deposit.asset_id,
        symbol=deposit.asset.symbol,
        asset_name=deposit.asset.name,
        wallet_address=deposit.wallet_address,
        target_wallet_address=deposit.target_wallet_address,
        amount_units=int(deposit.amount_units or 0),
        amount_display=format_asset_units(
            deposit.amount_units or 0,
            deposit.asset.decimals,
        ),
        payment_amount_nano=(
            fixed_price_quote.payment_amount_nano if fixed_price_quote else None
        ),
        payment_amount_ton=(
            format_asset_units(fixed_price_quote.payment_amount_nano, 9)
            if fixed_price_quote
            else None
        ),
        fixed_price_ton=(
            decimal_label(fixed_price_quote.fixed_price_ton)
            if fixed_price_quote
            else None
        ),
        payment_address=deposit.target_wallet_address,
        tx_hash=tx_hash,
        comment=deposit.comment,
        status=deposit.status,
        provider=deposit.provider,
        network=deposit.network,
        failed_reason=deposit.failed_reason,
        payout_status=deposit.payout_status or "pending",
        payout_tx_hash=payout_tx_hash,
        payout_failed_reason=deposit.payout_failed_reason,
        payout_sent_at=deposit.payout_sent_at,
        payout_confirmed_at=deposit.payout_confirmed_at,
        created_at=deposit.created_at,
        confirmed_at=deposit.confirmed_at,
    )


def serialize_asset_deposit_create(
    deposit: models.AssetDeposit,
) -> schemas.AssetDepositCreateResponse:
    payout_tx_hash = deposit.payout_tx_hash
    if payout_tx_hash and payout_tx_hash.startswith("pending:"):
        payout_tx_hash = None
    fixed_price_quote = None
    if deposit.provider == "tdsd_fixed_price":
        fixed_price_quote = calculate_tdsd_fixed_price_quote(
            int(deposit.amount_units or 0),
            deposit.asset.decimals,
        )
    return schemas.AssetDepositCreateResponse(
        deposit_id=deposit.id,
        asset_id=deposit.asset_id,
        asset_symbol=deposit.asset.symbol,
        symbol=deposit.asset.symbol,
        asset_name=deposit.asset.name,
        amount_units=int(deposit.amount_units or 0),
        amount_display=format_asset_units(
            deposit.amount_units or 0,
            deposit.asset.decimals,
        ),
        payment_amount_nano=(
            fixed_price_quote.payment_amount_nano if fixed_price_quote else None
        ),
        payment_amount_ton=(
            format_asset_units(fixed_price_quote.payment_amount_nano, 9)
            if fixed_price_quote
            else None
        ),
        fixed_price_ton=(
            decimal_label(fixed_price_quote.fixed_price_ton)
            if fixed_price_quote
            else None
        ),
        payment_address=deposit.target_wallet_address,
        target_wallet_address=deposit.target_wallet_address,
        comment=deposit.comment,
        provider=deposit.provider,
        network=deposit.network,
        status="pending",
        payout_status=deposit.payout_status or "pending",
        payout_tx_hash=payout_tx_hash,
        payout_failed_reason=deposit.payout_failed_reason,
        payout_sent_at=deposit.payout_sent_at,
        payout_confirmed_at=deposit.payout_confirmed_at,
    )


def parse_asset_metadata(value: str | None) -> object | None:
    if not value:
        return None
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def dump_asset_metadata(value: object | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def serialize_asset(asset: models.Asset) -> schemas.AssetPublic:
    return schemas.AssetPublic(
        id=asset.id,
        symbol=asset.symbol,
        name=asset.name,
        asset_type=asset.asset_type,
        network=asset.network,
        decimals=asset.decimals,
        contract_address=asset.contract_address,
        provider_key=asset.provider_key,
        metadata_json=parse_asset_metadata(asset.metadata_json),
        display_order=asset.display_order or 0,
        is_active=asset.is_active,
        created_at=asset.created_at,
    )


def serialize_asset_balance(
    asset: models.Asset,
    balance_units: int,
) -> schemas.AssetBalancePublic:
    return schemas.AssetBalancePublic(
        asset_id=asset.id,
        symbol=asset.symbol,
        name=asset.name,
        asset_type=asset.asset_type,
        network=asset.network,
        decimals=asset.decimals,
        contract_address=asset.contract_address,
        balance_units=int(balance_units),
        balance_display=format_asset_units(balance_units, asset.decimals),
    )


def serialize_ledger_entry(
    entry: models.AssetLedgerEntry,
) -> schemas.AssetLedgerEntryPublic:
    return schemas.AssetLedgerEntryPublic(
        id=entry.id,
        asset_id=entry.asset_id,
        symbol=entry.asset.symbol,
        name=entry.asset.name,
        decimals=entry.asset.decimals,
        entry_type=entry.entry_type,
        amount_units=entry.amount_units,
        amount_display=format_asset_units(entry.amount_units, entry.asset.decimals),
        direction=entry.direction,
        related_entity_type=entry.related_entity_type,
        related_entity_id=entry.related_entity_id,
        balance_after_units=entry.balance_after_units,
        balance_after_display=format_asset_units(
            entry.balance_after_units,
            entry.asset.decimals,
        ),
        created_at=entry.created_at,
        comment=entry.comment,
    )


def serialize_admin_ledger_entry(
    entry: models.AssetLedgerEntry,
) -> schemas.AdminLedgerEntryPublic:
    return schemas.AdminLedgerEntryPublic(
        id=entry.id,
        user_id=entry.user_id,
        username=entry.user.username,
        telegram_id=entry.user.telegram_id,
        asset_id=entry.asset_id,
        asset_symbol=entry.asset.symbol,
        asset_name=entry.asset.name,
        entry_type=entry.entry_type,
        direction=entry.direction,
        amount_units=entry.amount_units,
        amount_display=format_asset_units(entry.amount_units, entry.asset.decimals),
        balance_after_units=entry.balance_after_units,
        balance_after_display=format_asset_units(
            entry.balance_after_units,
            entry.asset.decimals,
        ),
        related_entity_type=entry.related_entity_type,
        related_entity_id=entry.related_entity_id,
        comment=entry.comment,
        created_at=entry.created_at,
    )


def serialize_admin_user(user: models.User) -> schemas.AdminUserPublic:
    return schemas.AdminUserPublic(
        id=user.id,
        telegram_id=user.telegram_id,
        username=user.username,
        first_name=user.first_name,
        balance=user.balance,
        karma=user.karma,
        reputation=int(user.reputation or 0),
        risk_score=int(user.risk_score or 0),
        community_weight=int(user.community_weight or 0),
        total_sent=user.total_sent,
        total_received=user.total_received,
        ton_wallet_address=user.ton_wallet_address,
        created_at=user.created_at,
        last_active_at=user.last_active_at,
    )


def serialize_admin_transaction(
    transaction: models.Transaction,
) -> schemas.AdminTransactionPublic:
    return schemas.AdminTransactionPublic(
        id=transaction.id,
        sender_id=transaction.sender_id,
        receiver_id=transaction.receiver_id,
        amount=transaction.amount,
        message=transaction.message,
        created_at=transaction.created_at,
    )


def serialize_reputation_event(
    event: models.ReputationEvent,
) -> schemas.ReputationEventPublic:
    return schemas.ReputationEventPublic(
        id=event.id,
        user_id=event.user_id,
        username=event.user.username,
        event_type=event.event_type,
        karma_delta=event.karma_delta,
        reputation_delta=event.reputation_delta,
        risk_delta=event.risk_delta,
        related_entity_type=event.related_entity_type,
        related_entity_id=event.related_entity_id,
        comment=event.comment,
        created_at=event.created_at,
    )


def user_display_name(user: models.User | None) -> str:
    if not user:
        return "Анонимно"
    if user.username:
        return f"@{user.username}"
    return user.first_name or "Анонимно"


def referral_asset_decimals(db: Session) -> int:
    asset = get_asset_by_symbol(db, REFERRAL_REWARD_ASSET_SYMBOL)
    return int(asset.decimals if asset else 9)


def serialize_referral_reward(
    reward: models.ReferralReward,
    decimals: int,
) -> schemas.ReferralRewardPublic:
    return schemas.ReferralRewardPublic(
        id=reward.id,
        referred_user_display_name=user_display_name(reward.referred_user),
        purchase_amount_tdsd=int(reward.purchase_amount_tdsd or 0),
        purchase_amount_display=format_asset_units(
            reward.purchase_amount_tdsd,
            decimals,
        ),
        reward_amount_tdsd=int(reward.reward_amount_tdsd or 0),
        reward_amount_display=format_asset_units(
            reward.reward_amount_tdsd,
            decimals,
        ),
        reward_percent=decimal_label(Decimal(str(reward.reward_percent or 0))),
        status=reward.status,
        created_at=reward.created_at,
        credited_at=reward.credited_at,
    )


def serialize_referral_dashboard(
    db: Session,
    user: models.User,
) -> schemas.ReferralDashboardResponse:
    referral_code = ensure_referral_code(db, user)
    decimals = referral_asset_decimals(db)
    invited_users = db.scalars(
        select(models.User)
        .where(models.User.referred_by_user_id == user.id)
        .order_by(desc(models.User.referred_at))
        .limit(100)
    ).all()
    rewards = db.scalars(
        select(models.ReferralReward)
        .where(models.ReferralReward.referrer_user_id == user.id)
        .order_by(desc(models.ReferralReward.created_at))
        .limit(100)
    ).all()

    rewards_by_user: dict[int, list[models.ReferralReward]] = {}
    total_reward_units = 0
    pending_reward_units = 0
    for reward in rewards:
        rewards_by_user.setdefault(reward.referred_user_id, []).append(reward)
        if reward.status == "credited":
            total_reward_units += int(reward.reward_amount_tdsd or 0)
        if reward.status == "pending":
            pending_reward_units += int(reward.reward_amount_tdsd or 0)

    invited_rows = []
    for invited in invited_users:
        invited_rewards = rewards_by_user.get(invited.id, [])
        purchase_units = sum(
            int(reward.purchase_amount_tdsd or 0)
            for reward in invited_rewards
            if reward.status in {"pending", "credited"}
        )
        reward_units = sum(
            int(reward.reward_amount_tdsd or 0)
            for reward in invited_rewards
            if reward.status == "credited"
        )
        invited_rows.append(
            schemas.ReferralInvitedUserPublic(
                user_id=invited.id,
                display_name=user_display_name(invited),
                username=invited.username,
                invited_at=invited.referred_at,
                total_purchases_tdsd=purchase_units,
                total_purchases_display=format_asset_units(purchase_units, decimals),
                total_reward_tdsd=reward_units,
                total_reward_display=format_asset_units(reward_units, decimals),
                status="credited" if reward_units > 0 else "invited",
            )
        )

    return schemas.ReferralDashboardResponse(
        referral_code=referral_code,
        referral_link=build_referral_link(referral_code),
        referrals_enabled=REFERRALS_ENABLED,
        reward_percent=decimal_label(REFERRAL_REWARD_PERCENT),
        reward_asset_symbol=REFERRAL_REWARD_ASSET_SYMBOL,
        invited_count=len(invited_users),
        total_reward_tdsd=total_reward_units,
        total_reward_display=format_asset_units(total_reward_units, decimals),
        pending_reward_tdsd=pending_reward_units,
        pending_reward_display=format_asset_units(pending_reward_units, decimals),
        invited_users=invited_rows,
        rewards=[
            serialize_referral_reward(reward, decimals)
            for reward in rewards
        ],
    )


def serialize_asset_gift(
    gift: models.AssetGift,
    current_user_id: int,
) -> schemas.AssetGiftPublic:
    gift_type = "sent" if gift.sender_id == current_user_id else "received"
    counterparty = gift.receiver if gift_type == "sent" else gift.sender
    display_units = (
        int(gift.amount_units or 0)
        if gift_type == "sent"
        else int(gift.net_amount_units or gift.amount_units or 0)
    )
    return schemas.AssetGiftPublic(
        id=gift.id,
        type=gift_type,
        symbol=gift.asset.symbol,
        asset_name=gift.asset.name,
        amount_units=display_units,
        amount_display=format_asset_units(display_units, gift.asset.decimals),
        fee_units=int(gift.fee_units or 0),
        fee_display=format_asset_units(gift.fee_units or 0, gift.asset.decimals),
        net_amount_units=int(gift.net_amount_units or 0),
        net_amount_display=format_asset_units(
            gift.net_amount_units or 0,
            gift.asset.decimals,
        ),
        message=gift.message,
        status=gift.status,
        counterparty_display_name=user_display_name(counterparty),
        created_at=gift.created_at,
    )


def serialize_asset_gift_feed_item(gift: models.AssetGift) -> schemas.AssetGiftFeedItem:
    amount_units = int(gift.amount_units or 0)
    amount_display = format_asset_units(amount_units, gift.asset.decimals)
    return schemas.AssetGiftFeedItem(
        id=gift.id,
        symbol=gift.asset.symbol,
        asset_name=gift.asset.name,
        amount_units=amount_units,
        amount_display=amount_display,
        text=f"Кто-то отправил {amount_display} {gift.asset.symbol}",
        created_at=gift.created_at,
    )


def serialize_public_virtual_transaction(
    transaction: models.Transaction,
) -> schemas.PublicTransactionFeedItem:
    return schemas.PublicTransactionFeedItem(
        id=f"virtual-{transaction.id}",
        source_type="virtual_gift",
        created_at=transaction.created_at,
        sender=user_display_name(transaction.sender),
        receiver=user_display_name(transaction.receiver),
        token=TDSD_ASSET_SYMBOL,
        amount=str(transaction.amount),
        direction="Перевод",
        comment=transaction.message,
    )


def serialize_public_asset_transaction(
    gift: models.AssetGift,
) -> schemas.PublicTransactionFeedItem:
    amount_units = int(gift.amount_units or 0)
    return schemas.PublicTransactionFeedItem(
        id=f"asset-{gift.id}",
        source_type="asset_gift",
        created_at=gift.created_at,
        sender=user_display_name(gift.sender),
        receiver=user_display_name(gift.receiver),
        token=gift.asset.symbol,
        amount=format_asset_units(amount_units, gift.asset.decimals),
        direction="Перевод",
        comment=gift.message,
    )


def serialize_public_fee_entry(
    entry: models.AssetLedgerEntry,
) -> schemas.PublicTransactionFeedItem:
    is_treasury_income = entry.entry_type == "treasury_income"
    return schemas.PublicTransactionFeedItem(
        id=f"fee-{entry.id}",
        source_type="fee",
        created_at=entry.created_at,
        sender="Сервис" if is_treasury_income else user_display_name(entry.user),
        receiver="Treasury",
        token=entry.asset.symbol,
        amount=format_asset_units(entry.amount_units, entry.asset.decimals),
        direction="Комиссия сервиса",
        comment=entry.comment,
    )


def serialize_public_referral_reward(
    reward: models.ReferralReward,
    decimals: int,
) -> schemas.PublicTransactionFeedItem:
    return schemas.PublicTransactionFeedItem(
        id=f"referral-{reward.id}",
        source_type="referral_reward",
        created_at=reward.credited_at or reward.created_at,
        sender=user_display_name(reward.referred_user),
        receiver=user_display_name(reward.referrer),
        token=REFERRAL_REWARD_ASSET_SYMBOL,
        amount=format_asset_units(reward.reward_amount_tdsd, decimals),
        direction="Реферальная награда",
        comment="10% от покупки TDSD приглашенным пользователем",
    )


def serialize_asset_gift_leaderboard_user(
    user: models.User,
    amount_units: int,
    asset: models.Asset,
) -> schemas.AssetGiftLeaderboardUser:
    return schemas.AssetGiftLeaderboardUser(
        id=user.id,
        username=user.username,
        first_name=user.first_name,
        amount_units=int(amount_units or 0),
        amount_display=format_asset_units(amount_units or 0, asset.decimals),
    )


def amount_ton_to_nano(amount_ton: Decimal) -> int:
    quantized = amount_ton.quantize(Decimal("0.000000001"), rounding=ROUND_DOWN)
    return int(quantized * Decimal("1000000000"))


def ensure_testnet_deposit_config() -> str:
    if TON_NETWORK != "testnet":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Депозиты разрешены только в TON testnet",
        )
    payment_wallet_address = get_tdsd_payment_wallet_address()
    if not payment_wallet_address:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Адрес приема оплаты временно не настроен",
        )
    return parse_wallet_address_or_400(payment_wallet_address)


def build_deposit_comment(user_id: int, deposit_id: int) -> str:
    return f"tuda-suda:{user_id}:{deposit_id}:{secrets.token_urlsafe(8)}"


def ton_verify_response(
    deposit: models.TonDeposit,
    current_user: models.User,
    message: str,
    db: Session,
) -> schemas.TonDepositVerifyResponse:
    ton_balance_nano = get_ton_balance_units(db, current_user)
    return schemas.TonDepositVerifyResponse(
        deposit=serialize_ton_deposit(deposit),
        ton_balance_nano=ton_balance_nano,
        ton_balance=nano_to_ton_float(ton_balance_nano),
        message=message,
    )


def mark_deposit_failed(deposit: models.TonDeposit, reason: str) -> None:
    deposit.status = "failed"
    deposit.failed_reason = reason[:500]


def mark_asset_deposit_failed(deposit: models.AssetDeposit, reason: str) -> None:
    deposit.status = "failed"
    deposit.failed_reason = reason[:500]


def asset_deposit_verify_response(
    deposit: models.AssetDeposit,
    message: str,
    asset_balance: models.AssetBalance | None = None,
) -> schemas.AssetDepositVerifyResponse:
    serialized_balance = None
    if asset_balance:
        serialized_balance = serialize_asset_balance(
            deposit.asset,
            asset_balance.balance_units,
        )
    return schemas.AssetDepositVerifyResponse(
        deposit=serialize_asset_deposit(deposit),
        asset_balance=serialized_balance,
        message=message,
    )


def is_tdsd_fixed_price_purchase(deposit: models.AssetDeposit) -> bool:
    return (
        deposit.asset.symbol == TDSD_ASSET_SYMBOL
        and deposit.provider == "tdsd_fixed_price"
    )


def tdsd_payout_user_message(deposit: models.AssetDeposit) -> str:
    if deposit.status == "pending":
        return "Ожидаем оплату"
    if deposit.status == "failed":
        return "Ошибка отправки, обратитесь в поддержку"
    payout_status = deposit.payout_status or "pending"
    if payout_status == "pending":
        return "Отправляем TDSD"
    if payout_status in {"sent", "confirmed"}:
        return "TDSD отправлены"
    if payout_status == "failed":
        if deposit.payout_failed_reason == PUBLIC_UNAVAILABLE_MESSAGE:
            return PUBLIC_UNAVAILABLE_MESSAGE
        return PUBLIC_SEND_FAILED_MESSAGE
    return "Оплата найдена"


def tdsd_payout_amount_units(deposit: models.AssetDeposit) -> int:
    if is_tdsd_fixed_price_purchase(deposit):
        return calculate_buy_commission(int(deposit.amount_units or 0)).credited_amount_units
    return int(deposit.amount_units or 0)


def is_pending_payout_lock(tx_hash: str | None) -> bool:
    return bool(tx_hash and tx_hash.startswith("pending:"))


def log_tdsd_payout_exception(
    message: str,
    exc: BaseException,
    deposit: models.AssetDeposit,
    payout_amount_units: int | None,
) -> None:
    exc_info = (type(exc), exc, exc.__traceback__)
    try:
        payout_amount_display = format_asset_units(
            payout_amount_units,
            deposit.asset.decimals,
        )
    except Exception:
        payout_amount_display = None
    logger.exception(
        "%s purchase_id=%s payment_tx_hash=%s hot_wallet_address=%s "
        "recipient_wallet_address=%s payout_amount_units=%s "
        "payout_amount_display=%s exception_type=%s exception=%s",
        message,
        deposit.id,
        deposit.tx_hash,
        HOT_WALLET_ADDRESS,
        deposit.wallet_address,
        payout_amount_units,
        payout_amount_display,
        type(exc).__name__,
        str(exc),
        exc_info=exc_info,
    )


def ensure_tdsd_hot_wallet_payout(
    db: Session,
    deposit: models.AssetDeposit,
    current_user: models.User,
    payout_amount_units: int,
) -> str:
    if not is_tdsd_fixed_price_purchase(deposit):
        return "Пополнение подтверждено"
    if deposit.status != "confirmed":
        return tdsd_payout_user_message(deposit)

    payout_status = deposit.payout_status or "pending"
    if payout_status in {"sent", "confirmed"}:
        return tdsd_payout_user_message(deposit)
    if deposit.payout_tx_hash and not is_pending_payout_lock(deposit.payout_tx_hash):
        return tdsd_payout_user_message(deposit)
    if is_pending_payout_lock(deposit.payout_tx_hash):
        return "Отправляем TDSD"

    if not current_user.ton_wallet_address:
        deposit.payout_status = "failed"
        deposit.payout_failed_reason = "Сначала подключите кошелек для получения TDSD"
        deposit.payout_tx_hash = None
        deposit.payout_sent_at = None
        db.commit()
        db.refresh(deposit)
        return PUBLIC_SEND_FAILED_MESSAGE

    deposit.payout_status = "pending"
    deposit.payout_failed_reason = None
    deposit.payout_tx_hash = f"pending:{deposit.id}:{secrets.token_urlsafe(12)}"
    deposit.payout_sent_at = datetime.utcnow()
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        log_tdsd_payout_exception(
            "TDSD hot wallet payout lock failed",
            exc,
            deposit,
            payout_amount_units,
        )
        return "Отправляем TDSD"
    db.refresh(deposit)

    try:
        payout = send_tdsd_from_hot_wallet(
            recipient_wallet_address=deposit.wallet_address,
            amount_units=payout_amount_units,
            purchase_id=deposit.id,
        )
    except HotWalletPayoutUnavailable as exc:
        deposit.payout_status = "failed"
        deposit.payout_failed_reason = PUBLIC_UNAVAILABLE_MESSAGE
        deposit.payout_tx_hash = None
        deposit.payout_sent_at = None
        db.commit()
        db.refresh(deposit)
        log_tdsd_payout_exception(
            "TDSD hot wallet payout unavailable",
            exc,
            deposit,
            payout_amount_units,
        )
        return PUBLIC_UNAVAILABLE_MESSAGE
    except HotWalletPayoutFailed as exc:
        deposit.payout_status = "failed"
        deposit.payout_failed_reason = PUBLIC_SEND_FAILED_MESSAGE
        deposit.payout_tx_hash = None
        deposit.payout_sent_at = None
        db.commit()
        db.refresh(deposit)
        log_tdsd_payout_exception(
            "TDSD hot wallet payout failed",
            exc,
            deposit,
            payout_amount_units,
        )
        return PUBLIC_SEND_FAILED_MESSAGE

    used_payout = db.scalar(
        select(models.AssetDeposit).where(
            models.AssetDeposit.payout_tx_hash == payout.tx_hash,
            models.AssetDeposit.id != deposit.id,
        )
    )
    if used_payout:
        deposit.payout_status = "failed"
        deposit.payout_failed_reason = "Tx hash выплаты уже сохранен в другой покупке"
        deposit.payout_tx_hash = None
        deposit.payout_sent_at = None
        db.commit()
        db.refresh(deposit)
        logger.error(
            "Duplicate TDSD payout tx hash purchase_id=%s payment_tx_hash=%s "
            "hot_wallet_address=%s recipient_wallet_address=%s "
            "payout_amount_units=%s payout_tx_hash=%s",
            deposit.id,
            deposit.tx_hash,
            HOT_WALLET_ADDRESS,
            deposit.wallet_address,
            payout_amount_units,
            payout.tx_hash,
        )
        return PUBLIC_SEND_FAILED_MESSAGE

    deposit.payout_status = "sent"
    deposit.payout_tx_hash = payout.tx_hash
    deposit.payout_failed_reason = None
    deposit.payout_sent_at = datetime.utcnow()
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        log_tdsd_payout_exception(
            "Could not save TDSD payout tx hash",
            exc,
            deposit,
            payout_amount_units,
        )
        return PUBLIC_SEND_FAILED_MESSAGE
    db.refresh(deposit)
    return "TDSD отправлены"


def get_or_create_user(
    db: Session,
    telegram_id: str,
    username: str | None,
    first_name: str | None,
    photo_url: str | None = None,
    referral_param: str | None = None,
) -> models.User:
    # Telegram Mini App открывается без отдельной регистрации: создаем профиль при первом входе.
    user = db.scalar(select(models.User).where(models.User.telegram_id == telegram_id))
    if user:
        user.username = username
        user.first_name = first_name
        user.photo_url = photo_url
        user.last_active_at = datetime.utcnow()
        ensure_referral_code(db, user)
        apply_referral_on_first_login(db, user, referral_param)
        update_user_trust_metrics(user)
        ensure_user_ton_asset_balance(db, user)
        db.commit()
        db.refresh(user)
        return user

    user = models.User(
        telegram_id=telegram_id,
        username=username,
        first_name=first_name,
        photo_url=photo_url,
        balance=INITIAL_BALANCE,
        karma=0,
        total_sent=0,
        total_received=0,
        last_active_at=datetime.utcnow(),
    )
    db.add(user)
    db.flush()
    ensure_referral_code(db, user)
    apply_referral_on_first_login(db, user, referral_param)
    add_reputation_event(
        db=db,
        user=user,
        event_type="account_created",
        reputation_delta=1,
        comment="Telegram Mini App profile created",
    )
    ensure_user_ton_asset_balance(db, user)
    db.commit()
    db.refresh(user)
    return user


def get_current_user(
    authorization: Annotated[str | None, Header()] = None,
    db: Session = Depends(get_db),
) -> models.User:
    # Для MVP используем простой подписанный токен, который backend выдает после initData/mock-login.
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Нужна авторизация",
        )

    token = authorization.split(" ", 1)[1].strip()
    telegram_id = decode_access_token(token)
    user = db.scalar(select(models.User).where(models.User.telegram_id == telegram_id))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Пользователь не найден",
        )
    return user


def require_admin(
    x_admin_token: Annotated[str | None, Header(alias="X-Admin-Token")] = None,
) -> None:
    if not ADMIN_API_KEY and not IS_PRODUCTION:
        return
    if not x_admin_token or not hmac.compare_digest(x_admin_token, ADMIN_API_KEY):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нужен admin token",
        )


@app.get("/health", response_model=schemas.HealthResponse)
def health(db: Session = Depends(get_db)) -> schemas.HealthResponse:
    db.execute(select(1))
    return schemas.HealthResponse(status="ok", database="connected")


@app.get("/ready", response_model=schemas.HealthResponse)
@app.get("/readiness", response_model=schemas.HealthResponse)
def readiness(db: Session = Depends(get_db)) -> schemas.HealthResponse:
    db.execute(select(1))
    ton_asset = get_asset_by_symbol(db, TON_ASSET_SYMBOL)
    if not ton_asset:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="TON asset не инициализирован",
        )
    if TDSD_DEPOSITS_ENABLED:
        tdsd_asset = get_asset_by_symbol(db, TDSD_ASSET_SYMBOL)
        if (
            not tdsd_asset
            or not tdsd_asset.is_active
            or tdsd_asset.provider_key != "jetton"
            or tdsd_asset.contract_address != TDSD_JETTON_MASTER_ADDRESS
            or not TDSD_PROJECT_JETTON_WALLET
        ):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="TDSD asset не готов к Jetton deposits",
            )
    else:
        tdsd_asset = get_asset_by_symbol(db, TDSD_ASSET_SYMBOL)
        if (
            not tdsd_asset
            or not tdsd_asset.is_active
            or not get_tdsd_payment_wallet_address()
        ):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="TDSD fixed-price покупка не готова",
            )
    return schemas.HealthResponse(status="ready", database="connected")


@app.post("/auth/telegram", response_model=schemas.AuthResponse)
def auth_telegram(
    payload: schemas.TelegramAuthRequest,
    db: Session = Depends(get_db),
) -> schemas.AuthResponse:
    if payload.mock:
        if not ALLOW_MOCK_AUTH:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Mock-login отключен на backend",
            )
        mock_user = payload.mock_user or schemas.MockTelegramUser(
            telegram_id="1001",
            username="demo_user",
            first_name="Demo",
        )
        telegram_user = mock_user.model_dump()
        referral_param = payload.referral_param or payload.start_param
    else:
        if not payload.init_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Передайте initData или включите mock-login",
            )
        telegram_user = parse_telegram_init_data(
            payload.init_data,
            TELEGRAM_BOT_TOKEN,
        )
        referral_param = (
            telegram_user.get("start_param")
            or payload.referral_param
            or payload.start_param
        )

    user = get_or_create_user(
        db=db,
        telegram_id=str(telegram_user["telegram_id"]),
        username=telegram_user.get("username"),
        first_name=telegram_user.get("first_name"),
        photo_url=telegram_user.get("photo_url"),
        referral_param=referral_param,
    )
    return schemas.AuthResponse(
        access_token=create_access_token(user.telegram_id),
        user=serialize_user(user, db),
    )


@app.get("/me", response_model=schemas.UserDashboard)
def me(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> schemas.UserDashboard:
    transactions = db.scalars(
        select(models.Transaction)
        .where(
            or_(
                models.Transaction.sender_id == current_user.id,
                models.Transaction.receiver_id == current_user.id,
            )
        )
        .order_by(desc(models.Transaction.created_at))
        .limit(5)
    ).all()
    return schemas.UserDashboard(
        user=serialize_user(current_user, db),
        last_transactions=[
            serialize_transaction(transaction, current_user.id)
            for transaction in transactions
        ],
    )


@app.get("/referrals/me", response_model=schemas.ReferralDashboardResponse)
def referrals_me(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> schemas.ReferralDashboardResponse:
    response = serialize_referral_dashboard(db, current_user)
    db.commit()
    return response


@app.post("/wallet/connect", response_model=schemas.UserPublic)
def connect_wallet(
    payload: schemas.WalletConnectRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> schemas.UserPublic:
    wallet_address = parse_wallet_address_or_400(payload.wallet_address)
    now = datetime.utcnow()
    active_wallets = db.scalars(
        select(models.WalletConnection).where(
            models.WalletConnection.user_id == current_user.id,
            models.WalletConnection.network == "ton",
            models.WalletConnection.is_active.is_(True),
        )
    ).all()
    for wallet in active_wallets:
        wallet.is_active = False
        wallet.disconnected_at = now
    db.add(
        models.WalletConnection(
            user_id=current_user.id,
            network="ton",
            wallet_address=wallet_address,
            is_active=True,
            connected_at=now,
        )
    )
    current_user.ton_wallet_address = wallet_address
    current_user.ton_wallet_connected_at = now
    db.commit()
    db.refresh(current_user)
    return serialize_user(current_user, db)


@app.get("/wallet/me", response_model=schemas.WalletResponse)
def wallet_me(
    current_user: models.User = Depends(get_current_user),
) -> schemas.WalletResponse:
    return schemas.WalletResponse(
        wallet_address=current_user.ton_wallet_address,
        connected_at=current_user.ton_wallet_connected_at,
    )


@app.delete("/wallet/disconnect", response_model=schemas.UserPublic)
def disconnect_wallet(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> schemas.UserPublic:
    now = datetime.utcnow()
    active_wallets = db.scalars(
        select(models.WalletConnection).where(
            models.WalletConnection.user_id == current_user.id,
            models.WalletConnection.network == "ton",
            models.WalletConnection.is_active.is_(True),
        )
    ).all()
    for wallet in active_wallets:
        wallet.is_active = False
        wallet.disconnected_at = now
    current_user.ton_wallet_address = None
    current_user.ton_wallet_connected_at = None
    db.commit()
    db.refresh(current_user)
    return serialize_user(current_user, db)


@app.get(
    "/fees/config",
    response_model=schemas.FeeConfigPublic,
    response_model_exclude_none=True,
)
def fees_config() -> schemas.FeeConfigPublic:
    return schemas.FeeConfigPublic(
        buy_commission_percent=decimal_label(BUY_COMMISSION_PERCENT),
        buy_fee_percent=decimal_label(BUY_COMMISSION_PERCENT),
        tdsd_fixed_price_ton=decimal_label(TDSD_FIXED_PRICE_TON),
        tdsd_per_ton=decimal_label(Decimal("1") / TDSD_FIXED_PRICE_TON),
        transfer_commission_percent=decimal_label(TRANSFER_COMMISSION_PERCENT),
        purchase_fee_percent=decimal_label(BUY_COMMISSION_PERCENT),
        purchase_min_fee_ton="0",
        transfer_fee_percent=decimal_label(TRANSFER_COMMISSION_PERCENT),
        transfer_fee_asset_symbol=TDSD_ASSET_SYMBOL,
        payment_address=get_tdsd_payment_wallet_address(),
        project_ton_wallet_address=None,
        treasury_wallet_address=TREASURY_WALLET_ADDRESS,
        hot_wallet_address=HOT_WALLET_ADDRESS,
        tdsd_jetton_master_address=TDSD_JETTON_MASTER_ADDRESS,
    )


@app.post("/fees/purchase/quote", response_model=schemas.PurchaseFeeQuoteResponse)
def purchase_fee_quote(
    payload: schemas.PurchaseFeeQuoteRequest,
) -> schemas.PurchaseFeeQuoteResponse:
    try:
        quote = calculate_purchase_fee(payload.amount_ton)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    return schemas.PurchaseFeeQuoteResponse(
        total_amount_nano=quote.total_amount_nano,
        total_amount_ton=format_asset_units(quote.total_amount_nano, 9),
        fee_amount_nano=quote.fee_amount_nano,
        fee_amount_ton=format_asset_units(quote.fee_amount_nano, 9),
        treasury_amount_nano=quote.treasury_amount_nano,
        treasury_amount_ton=format_asset_units(quote.treasury_amount_nano, 9),
        purchase_amount_nano=quote.purchase_amount_nano,
        purchase_amount_ton=format_asset_units(quote.purchase_amount_nano, 9),
        fee_percent=decimal_label(quote.fee_percent),
        min_fee_ton=decimal_label(quote.min_fee_ton),
    )


@app.post("/fees/transfer/quote", response_model=schemas.TransferFeeQuoteResponse)
def transfer_fee_quote(
    payload: schemas.TransferFeeQuoteRequest,
    db: Session = Depends(get_db),
) -> schemas.TransferFeeQuoteResponse:
    asset = get_asset_by_symbol(db, payload.asset_symbol)
    if not asset or not asset.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Актив не найден",
        )
    try:
        quote = calculate_transfer_fee(asset.symbol, payload.amount_units)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    return schemas.TransferFeeQuoteResponse(
        asset_symbol=asset.symbol,
        total_amount_units=quote.total_amount_units,
        total_amount_display=format_asset_units(
            quote.total_amount_units,
            asset.decimals,
        ),
        fee_amount_units=quote.fee_amount_units,
        fee_amount_display=format_asset_units(quote.fee_amount_units, asset.decimals),
        treasury_amount_units=quote.treasury_amount_units,
        treasury_amount_display=format_asset_units(
            quote.treasury_amount_units,
            asset.decimals,
        ),
        recipient_amount_units=quote.recipient_amount_units,
        recipient_amount_display=format_asset_units(
            quote.recipient_amount_units,
            asset.decimals,
        ),
        fee_percent=decimal_label(quote.fee_percent),
    )


@app.get("/assets", response_model=list[schemas.AssetPublic])
def assets(db: Session = Depends(get_db)) -> list[schemas.AssetPublic]:
    rows = db.scalars(
        select(models.Asset)
        .where(models.Asset.is_active.is_(True))
        .order_by(models.Asset.display_order, models.Asset.symbol)
    ).all()
    return [serialize_asset(asset) for asset in rows]


@app.get(
    "/admin/assets",
    response_model=list[schemas.AssetPublic],
    dependencies=[Depends(require_admin)],
)
def admin_assets(
    db: Session = Depends(get_db),
    symbol: Annotated[str | None, Query(max_length=32)] = None,
    asset_type: Annotated[str | None, Query(max_length=32)] = None,
    network: Annotated[str | None, Query(max_length=32)] = None,
    is_active: Annotated[bool | None, Query()] = None,
) -> list[schemas.AssetPublic]:
    statement = select(models.Asset)
    if symbol:
        statement = statement.where(models.Asset.symbol == symbol.strip().upper())
    if asset_type:
        statement = statement.where(models.Asset.asset_type == asset_type.strip())
    if network:
        statement = statement.where(models.Asset.network == network.strip())
    if is_active is not None:
        statement = statement.where(models.Asset.is_active.is_(is_active))
    rows = db.scalars(
        statement.order_by(
            models.Asset.display_order,
            models.Asset.symbol,
        )
    ).all()
    return [serialize_asset(asset) for asset in rows]


@app.post(
    "/admin/assets/create",
    response_model=schemas.AssetPublic,
    dependencies=[Depends(require_admin)],
)
def create_admin_asset(
    payload: schemas.AssetCreateRequest,
    db: Session = Depends(get_db),
) -> schemas.AssetPublic:
    existing = get_asset_by_symbol(db, payload.symbol)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Asset с таким symbol уже существует",
        )

    asset = models.Asset(
        symbol=payload.symbol,
        name=payload.name,
        asset_type=payload.asset_type,
        network=payload.network,
        decimals=payload.decimals,
        contract_address=payload.contract_address,
        provider_key=payload.provider_key,
        metadata_json=dump_asset_metadata(payload.metadata_json),
        display_order=payload.display_order,
        is_active=payload.is_active,
    )
    db.add(asset)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Asset с таким symbol уже существует",
        ) from exc
    db.refresh(asset)
    return serialize_asset(asset)


@app.get("/assets/balances", response_model=list[schemas.AssetBalancePublic])
def asset_balances(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[schemas.AssetBalancePublic]:
    active_assets = db.scalars(
        select(models.Asset)
        .where(models.Asset.is_active.is_(True))
        .order_by(models.Asset.display_order, models.Asset.symbol)
    ).all()
    balance_rows = db.scalars(
        select(models.AssetBalance).where(
            models.AssetBalance.user_id == current_user.id
        )
    ).all()
    balance_by_asset = {
        balance.asset_id: int(balance.balance_units or 0)
        for balance in balance_rows
    }
    return [
        serialize_asset_balance(asset, balance_by_asset.get(asset.id, 0))
        for asset in active_assets
    ]


@app.get("/assets/ledger", response_model=list[schemas.AssetLedgerEntryPublic])
def asset_ledger(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[schemas.AssetLedgerEntryPublic]:
    rows = db.scalars(
        select(models.AssetLedgerEntry)
        .where(models.AssetLedgerEntry.user_id == current_user.id)
        .order_by(desc(models.AssetLedgerEntry.created_at))
        .limit(limit)
    ).all()
    return [serialize_ledger_entry(entry) for entry in rows]


@app.get(
    "/admin/ledger/all",
    response_model=list[schemas.AdminLedgerEntryPublic],
    dependencies=[Depends(require_admin)],
)
@app.get(
    "/ledger/all",
    response_model=list[schemas.AdminLedgerEntryPublic],
    dependencies=[Depends(require_admin)],
)
def all_ledger_entries(
    db: Session = Depends(get_db),
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
    asset_symbol: Annotated[str | None, Query(max_length=32)] = None,
    user_id: Annotated[int | None, Query(ge=1)] = None,
    entry_type: Annotated[str | None, Query(max_length=32)] = None,
    direction: Annotated[str | None, Query(max_length=16)] = None,
) -> list[schemas.AdminLedgerEntryPublic]:
    query = (
        select(models.AssetLedgerEntry)
        .join(models.AssetLedgerEntry.user)
        .join(models.AssetLedgerEntry.asset)
    )
    if asset_symbol:
        query = query.where(models.Asset.symbol == asset_symbol.strip().upper())
    if user_id:
        query = query.where(models.AssetLedgerEntry.user_id == user_id)
    if entry_type:
        query = query.where(models.AssetLedgerEntry.entry_type == entry_type.strip())
    if direction:
        query = query.where(models.AssetLedgerEntry.direction == direction.strip())

    rows = db.scalars(
        query
        .order_by(desc(models.AssetLedgerEntry.created_at))
        .limit(limit)
        .offset(offset)
    ).all()
    return [serialize_admin_ledger_entry(entry) for entry in rows]


@app.get(
    "/admin/users",
    response_model=list[schemas.AdminUserPublic],
    dependencies=[Depends(require_admin)],
)
def admin_users(
    db: Session = Depends(get_db),
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
    query: Annotated[str | None, Query(max_length=64)] = None,
) -> list[schemas.AdminUserPublic]:
    statement = select(models.User)
    if query:
        cleaned = f"%{query.strip()}%"
        statement = statement.where(
            or_(
                models.User.telegram_id.ilike(cleaned),
                models.User.username.ilike(cleaned),
                models.User.first_name.ilike(cleaned),
            )
        )
    rows = db.scalars(
        statement.order_by(desc(models.User.created_at)).limit(limit).offset(offset)
    ).all()
    return [serialize_admin_user(user) for user in rows]


@app.get(
    "/admin/transactions",
    response_model=list[schemas.AdminTransactionPublic],
    dependencies=[Depends(require_admin)],
)
def admin_transactions(
    db: Session = Depends(get_db),
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
    user_id: Annotated[int | None, Query(ge=1)] = None,
) -> list[schemas.AdminTransactionPublic]:
    statement = select(models.Transaction)
    if user_id:
        statement = statement.where(
            or_(
                models.Transaction.sender_id == user_id,
                models.Transaction.receiver_id == user_id,
            )
        )
    rows = db.scalars(
        statement
        .order_by(desc(models.Transaction.created_at))
        .limit(limit)
        .offset(offset)
    ).all()
    return [serialize_admin_transaction(transaction) for transaction in rows]


@app.get(
    "/admin/reputation",
    response_model=list[schemas.ReputationEventPublic],
    dependencies=[Depends(require_admin)],
)
@app.get(
    "/admin/karma",
    response_model=list[schemas.ReputationEventPublic],
    dependencies=[Depends(require_admin)],
)
def admin_reputation_events(
    db: Session = Depends(get_db),
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
    user_id: Annotated[int | None, Query(ge=1)] = None,
    event_type: Annotated[str | None, Query(max_length=64)] = None,
) -> list[schemas.ReputationEventPublic]:
    statement = select(models.ReputationEvent).join(models.ReputationEvent.user)
    if user_id:
        statement = statement.where(models.ReputationEvent.user_id == user_id)
    if event_type:
        statement = statement.where(models.ReputationEvent.event_type == event_type.strip())
    rows = db.scalars(
        statement
        .order_by(desc(models.ReputationEvent.created_at))
        .limit(limit)
        .offset(offset)
    ).all()
    return [serialize_reputation_event(event) for event in rows]


@app.get(
    "/admin/statistics",
    response_model=schemas.AdminStatsPublic,
    dependencies=[Depends(require_admin)],
)
def admin_statistics(db: Session = Depends(get_db)) -> schemas.AdminStatsPublic:
    return schemas.AdminStatsPublic(
        users_count=db.scalar(select(func.count(models.User.id))) or 0,
        active_assets_count=db.scalar(
            select(func.count(models.Asset.id)).where(models.Asset.is_active.is_(True))
        ) or 0,
        asset_gifts_count=db.scalar(select(func.count(models.AssetGift.id))) or 0,
        ledger_entries_count=db.scalar(select(func.count(models.AssetLedgerEntry.id))) or 0,
        virtual_transactions_count=db.scalar(select(func.count(models.Transaction.id))) or 0,
        deposits_count=db.scalar(select(func.count(models.AssetDeposit.id))) or 0,
    )


@app.get(
    "/assets/{symbol}/balance",
    response_model=schemas.AssetBalancePublic,
)
def asset_balance_by_symbol(
    symbol: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> schemas.AssetBalancePublic:
    asset = get_asset_by_symbol(db, symbol)
    if not asset or not asset.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Актив не найден",
        )
    return serialize_asset_balance(
        asset,
        get_asset_balance_units(db, current_user.id, asset.id),
    )


@app.post(
    "/asset-gifts/send-random",
    response_model=schemas.AssetGiftSendResponse,
)
@app.post(
    "/asset-gifts/send",
    response_model=schemas.AssetGiftSendResponse,
)
def send_random_asset_gift_endpoint(
    payload: schemas.AssetGiftSendRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> schemas.AssetGiftSendResponse:
    symbol = payload.asset_symbol or payload.symbol
    gift, sender_balance = send_random_asset_gift(
        db=db,
        sender=current_user,
        asset_symbol=symbol or "",
        amount_units=payload.amount_units,
        message=payload.message,
    )
    return schemas.AssetGiftSendResponse(
        message="Asset-подарок отправлен случайному пользователю",
        gift=serialize_asset_gift(gift, current_user.id),
        sender_balance=serialize_asset_balance(gift.asset, sender_balance.balance_units),
    )


@app.get("/asset-gifts", response_model=list[schemas.AssetGiftPublic])
def asset_gifts(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[schemas.AssetGiftPublic]:
    rows = db.scalars(
        select(models.AssetGift)
        .where(
            or_(
                models.AssetGift.sender_id == current_user.id,
                models.AssetGift.receiver_id == current_user.id,
            )
        )
        .order_by(desc(models.AssetGift.created_at))
        .limit(limit)
    ).all()
    return [serialize_asset_gift(gift, current_user.id) for gift in rows]


@app.get("/asset-gifts/history", response_model=list[schemas.AssetGiftPublic])
def asset_gifts_history(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[schemas.AssetGiftPublic]:
    return asset_gifts(current_user=current_user, db=db, limit=limit)


@app.get("/asset-gifts/feed", response_model=list[schemas.AssetGiftFeedItem])
def asset_gifts_feed(
    db: Session = Depends(get_db),
    limit: Annotated[int, Query(ge=1, le=100)] = 30,
) -> list[schemas.AssetGiftFeedItem]:
    rows = db.scalars(
        select(models.AssetGift)
        .where(models.AssetGift.status == "completed")
        .order_by(desc(models.AssetGift.created_at))
        .limit(limit)
    ).all()
    return [serialize_asset_gift_feed_item(gift) for gift in rows]


@app.get(
    "/asset-gifts/leaderboard",
    response_model=schemas.AssetGiftLeaderboardResponse,
)
def asset_gifts_leaderboard(
    symbol: Annotated[str, Query(min_length=1, max_length=32)] = TDSD_ASSET_SYMBOL,
    db: Session = Depends(get_db),
) -> schemas.AssetGiftLeaderboardResponse:
    asset = get_asset_by_symbol(db, symbol)
    if not asset or not asset.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Актив не найден",
        )

    sender_total = func.sum(models.AssetGift.amount_units).label("total_units")
    sender_rows = db.execute(
        select(models.User, sender_total)
        .join(models.AssetGift, models.AssetGift.sender_id == models.User.id)
        .where(
            models.AssetGift.asset_id == asset.id,
            models.AssetGift.status == "completed",
        )
        .group_by(models.User.id)
        .order_by(desc(sender_total))
        .limit(100)
    ).all()

    receiver_total = func.sum(models.AssetGift.net_amount_units).label("total_units")
    receiver_rows = db.execute(
        select(models.User, receiver_total)
        .join(models.AssetGift, models.AssetGift.receiver_id == models.User.id)
        .where(
            models.AssetGift.asset_id == asset.id,
            models.AssetGift.status == "completed",
        )
        .group_by(models.User.id)
        .order_by(desc(receiver_total))
        .limit(100)
    ).all()

    return schemas.AssetGiftLeaderboardResponse(
        symbol=asset.symbol,
        asset_name=asset.name,
        senders=[
            serialize_asset_gift_leaderboard_user(user, total_units, asset)
            for user, total_units in sender_rows
        ],
        receivers=[
            serialize_asset_gift_leaderboard_user(user, total_units, asset)
            for user, total_units in receiver_rows
        ],
    )


@app.post(
    "/asset-deposits/create",
    response_model=schemas.AssetDepositCreateResponse,
)
def create_asset_deposit(
    payload: schemas.AssetDepositCreateRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> schemas.AssetDepositCreateResponse:
    asset = get_asset_by_symbol(db, payload.asset_symbol)
    if not asset or not asset.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Актив не найден",
        )
    if not current_user.ton_wallet_address:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Сначала сохраните кошелек в профиле",
        )

    try:
        provider = get_provider_for_asset(asset)
        instructions = provider.create_deposit_instructions(
            asset=asset,
            user=current_user,
            amount_units=payload.amount_units,
        )
    except ProviderError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    deposit = models.AssetDeposit(
        user_id=current_user.id,
        asset_id=asset.id,
        wallet_address=parse_wallet_address_or_400(current_user.ton_wallet_address),
        target_wallet_address=instructions.target_wallet_address,
        amount_units=instructions.amount_units,
        comment=instructions.comment,
        status="pending",
        provider=instructions.provider,
        network=instructions.network,
    )
    db.add(deposit)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Не удалось создать пополнение, попробуйте еще раз",
        ) from exc
    db.refresh(deposit)
    return serialize_asset_deposit_create(deposit)


@app.post(
    "/asset-deposits/{deposit_id}/verify",
    response_model=schemas.AssetDepositVerifyResponse,
)
def verify_asset_deposit(
    deposit_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> schemas.AssetDepositVerifyResponse:
    deposit = db.scalar(
        select(models.AssetDeposit).where(
            models.AssetDeposit.id == deposit_id,
            models.AssetDeposit.user_id == current_user.id,
        )
    )
    if not deposit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пополнение не найдено",
        )

    if deposit.status == "confirmed":
        balance = db.scalar(
            select(models.AssetBalance).where(
                models.AssetBalance.user_id == current_user.id,
                models.AssetBalance.asset_id == deposit.asset_id,
            )
        )
        message = "Пополнение уже подтверждено"
        if is_tdsd_fixed_price_purchase(deposit):
            try:
                message = ensure_tdsd_hot_wallet_payout(
                    db=db,
                    deposit=deposit,
                    current_user=current_user,
                    payout_amount_units=tdsd_payout_amount_units(deposit),
                )
            except ValueError as exc:
                deposit.payout_status = "failed"
                deposit.payout_failed_reason = str(exc)[:500]
                db.commit()
                db.refresh(deposit)
                log_tdsd_payout_exception(
                    "TDSD payout amount calculation failed",
                    exc,
                    deposit,
                    deposit.amount_units,
                )
                message = PUBLIC_SEND_FAILED_MESSAGE
        return asset_deposit_verify_response(
            deposit,
            message,
            balance,
        )
    if deposit.status == "failed":
        return asset_deposit_verify_response(
            deposit,
            "Пополнение уже помечено как неуспешное",
        )

    expires_at = deposit.created_at + timedelta(
        minutes=DEPOSIT_CONFIRMATION_TIMEOUT_MINUTES
    )
    if datetime.utcnow() > expires_at:
        mark_asset_deposit_failed(
            deposit,
            "Транзакция не найдена за отведенное время",
        )
        db.commit()
        db.refresh(deposit)
        return asset_deposit_verify_response(
            deposit,
            "Время ожидания пополнения истекло",
        )

    try:
        provider = get_provider_for_asset(deposit.asset)
        verification = provider.verify_deposit(deposit, current_user)
    except ProviderError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    if verification.retryable_error:
        deposit.failed_reason = verification.retryable_error
        db.commit()
        db.refresh(deposit)
        return asset_deposit_verify_response(
            deposit,
            "Не удалось проверить пополнение. Попробуйте позже.",
        )

    if verification.failed_reason:
        mark_asset_deposit_failed(deposit, verification.failed_reason)
        db.commit()
        db.refresh(deposit)
        return asset_deposit_verify_response(
            deposit,
            "Транзакция найдена, но не прошла проверку",
        )

    if not verification.confirmed:
        return asset_deposit_verify_response(
            deposit,
            "Транзакция пока не найдена, попробуйте позже",
        )

    if not verification.tx_hash:
        mark_asset_deposit_failed(deposit, "Не удалось получить подтверждение транзакции")
        db.commit()
        db.refresh(deposit)
        return asset_deposit_verify_response(
            deposit,
            "Не удалось получить подтверждение транзакции",
        )

    used_asset_tx = db.scalar(
        select(models.AssetDeposit).where(
            models.AssetDeposit.tx_hash == verification.tx_hash,
            models.AssetDeposit.status == "confirmed",
            models.AssetDeposit.id != deposit.id,
        )
    )
    used_ton_tx = db.scalar(
        select(models.TonDeposit).where(
            models.TonDeposit.tx_hash == verification.tx_hash,
            models.TonDeposit.status == "confirmed",
        )
    )
    if used_asset_tx or used_ton_tx:
        mark_asset_deposit_failed(
            deposit,
            "Этот tx_hash уже использован в другом депозите",
        )
        db.commit()
        db.refresh(deposit)
        return asset_deposit_verify_response(
            deposit,
            "Эта транзакция уже была использована",
        )

    deposit.tx_hash = verification.tx_hash
    deposit.status = "confirmed"
    deposit.failed_reason = None
    deposit.confirmed_at = datetime.utcnow()
    deposit_amount_units = int(deposit.amount_units or 0)
    buy_quote = None
    if deposit.asset.symbol == TDSD_ASSET_SYMBOL:
        try:
            buy_quote = calculate_buy_commission(deposit_amount_units)
        except ValueError as exc:
            mark_asset_deposit_failed(deposit, str(exc))
            db.commit()
            db.refresh(deposit)
            return asset_deposit_verify_response(
                deposit,
                "Покупка TDSD не прошла проверку комиссии",
            )
    credit_amount_units = (
        buy_quote.credited_amount_units
        if buy_quote is not None
        else deposit_amount_units
    )
    balance = credit_asset_balance(
        db=db,
        user=current_user,
        asset=deposit.asset,
        amount_units=credit_amount_units,
        entry_type="deposit",
        related_entity_type="asset_deposit",
        related_entity_id=deposit.id,
        comment=f"Пополнение {deposit.asset.symbol} #{deposit.id}",
    )
    if buy_quote:
        if buy_quote.commission_amount_units > 0:
            db.add(
                models.AssetLedgerEntry(
                    user_id=current_user.id,
                    asset_id=deposit.asset.id,
                    entry_type="fee_purchase",
                    amount_units=buy_quote.commission_amount_units,
                    direction="debit",
                    related_entity_type="asset_deposit",
                    related_entity_id=deposit.id,
                    balance_after_units=balance.balance_units,
                    comment=(
                        f"{decimal_label(buy_quote.commission_percent)}% "
                        f"комиссия покупки TDSD удержана перед зачислением "
                        f"пополнения #{deposit.id}"
                    ),
                )
            )
            treasury_user = get_or_create_treasury_user(db)
            credit_asset_balance(
                db=db,
                user=treasury_user,
                asset=deposit.asset,
                amount_units=buy_quote.treasury_amount_units,
                entry_type="treasury_income",
                related_entity_type="asset_deposit",
                related_entity_id=deposit.id,
                comment=f"Treasury income from TDSD purchase #{deposit.id}",
            )
    if deposit.asset.symbol == TON_ASSET_SYMBOL:
        sync_legacy_ton_balance_units(current_user, balance.balance_units)
    if deposit.asset.symbol == REFERRAL_REWARD_ASSET_SYMBOL:
        credit_referral_reward_for_purchase(
            db=db,
            buyer=current_user,
            asset=deposit.asset,
            purchase_id=deposit.id,
            purchase_amount_units=int(deposit.amount_units or 0),
        )

    db.commit()
    db.refresh(deposit)
    db.refresh(balance)
    db.refresh(current_user)
    message = "Пополнение подтверждено"
    if is_tdsd_fixed_price_purchase(deposit):
        message = ensure_tdsd_hot_wallet_payout(
            db=db,
            deposit=deposit,
            current_user=current_user,
            payout_amount_units=credit_amount_units,
        )
        db.refresh(balance)
        db.refresh(current_user)
    return asset_deposit_verify_response(
        deposit,
        message,
        balance,
    )


@app.get("/asset-deposits", response_model=list[schemas.AssetDepositPublic])
def asset_deposits(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[schemas.AssetDepositPublic]:
    rows = db.scalars(
        select(models.AssetDeposit)
        .where(models.AssetDeposit.user_id == current_user.id)
        .order_by(desc(models.AssetDeposit.created_at))
        .limit(limit)
    ).all()
    return [serialize_asset_deposit(deposit) for deposit in rows]


@app.post("/ton/deposits/create", response_model=schemas.TonDepositCreateResponse)
def create_ton_deposit(
    payload: schemas.TonDepositCreateRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> schemas.TonDepositCreateResponse:
    if not current_user.ton_wallet_address:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Сначала сохраните TON-кошелек в профиле",
        )

    target_wallet_address = ensure_testnet_deposit_config()
    amount_ton = payload.amount_ton
    if amount_ton < MIN_DEPOSIT_TON:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Минимальный депозит: {MIN_DEPOSIT_TON} TON",
        )
    if amount_ton > MAX_DEPOSIT_TON:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Максимальный депозит: {MAX_DEPOSIT_TON} TON",
        )

    amount_nano = amount_ton_to_nano(amount_ton)
    if amount_nano <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Сумма депозита слишком мала",
        )

    deposit = models.TonDeposit(
        user_id=current_user.id,
        wallet_address=current_user.ton_wallet_address,
        target_wallet_address=target_wallet_address,
        network=TON_NETWORK,
        amount_ton=amount_ton,
        amount_nano=amount_nano,
        tx_hash=f"pending:{secrets.token_urlsafe(12)}",
        comment="pending",
        status="pending",
    )
    db.add(deposit)
    db.flush()
    deposit.comment = build_deposit_comment(current_user.id, deposit.id)
    deposit.tx_hash = f"pending:{deposit.comment}"
    db.commit()
    db.refresh(deposit)

    return schemas.TonDepositCreateResponse(
        deposit_id=deposit.id,
        amount_ton=float(deposit.amount_ton),
        amount_nano=deposit.amount_nano,
        target_wallet_address=deposit.target_wallet_address,
        comment=deposit.comment,
        status="pending",
        network=deposit.network,
    )


@app.post(
    "/ton/deposits/{deposit_id}/verify",
    response_model=schemas.TonDepositVerifyResponse,
)
def verify_ton_deposit(
    deposit_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> schemas.TonDepositVerifyResponse:
    deposit = db.scalar(
        select(models.TonDeposit).where(
            models.TonDeposit.id == deposit_id,
            models.TonDeposit.user_id == current_user.id,
        )
    )
    if not deposit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Депозит не найден",
        )

    if deposit.status == "confirmed":
        return ton_verify_response(
            deposit,
            current_user,
            "Депозит уже подтвержден",
            db,
        )
    if deposit.status == "failed":
        return ton_verify_response(
            deposit,
            current_user,
            "Депозит уже помечен как failed",
            db,
        )

    if not deposit.target_wallet_address or not deposit.comment or not deposit.amount_nano:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Этот депозит нельзя проверить через TON testnet flow",
        )

    expires_at = deposit.created_at + timedelta(
        minutes=DEPOSIT_CONFIRMATION_TIMEOUT_MINUTES
    )
    if datetime.utcnow() > expires_at:
        mark_deposit_failed(deposit, "Транзакция не найдена до истечения timeout")
        db.commit()
        db.refresh(deposit)
        return ton_verify_response(
            deposit,
            current_user,
            "Время ожидания депозита истекло",
            db,
        )

    try:
        search_result = verify_deposit(deposit, deposit.wallet_address)
    except TonCenterError as exc:
        # External TON Center errors are temporary infrastructure failures.
        # Do not mark the deposit as failed: the user must be able to retry verification.
        deposit.failed_reason = f"Последняя ошибка TON Center API: {str(exc)[:430]}"
        db.commit()
        db.refresh(deposit)
        return ton_verify_response(
            deposit,
            current_user,
            "Не удалось проверить TON testnet transaction. Попробуйте позже.",
            db,
        )

    if search_result.failed_reason:
        mark_deposit_failed(deposit, search_result.failed_reason)
        db.commit()
        db.refresh(deposit)
        return ton_verify_response(
            deposit,
            current_user,
            "Транзакция найдена, но не прошла проверку",
            db,
        )

    matched = search_result.matched

    if not matched:
        return ton_verify_response(
            deposit,
            current_user,
            "Транзакция пока не найдена, попробуйте позже",
            db,
        )

    used_tx = db.scalar(
        select(models.TonDeposit).where(
            models.TonDeposit.tx_hash == matched.tx_hash,
            models.TonDeposit.status == "confirmed",
            models.TonDeposit.id != deposit.id,
        )
    )
    if used_tx:
        mark_deposit_failed(deposit, "Этот tx_hash уже использован в другом депозите")
        db.commit()
        db.refresh(deposit)
        return ton_verify_response(
            deposit,
            current_user,
            "Эта TON transaction уже была использована",
            db,
        )

    ton_asset = get_ton_asset(db)
    deposit.tx_hash = matched.tx_hash
    deposit.status = "confirmed"
    deposit.failed_reason = None
    deposit.confirmed_at = datetime.utcnow()
    balance = credit_asset_balance(
        db=db,
        user=current_user,
        asset=ton_asset,
        amount_units=int(deposit.amount_nano or 0),
        entry_type="deposit",
        related_entity_type="ton_deposit",
        related_entity_id=deposit.id,
        comment=f"TON testnet deposit #{deposit.id}",
    )
    sync_legacy_ton_balance_units(current_user, balance.balance_units)
    db.commit()
    db.refresh(deposit)
    db.refresh(current_user)
    return ton_verify_response(
        deposit,
        current_user,
        message="Депозит подтвержден",
        db=db,
    )


@app.get("/ton/balance", response_model=schemas.TonBalanceResponse)
def ton_balance(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> schemas.TonBalanceResponse:
    ton_balance_nano = get_ton_balance_units(db, current_user)
    return schemas.TonBalanceResponse(
        ton_balance_nano=ton_balance_nano,
        ton_balance=nano_to_ton_float(ton_balance_nano),
    )


@app.post("/ton/deposits/mock", response_model=schemas.TonDepositPublic)
def create_mock_ton_deposit(
    payload: schemas.TonDepositCreateMockRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> schemas.TonDepositPublic:
    if APP_ENV == "production" or not (ALLOW_MOCK_AUTH or APP_ENV == "development"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Mock deposits доступны только в dev/mock режиме",
        )

    wallet_address = payload.wallet_address or current_user.ton_wallet_address
    if not wallet_address:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Сначала сохраните TON-кошелек или передайте wallet_address",
        )

    amount_decimal = Decimal(str(payload.amount_ton))
    comment = f"mock:{current_user.id}:{secrets.token_urlsafe(8)}"
    duplicate = db.scalar(
        select(models.TonDeposit).where(
            models.TonDeposit.tx_hash == payload.tx_hash,
            models.TonDeposit.status == "confirmed",
        )
    )
    if duplicate:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Депозит с таким tx_hash уже подтвержден",
        )

    deposit = models.TonDeposit(
        user_id=current_user.id,
        wallet_address=parse_wallet_address_or_400(wallet_address),
        target_wallet_address=parse_wallet_address_or_400(
            get_tdsd_payment_wallet_address() or wallet_address
        ),
        network=TON_NETWORK,
        amount_ton=amount_decimal,
        amount_nano=amount_ton_to_nano(amount_decimal),
        tx_hash=payload.tx_hash,
        comment=comment,
        status=payload.status,
        confirmed_at=datetime.utcnow() if payload.status == "confirmed" else None,
    )
    db.add(deposit)
    db.flush()
    if payload.status == "confirmed":
        ton_asset = get_ton_asset(db)
        balance = credit_asset_balance(
            db=db,
            user=current_user,
            asset=ton_asset,
            amount_units=int(deposit.amount_nano or 0),
            entry_type="deposit",
            related_entity_type="ton_deposit",
            related_entity_id=deposit.id,
            comment=f"Mock TON testnet deposit {deposit.tx_hash}",
        )
        sync_legacy_ton_balance_units(current_user, balance.balance_units)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Депозит с таким tx_hash уже существует",
        ) from exc
    db.refresh(deposit)
    return serialize_ton_deposit(deposit)


@app.get("/ton/deposits", response_model=list[schemas.TonDepositPublic])
def ton_deposits(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[schemas.TonDepositPublic]:
    rows = db.scalars(
        select(models.TonDeposit)
        .where(models.TonDeposit.user_id == current_user.id)
        .order_by(desc(models.TonDeposit.created_at))
        .limit(limit)
    ).all()
    return [serialize_ton_deposit(deposit) for deposit in rows]


@app.post("/gift/send", response_model=schemas.GiftSendResponse)
def send_gift(
    payload: schemas.GiftSendRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> schemas.GiftSendResponse:
    if current_user.balance < payload.amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Недостаточно монет",
        )

    available_receivers = db.scalar(
        select(func.count(models.User.id)).where(
            models.User.id != current_user.id,
            models.User.telegram_id.is_not(None),
            not_(models.User.telegram_id.like("system:%")),
        )
    )
    if not available_receivers:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Нужно минимум два пользователя",
        )

    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    # Лимит считается по количеству отправок за текущие UTC-сутки.
    sent_today = db.scalar(
        select(func.count(models.Transaction.id)).where(
            models.Transaction.sender_id == current_user.id,
            models.Transaction.created_at >= today_start,
        )
    )
    if sent_today >= DAILY_SEND_LIMIT:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Дневной лимит: {DAILY_SEND_LIMIT} отправок",
        )

    receiver = db.scalar(
        select(models.User)
        .where(
            models.User.id != current_user.id,
            models.User.telegram_id.is_not(None),
            not_(models.User.telegram_id.like("system:%")),
        )
        .order_by(func.random())
        .limit(1)
    )
    if not receiver:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Не удалось выбрать получателя",
        )

    # Деньги не используются: это простое перемещение виртуальных монет внутри SQLite.
    current_user.balance -= payload.amount
    current_user.total_sent += payload.amount

    receiver.balance += payload.amount
    receiver.total_received += payload.amount

    transaction = models.Transaction(
        sender_id=current_user.id,
        receiver_id=receiver.id,
        amount=payload.amount,
        message=payload.message,
    )
    db.add(transaction)
    db.flush()
    add_reputation_event(
        db=db,
        user=current_user,
        event_type="virtual_gift_sent",
        karma_delta=payload.amount,
        reputation_delta=max(1, payload.amount // 5),
        related_entity_type="transaction",
        related_entity_id=transaction.id,
        comment="Virtual gift sent",
    )
    db.commit()
    db.refresh(current_user)
    db.refresh(transaction)

    return schemas.GiftSendResponse(
        message="Подарок отправлен случайному пользователю",
        user=serialize_user(current_user, db),
        transaction=serialize_transaction(transaction, current_user.id),
    )


@app.get("/transactions", response_model=list[schemas.TransactionPublic])
def transactions(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[schemas.TransactionPublic]:
    rows = db.scalars(
        select(models.Transaction)
        .where(
            or_(
                models.Transaction.sender_id == current_user.id,
                models.Transaction.receiver_id == current_user.id,
            )
        )
        .order_by(desc(models.Transaction.created_at))
        .limit(limit)
    ).all()
    return [serialize_transaction(transaction, current_user.id) for transaction in rows]


@app.get(
    "/transactions/public",
    response_model=list[schemas.PublicTransactionFeedItem],
)
def public_transactions(
    db: Session = Depends(get_db),
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
) -> list[schemas.PublicTransactionFeedItem]:
    virtual_rows = db.scalars(
        select(models.Transaction).order_by(desc(models.Transaction.created_at)).limit(limit)
    ).all()
    asset_rows = db.scalars(
        select(models.AssetGift)
        .where(models.AssetGift.status == "completed")
        .order_by(desc(models.AssetGift.created_at))
        .limit(limit)
    ).all()
    fee_rows = db.scalars(
        select(models.AssetLedgerEntry)
        .where(models.AssetLedgerEntry.entry_type == "treasury_income")
        .order_by(desc(models.AssetLedgerEntry.created_at))
        .limit(limit)
    ).all()
    referral_rows = db.scalars(
        select(models.ReferralReward)
        .where(models.ReferralReward.status == "credited")
        .order_by(desc(models.ReferralReward.created_at))
        .limit(limit)
    ).all()
    referral_decimals = referral_asset_decimals(db)
    rows = [
        *[serialize_public_virtual_transaction(transaction) for transaction in virtual_rows],
        *[serialize_public_asset_transaction(gift) for gift in asset_rows],
        *[serialize_public_fee_entry(entry) for entry in fee_rows],
        *[
            serialize_public_referral_reward(reward, referral_decimals)
            for reward in referral_rows
        ],
    ]
    return sorted(rows, key=lambda item: item.created_at, reverse=True)[:limit]


@app.get("/leaderboard", response_model=schemas.LeaderboardResponse)
def leaderboard(db: Session = Depends(get_db)) -> schemas.LeaderboardResponse:
    top_karma = db.scalars(
        select(models.User)
        .order_by(desc(models.User.karma), models.User.created_at)
        .limit(100)
    ).all()
    top_senders = db.scalars(
        select(models.User)
        .order_by(desc(models.User.total_sent), models.User.created_at)
        .limit(100)
    ).all()
    top_receivers = db.scalars(
        select(models.User)
        .order_by(desc(models.User.total_received), models.User.created_at)
        .limit(100)
    ).all()
    return schemas.LeaderboardResponse(
        karma=[serialize_leaderboard_user(user) for user in top_karma],
        senders=[serialize_leaderboard_user(user) for user in top_senders],
        receivers=[serialize_leaderboard_user(user) for user in top_receivers],
    )
