from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy import desc, func, not_, select
from sqlalchemy.orm import Session

from . import models
from .config import TREASURY_USER_ID
from .fee_service import calculate_transfer_fee


SYSTEM_TREASURY_TELEGRAM_ID = "system:treasury"


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


def debit_asset_balance(
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
            detail="Сумма списания должна быть больше нуля",
        )

    balance = get_or_create_asset_balance(db, user.id, asset.id)
    if int(balance.balance_units or 0) < amount_units:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Недостаточно средств",
        )

    balance.balance_units = int(balance.balance_units or 0) - amount_units
    balance.updated_at = datetime.utcnow()
    db.add(
        models.AssetLedgerEntry(
            user_id=user.id,
            asset_id=asset.id,
            entry_type=entry_type,
            amount_units=amount_units,
            direction="debit",
            related_entity_type=related_entity_type,
            related_entity_id=related_entity_id,
            balance_after_units=balance.balance_units,
            comment=comment,
        )
    )
    return balance


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
            detail="Сумма начисления должна быть больше нуля",
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


def enforce_asset_gift_limits(db: Session, sender: models.User) -> None:
    # Stage 7: asset gift rate limits are intentionally disabled for MVP testing.
    # Keep the function as an extension point for future anti-abuse/admin controls.
    return None


def calculate_karma(asset: models.Asset, amount_units: int) -> int:
    scale = 10 ** max(int(asset.decimals or 0), 0)
    normalized = int(amount_units) // scale if scale else int(amount_units)
    return max(1, normalized)


def get_or_create_treasury_user(db: Session) -> models.User:
    if TREASURY_USER_ID is not None:
        treasury_user = db.get(models.User, TREASURY_USER_ID)
        if treasury_user:
            return treasury_user

    treasury_user = db.scalar(
        select(models.User).where(
            models.User.telegram_id == SYSTEM_TREASURY_TELEGRAM_ID
        )
    )
    if treasury_user:
        return treasury_user

    treasury_user = models.User(
        telegram_id=SYSTEM_TREASURY_TELEGRAM_ID,
        username="treasury",
        first_name="Tuda Suda Treasury",
        balance=0,
        karma=0,
        total_sent=0,
        total_received=0,
    )
    db.add(treasury_user)
    db.flush()
    return treasury_user


def select_random_receiver(
    db: Session,
    sender: models.User,
) -> models.User:
    base_conditions = [
        models.User.id != sender.id,
        models.User.telegram_id.is_not(None),
        not_(models.User.telegram_id.like("system:%")),
    ]
    total_candidates = db.scalar(
        select(func.count(models.User.id)).where(*base_conditions)
    )
    if not total_candidates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Нужно минимум два пользователя",
        )

    last_gift = db.scalar(
        select(models.AssetGift)
        .where(
            models.AssetGift.sender_id == sender.id,
            models.AssetGift.status == "completed",
        )
        .order_by(desc(models.AssetGift.created_at))
        .limit(1)
    )
    conditions = list(base_conditions)
    if last_gift and total_candidates > 1:
        conditions.append(models.User.id != last_gift.receiver_id)

    receiver = db.scalar(
        select(models.User)
        .where(*conditions)
        .order_by(func.random())
        .limit(1)
    )
    if not receiver:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Не удалось выбрать получателя",
        )
    return receiver


def send_random_asset_gift(
    db: Session,
    sender: models.User,
    asset_symbol: str,
    amount_units: int,
    message: str | None = None,
) -> tuple[models.AssetGift, models.AssetBalance]:
    try:
        asset = db.scalar(
            select(models.Asset).where(models.Asset.symbol == asset_symbol.upper())
        )
        if not asset or not asset.is_active:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Актив не найден",
            )

        amount_units = int(amount_units)
        if amount_units <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Сумма подарка должна быть больше нуля",
            )

        enforce_asset_gift_limits(db, sender)

        try:
            fee_quote = calculate_transfer_fee(asset.symbol, amount_units)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(exc),
            ) from exc
        fee_units = fee_quote.fee_amount_units
        net_amount_units = fee_quote.recipient_amount_units

        receiver = select_random_receiver(db, sender)
        gift = models.AssetGift(
            sender_id=sender.id,
            receiver_id=receiver.id,
            asset_id=asset.id,
            amount_units=amount_units,
            fee_units=fee_units,
            net_amount_units=net_amount_units,
            message=message,
            status="completed",
        )
        db.add(gift)
        db.flush()

        sender_balance = debit_asset_balance(
            db=db,
            user=sender,
            asset=asset,
            amount_units=amount_units,
            entry_type="gift_sent",
            related_entity_type="asset_gift",
            related_entity_id=gift.id,
            comment=f"Asset gift #{gift.id}",
        )
        credit_asset_balance(
            db=db,
            user=receiver,
            asset=asset,
            amount_units=net_amount_units,
            entry_type="gift_received",
            related_entity_type="asset_gift",
            related_entity_id=gift.id,
            comment=f"Asset gift #{gift.id}",
        )

        if fee_units > 0:
            db.add(
                models.AssetLedgerEntry(
                    user_id=sender.id,
                    asset_id=asset.id,
                    entry_type="fee_transfer",
                    amount_units=fee_units,
                    direction="debit",
                    related_entity_type="asset_gift",
                    related_entity_id=gift.id,
                    balance_after_units=sender_balance.balance_units,
                    comment=f"Service fee included in asset gift #{gift.id}",
                )
            )
            treasury_user = get_or_create_treasury_user(db)
            credit_asset_balance(
                db=db,
                user=treasury_user,
                asset=asset,
                amount_units=fee_units,
                entry_type="treasury_income",
                related_entity_type="asset_gift",
                related_entity_id=gift.id,
                comment=f"Treasury income from asset gift #{gift.id}",
            )

        karma_delta = calculate_karma(asset, amount_units)
        sender.karma += karma_delta
        sender.reputation = max(0, int(sender.reputation or 0) + max(1, karma_delta // 2))
        sender.community_weight = max(
            0,
            int(sender.reputation or 0)
            + int(sender.karma or 0) // 10
            - int(sender.risk_score or 0),
        )
        db.add(
            models.ReputationEvent(
                user_id=sender.id,
                event_type="asset_gift_sent",
                karma_delta=karma_delta,
                reputation_delta=max(1, karma_delta // 2),
                related_entity_type="asset_gift",
                related_entity_id=gift.id,
                comment=f"{asset.symbol} gift sent",
            )
        )
        db.commit()
        db.refresh(gift)
        db.refresh(sender_balance)
        return gift, sender_balance
    except Exception:
        db.rollback()
        raise
