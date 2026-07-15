from datetime import date, datetime, timedelta
from typing import Literal

from sqlalchemy import and_, case, desc, func, not_, or_, select
from sqlalchemy.orm import Session, aliased, joinedload

from . import models, schemas
from .config import TDSD_ASSET_SYMBOL
from .fee_service import calculate_tdsd_fixed_price_quote


AdminPeriod = Literal["today", "7d", "30d", "all"]
SUCCESSFUL_PAYOUT_STATUSES = ("sent", "confirmed")


def admin_period_start(period: AdminPeriod, now: datetime) -> datetime | None:
    if period == "today":
        return now.replace(hour=0, minute=0, second=0, microsecond=0)
    if period == "7d":
        return now - timedelta(days=7)
    if period == "30d":
        return now - timedelta(days=30)
    return None


def _real_user_conditions() -> list[object]:
    return [not_(models.User.telegram_id.like("system:%"))]


def _period_condition(column: object, start: datetime | None) -> list[object]:
    return [column >= start] if start is not None else []


def _count(db: Session, statement: object) -> int:
    return int(db.scalar(statement) or 0)


def _format_units(amount_units: int, decimals: int) -> str:
    amount = int(amount_units or 0)
    sign = "-" if amount < 0 else ""
    absolute = abs(amount)
    if decimals <= 0:
        return f"{sign}{absolute}"
    scale = 10 ** decimals
    whole = absolute // scale
    fraction = str(absolute % scale).rjust(decimals, "0").rstrip("0")
    return f"{sign}{whole}.{fraction}" if fraction else f"{sign}{whole}"


def _tdsd_asset(db: Session) -> models.Asset | None:
    return db.scalar(
        select(models.Asset).where(models.Asset.symbol == TDSD_ASSET_SYMBOL)
    )


def _payment_amount_nano(amount_units: int, decimals: int) -> int:
    if amount_units <= 0:
        return 0
    try:
        return calculate_tdsd_fixed_price_quote(
            amount_units,
            decimals,
        ).payment_amount_nano
    except ValueError:
        return 0


def _user_label(user: models.User) -> str:
    if user.username:
        return f"@{user.username}"
    if user.first_name:
        return user.first_name
    return f"User #{user.id}"


def build_admin_users_page(
    db: Session,
    *,
    limit: int,
    offset: int,
    query: str | None = None,
) -> schemas.AdminDashboardUsersPage:
    conditions = _real_user_conditions()
    cleaned_query = (query or "").strip()
    if cleaned_query:
        pattern = f"%{cleaned_query}%"
        conditions.append(
            or_(
                models.User.telegram_id.ilike(pattern),
                models.User.username.ilike(pattern),
                models.User.first_name.ilike(pattern),
                models.User.ton_wallet_address.ilike(pattern),
            )
        )

    total = _count(
        db,
        select(func.count(models.User.id)).where(*conditions),
    )
    referrer = aliased(models.User)
    rows = db.execute(
        select(models.User, referrer)
        .outerjoin(referrer, models.User.referred_by_user_id == referrer.id)
        .where(*conditions)
        .order_by(desc(models.User.created_at), desc(models.User.id))
        .limit(limit)
        .offset(offset)
    ).all()

    asset = _tdsd_asset(db)
    balances_by_user: dict[int, int] = {}
    user_ids = [user.id for user, _ in rows]
    if asset is not None and user_ids:
        balances_by_user = {
            int(user_id): int(balance_units or 0)
            for user_id, balance_units in db.execute(
                select(
                    models.AssetBalance.user_id,
                    models.AssetBalance.balance_units,
                ).where(
                    models.AssetBalance.asset_id == asset.id,
                    models.AssetBalance.user_id.in_(user_ids),
                )
            ).all()
        }

    tdsd_decimals = int(asset.decimals if asset else 9)
    items = []
    for user, referred_by in rows:
        tdsd_balance_units = balances_by_user.get(user.id, 0)
        ton_balance_nano = int(user.ton_balance_nano or 0)
        items.append(
            schemas.AdminDashboardUserItem(
                id=user.id,
                telegram_id=user.telegram_id,
                username=user.username,
                first_name=user.first_name,
                photo_url=user.photo_url,
                balance=int(user.balance or 0),
                karma=int(user.karma or 0),
                reputation=int(user.reputation or 0),
                risk_score=int(user.risk_score or 0),
                community_weight=int(user.community_weight or 0),
                total_sent=int(user.total_sent or 0),
                total_received=int(user.total_received or 0),
                ton_balance_nano=ton_balance_nano,
                ton_balance_display=_format_units(ton_balance_nano, 9),
                tdsd_balance_units=tdsd_balance_units,
                tdsd_balance_display=_format_units(
                    tdsd_balance_units,
                    tdsd_decimals,
                ),
                ton_wallet_address=user.ton_wallet_address,
                ton_wallet_connected_at=user.ton_wallet_connected_at,
                referral_code=user.referral_code,
                referred_by_user_id=user.referred_by_user_id,
                referrer=_user_label(referred_by) if referred_by else None,
                referred_at=user.referred_at,
                created_at=user.created_at,
                last_active_at=user.last_active_at,
            )
        )

    return schemas.AdminDashboardUsersPage(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )


def build_admin_overview(
    db: Session,
    period: AdminPeriod,
    now: datetime | None = None,
) -> schemas.AdminDashboardOverview:
    generated_at = now or datetime.utcnow()
    start = admin_period_start(period, generated_at)
    asset = _tdsd_asset(db)
    decimals = int(asset.decimals if asset else 9)

    real_users = _real_user_conditions()
    users_total = _count(
        db,
        select(func.count(models.User.id)).where(*real_users),
    )
    new_users = _count(
        db,
        select(func.count(models.User.id)).where(
            *real_users,
            *_period_condition(models.User.created_at, start),
        ),
    )
    active_users = _count(
        db,
        select(func.count(models.User.id)).where(
            *real_users,
            models.User.last_active_at.is_not(None),
            *_period_condition(models.User.last_active_at, start),
        ),
    )

    def active_since(days: int) -> int:
        return _count(
            db,
            select(func.count(models.User.id)).where(
                *real_users,
                models.User.last_active_at >= generated_at - timedelta(days=days),
            ),
        )

    wallets_connected = _count(
        db,
        select(func.count(models.User.id)).where(
            *real_users,
            models.User.ton_wallet_address.is_not(None),
            models.User.ton_wallet_address != "",
        ),
    )

    gift_conditions: list[object] = [models.AssetGift.status == "completed"]
    if asset:
        gift_conditions.append(models.AssetGift.asset_id == asset.id)
    else:
        gift_conditions.append(models.AssetGift.id < 0)
    gift_conditions.extend(_period_condition(models.AssetGift.created_at, start))
    gift_row = db.execute(
        select(
            func.count(models.AssetGift.id),
            func.coalesce(func.sum(models.AssetGift.amount_units), 0),
            func.coalesce(func.sum(models.AssetGift.net_amount_units), 0),
            func.coalesce(func.sum(models.AssetGift.fee_units), 0),
            func.count(func.distinct(models.AssetGift.sender_id)),
            func.count(func.distinct(models.AssetGift.receiver_id)),
        ).where(*gift_conditions)
    ).one()
    gifts_count = int(gift_row[0] or 0)
    gift_gross_units = int(gift_row[1] or 0)
    gift_net_units = int(gift_row[2] or 0)
    gift_fee_units = int(gift_row[3] or 0)
    gift_average_units = gift_gross_units // gifts_count if gifts_count else 0

    purchase_conditions: list[object] = [
        models.AssetDeposit.provider == "tdsd_fixed_price",
    ]
    if asset:
        purchase_conditions.append(models.AssetDeposit.asset_id == asset.id)
    else:
        purchase_conditions.append(models.AssetDeposit.id < 0)
    purchase_conditions.extend(
        _period_condition(models.AssetDeposit.created_at, start)
    )
    payout_status = func.coalesce(models.AssetDeposit.payout_status, "pending")
    successful_purchase = and_(
        models.AssetDeposit.status == "confirmed",
        payout_status.in_(SUCCESSFUL_PAYOUT_STATUSES),
    )
    purchase_row = db.execute(
        select(
            func.count(models.AssetDeposit.id),
            func.coalesce(
                func.sum(case((models.AssetDeposit.status == "pending", 1), else_=0)),
                0,
            ),
            func.coalesce(
                func.sum(case((models.AssetDeposit.status == "confirmed", 1), else_=0)),
                0,
            ),
            func.coalesce(func.sum(case((successful_purchase, 1), else_=0)), 0),
            func.coalesce(
                func.sum(case((models.AssetDeposit.status == "failed", 1), else_=0)),
                0,
            ),
            func.coalesce(
                func.sum(
                    case(
                        (
                            and_(
                                models.AssetDeposit.status == "confirmed",
                                payout_status == "pending",
                            ),
                            1,
                        ),
                        else_=0,
                    )
                ),
                0,
            ),
            func.coalesce(
                func.sum(
                    case(
                        (
                            and_(
                                models.AssetDeposit.status == "confirmed",
                                payout_status == "failed",
                            ),
                            1,
                        ),
                        else_=0,
                    )
                ),
                0,
            ),
            func.coalesce(
                func.sum(
                    case(
                        (successful_purchase, models.AssetDeposit.amount_units),
                        else_=0,
                    )
                ),
                0,
            ),
        ).where(*purchase_conditions)
    ).one()
    purchases_created = int(purchase_row[0] or 0)
    pending_payment = int(purchase_row[1] or 0)
    payment_confirmed = int(purchase_row[2] or 0)
    purchases_successful = int(purchase_row[3] or 0)
    payment_failed = int(purchase_row[4] or 0)
    payout_pending = int(purchase_row[5] or 0)
    payout_failed = int(purchase_row[6] or 0)
    purchased_units = int(purchase_row[7] or 0)
    payment_amount_nano = _payment_amount_nano(purchased_units, decimals)

    ledger_period = _period_condition(models.AssetLedgerEntry.created_at, start)
    purchase_fee_conditions: list[object] = [
        models.AssetLedgerEntry.entry_type == "fee_purchase",
        models.AssetLedgerEntry.direction == "debit",
        *ledger_period,
    ]
    if asset:
        purchase_fee_conditions.append(models.AssetLedgerEntry.asset_id == asset.id)
    else:
        purchase_fee_conditions.append(models.AssetLedgerEntry.id < 0)
    purchase_fee_units = _count(
        db,
        select(func.coalesce(func.sum(models.AssetLedgerEntry.amount_units), 0)).where(
            *purchase_fee_conditions
        ),
    )

    reveal_conditions = _period_condition(models.UserReveal.created_at, start)
    reveal_row = db.execute(
        select(
            func.count(models.UserReveal.id),
            func.coalesce(func.sum(models.UserReveal.price_units), 0),
        ).where(*reveal_conditions)
    ).one()
    reveals_count = int(reveal_row[0] or 0)
    reveal_income_units = int(reveal_row[1] or 0)

    invited_conditions = [models.User.referred_by_user_id.is_not(None)]
    if start is not None:
        invited_conditions.append(models.User.referred_at >= start)
    invited_users = _count(
        db,
        select(func.count(models.User.id)).where(*invited_conditions),
    )

    reward_conditions = [models.ReferralReward.status == "credited"]
    if start is not None:
        reward_conditions.append(models.ReferralReward.credited_at >= start)
    reward_row = db.execute(
        select(
            func.count(models.ReferralReward.id),
            func.coalesce(func.sum(models.ReferralReward.reward_amount_tdsd), 0),
        ).where(*reward_conditions)
    ).one()
    credited_rewards = int(reward_row[0] or 0)
    credited_reward_units = int(reward_row[1] or 0)

    legacy_transactions_count = _count(
        db,
        select(func.count(models.Transaction.id)).where(
            *_period_condition(models.Transaction.created_at, start)
        ),
    )

    total_revenue_units = (
        purchase_fee_units + gift_fee_units + reveal_income_units
    )
    return schemas.AdminDashboardOverview(
        period=period,
        period_start=start,
        generated_at=generated_at,
        asset_symbol=asset.symbol if asset else TDSD_ASSET_SYMBOL,
        users=schemas.AdminDashboardUsersStats(
            total=users_total,
            new_in_period=new_users,
            active_in_period=active_users,
            active_1d=active_since(1),
            active_7d=active_since(7),
            active_30d=active_since(30),
            wallets_connected=wallets_connected,
        ),
        gifts=schemas.AdminDashboardGiftStats(
            count=gifts_count,
            gross_units=gift_gross_units,
            gross_display=_format_units(gift_gross_units, decimals),
            net_units=gift_net_units,
            net_display=_format_units(gift_net_units, decimals),
            fee_units=gift_fee_units,
            fee_display=_format_units(gift_fee_units, decimals),
            average_units=gift_average_units,
            average_display=_format_units(gift_average_units, decimals),
            unique_senders=int(gift_row[4] or 0),
            unique_receivers=int(gift_row[5] or 0),
        ),
        purchases=schemas.AdminDashboardPurchaseStats(
            created=purchases_created,
            pending_payment=pending_payment,
            payment_confirmed=payment_confirmed,
            successful=purchases_successful,
            payment_failed=payment_failed,
            payout_pending=payout_pending,
            payout_failed=payout_failed,
            purchased_units=purchased_units,
            purchased_display=_format_units(purchased_units, decimals),
            payment_amount_nano=payment_amount_nano,
            payment_amount_ton=_format_units(payment_amount_nano, 9),
        ),
        revenue=schemas.AdminDashboardRevenueStats(
            purchase_fee_units=purchase_fee_units,
            purchase_fee_display=_format_units(purchase_fee_units, decimals),
            transfer_fee_units=gift_fee_units,
            transfer_fee_display=_format_units(gift_fee_units, decimals),
            reveal_income_units=reveal_income_units,
            reveal_income_display=_format_units(reveal_income_units, decimals),
            total_units=total_revenue_units,
            total_display=_format_units(total_revenue_units, decimals),
        ),
        referrals=schemas.AdminDashboardReferralStats(
            invited_users=invited_users,
            credited_rewards=credited_rewards,
            credited_reward_units=credited_reward_units,
            credited_reward_display=_format_units(credited_reward_units, decimals),
        ),
        reveals=schemas.AdminDashboardRevealStats(
            count=reveals_count,
            income_units=reveal_income_units,
            income_display=_format_units(reveal_income_units, decimals),
        ),
        legacy_transactions_count=legacy_transactions_count,
    )


def _date_key(value: object) -> str:
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return str(value)[:10]


def build_admin_timeseries(
    db: Session,
    days: int,
    now: datetime | None = None,
) -> schemas.AdminDashboardTimeSeries:
    generated_at = now or datetime.utcnow()
    start_day = generated_at.date() - timedelta(days=days - 1)
    start = datetime.combine(start_day, datetime.min.time())
    asset = _tdsd_asset(db)
    decimals = int(asset.decimals if asset else 9)
    points = {
        (start_day + timedelta(days=offset)).isoformat(): {
            "new_users": 0,
            "gifts_count": 0,
            "gift_volume_units": 0,
            "purchases_count": 0,
            "purchase_volume_units": 0,
        }
        for offset in range(days)
    }

    user_day = func.date(models.User.created_at)
    user_rows = db.execute(
        select(user_day, func.count(models.User.id))
        .where(
            *_real_user_conditions(),
            models.User.created_at >= start,
        )
        .group_by(user_day)
    ).all()
    for day_value, count_value in user_rows:
        key = _date_key(day_value)
        if key in points:
            points[key]["new_users"] = int(count_value or 0)

    if asset:
        gift_day = func.date(models.AssetGift.created_at)
        gift_rows = db.execute(
            select(
                gift_day,
                func.count(models.AssetGift.id),
                func.coalesce(func.sum(models.AssetGift.amount_units), 0),
            )
            .where(
                models.AssetGift.asset_id == asset.id,
                models.AssetGift.status == "completed",
                models.AssetGift.created_at >= start,
            )
            .group_by(gift_day)
        ).all()
        for day_value, count_value, volume_value in gift_rows:
            key = _date_key(day_value)
            if key in points:
                points[key]["gifts_count"] = int(count_value or 0)
                points[key]["gift_volume_units"] = int(volume_value or 0)

        purchase_day = func.date(models.AssetDeposit.created_at)
        payout_status = func.coalesce(models.AssetDeposit.payout_status, "pending")
        purchase_rows = db.execute(
            select(
                purchase_day,
                func.count(models.AssetDeposit.id),
                func.coalesce(func.sum(models.AssetDeposit.amount_units), 0),
            )
            .where(
                models.AssetDeposit.asset_id == asset.id,
                models.AssetDeposit.provider == "tdsd_fixed_price",
                models.AssetDeposit.status == "confirmed",
                payout_status.in_(SUCCESSFUL_PAYOUT_STATUSES),
                models.AssetDeposit.created_at >= start,
            )
            .group_by(purchase_day)
        ).all()
        for day_value, count_value, volume_value in purchase_rows:
            key = _date_key(day_value)
            if key in points:
                points[key]["purchases_count"] = int(count_value or 0)
                points[key]["purchase_volume_units"] = int(volume_value or 0)

    return schemas.AdminDashboardTimeSeries(
        days=days,
        asset_symbol=asset.symbol if asset else TDSD_ASSET_SYMBOL,
        points=[
            schemas.AdminDashboardTimeSeriesPoint(
                date=date.fromisoformat(day_key),
                new_users=values["new_users"],
                gifts_count=values["gifts_count"],
                gift_volume_units=values["gift_volume_units"],
                gift_volume_display=_format_units(
                    values["gift_volume_units"],
                    decimals,
                ),
                purchases_count=values["purchases_count"],
                purchase_volume_units=values["purchase_volume_units"],
                purchase_volume_display=_format_units(
                    values["purchase_volume_units"],
                    decimals,
                ),
            )
            for day_key, values in points.items()
        ],
    )


def build_admin_activity(
    db: Session,
    limit: int,
) -> schemas.AdminDashboardActivity:
    asset = _tdsd_asset(db)
    gift_statement = (
        select(models.AssetGift)
        .options(
            joinedload(models.AssetGift.sender),
            joinedload(models.AssetGift.receiver),
            joinedload(models.AssetGift.asset),
        )
        .order_by(models.AssetGift.created_at.desc())
        .limit(limit)
    )
    purchase_statement = (
        select(models.AssetDeposit)
        .options(
            joinedload(models.AssetDeposit.user),
            joinedload(models.AssetDeposit.asset),
        )
        .where(models.AssetDeposit.provider == "tdsd_fixed_price")
        .order_by(models.AssetDeposit.created_at.desc())
        .limit(limit)
    )
    if asset:
        gift_statement = gift_statement.where(models.AssetGift.asset_id == asset.id)
        purchase_statement = purchase_statement.where(
            models.AssetDeposit.asset_id == asset.id
        )
    else:
        gift_statement = gift_statement.where(models.AssetGift.id < 0)
        purchase_statement = purchase_statement.where(models.AssetDeposit.id < 0)

    gifts = db.scalars(gift_statement).all()
    purchases = db.scalars(purchase_statement).all()
    gift_rows = [
        schemas.AdminDashboardGiftActivity(
            id=gift.id,
            sender=_user_label(gift.sender),
            receiver=_user_label(gift.receiver),
            amount_display=_format_units(gift.amount_units, gift.asset.decimals),
            net_amount_display=_format_units(
                gift.net_amount_units,
                gift.asset.decimals,
            ),
            fee_display=_format_units(gift.fee_units, gift.asset.decimals),
            status=gift.status,
            created_at=gift.created_at,
        )
        for gift in gifts
    ]
    purchase_rows = []
    for purchase in purchases:
        payment_nano = _payment_amount_nano(
            int(purchase.amount_units or 0),
            purchase.asset.decimals,
        )
        purchase_rows.append(
            schemas.AdminDashboardPurchaseActivity(
                id=purchase.id,
                user=_user_label(purchase.user),
                amount_display=_format_units(
                    purchase.amount_units,
                    purchase.asset.decimals,
                ),
                payment_amount_ton=_format_units(payment_nano, 9),
                status=purchase.status,
                payout_status=purchase.payout_status or "pending",
                error=purchase.payout_failed_reason or purchase.failed_reason,
                created_at=purchase.created_at,
                confirmed_at=purchase.confirmed_at,
            )
        )

    return schemas.AdminDashboardActivity(
        recent_gifts=gift_rows,
        recent_purchases=purchase_rows,
    )
