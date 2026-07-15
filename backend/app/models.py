from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def utcnow() -> datetime:
    return datetime.utcnow()


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    telegram_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    photo_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    balance: Mapped[int] = mapped_column(Integer, default=100)
    karma: Mapped[int] = mapped_column(Integer, default=0)
    reputation: Mapped[int] = mapped_column(Integer, default=0, index=True)
    risk_score: Mapped[int] = mapped_column(Integer, default=0, index=True)
    community_weight: Mapped[int] = mapped_column(Integer, default=0, index=True)
    total_sent: Mapped[int] = mapped_column(Integer, default=0)
    total_received: Mapped[int] = mapped_column(Integer, default=0)
    # Legacy decimal field is kept for old local databases; blockchain math uses nanotons.
    ton_balance: Mapped[float] = mapped_column(Numeric(18, 9), default=0)
    ton_balance_nano: Mapped[int] = mapped_column(BigInteger, default=0)
    ton_wallet_address: Mapped[str | None] = mapped_column(String(128), nullable=True)
    ton_wallet_connected_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )
    referral_code: Mapped[str | None] = mapped_column(
        String(16),
        unique=True,
        index=True,
        nullable=True,
    )
    referred_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"),
        index=True,
        nullable=True,
    )
    referred_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    last_active_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
        index=True,
    )

    sent_transactions: Mapped[list["Transaction"]] = relationship(
        "Transaction",
        back_populates="sender",
        foreign_keys="Transaction.sender_id",
    )
    received_transactions: Mapped[list["Transaction"]] = relationship(
        "Transaction",
        back_populates="receiver",
        foreign_keys="Transaction.receiver_id",
    )
    ton_deposits: Mapped[list["TonDeposit"]] = relationship(
        "TonDeposit",
        back_populates="user",
    )
    asset_deposits: Mapped[list["AssetDeposit"]] = relationship(
        "AssetDeposit",
        back_populates="user",
    )
    asset_balances: Mapped[list["AssetBalance"]] = relationship(
        "AssetBalance",
        back_populates="user",
    )
    asset_ledger_entries: Mapped[list["AssetLedgerEntry"]] = relationship(
        "AssetLedgerEntry",
        back_populates="user",
    )
    sent_asset_gifts: Mapped[list["AssetGift"]] = relationship(
        "AssetGift",
        back_populates="sender",
        foreign_keys="AssetGift.sender_id",
    )
    received_asset_gifts: Mapped[list["AssetGift"]] = relationship(
        "AssetGift",
        back_populates="receiver",
        foreign_keys="AssetGift.receiver_id",
    )
    wallet_connections: Mapped[list["WalletConnection"]] = relationship(
        "WalletConnection",
        back_populates="user",
    )
    reputation_events: Mapped[list["ReputationEvent"]] = relationship(
        "ReputationEvent",
        back_populates="user",
    )
    referral_rewards: Mapped[list["ReferralReward"]] = relationship(
        "ReferralReward",
        back_populates="referrer",
        foreign_keys="ReferralReward.referrer_user_id",
    )
    referral_purchase_rewards: Mapped[list["ReferralReward"]] = relationship(
        "ReferralReward",
        back_populates="referred_user",
        foreign_keys="ReferralReward.referred_user_id",
    )


class WalletConnection(Base):
    __tablename__ = "wallet_connections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    network: Mapped[str] = mapped_column(String(32), default="ton", index=True)
    wallet_address: Mapped[str] = mapped_column(String(128), index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    connected_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    disconnected_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    user: Mapped[User] = relationship("User", back_populates="wallet_connections")


class ReputationEvent(Base):
    __tablename__ = "reputation_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    event_type: Mapped[str] = mapped_column(String(64), index=True)
    karma_delta: Mapped[int] = mapped_column(Integer, default=0)
    reputation_delta: Mapped[int] = mapped_column(Integer, default=0)
    risk_delta: Mapped[int] = mapped_column(Integer, default=0)
    related_entity_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    related_entity_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    comment: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)

    user: Mapped[User] = relationship("User", back_populates="reputation_events")


class Asset(Base):
    __tablename__ = "assets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    symbol: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(128))
    asset_type: Mapped[str] = mapped_column(String(32), index=True)
    network: Mapped[str] = mapped_column(String(32), index=True)
    decimals: Mapped[int] = mapped_column(Integer, default=0)
    contract_address: Mapped[str | None] = mapped_column(String(128), nullable=True)
    provider_key: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    display_order: Mapped[int] = mapped_column(Integer, default=0, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    balances: Mapped[list["AssetBalance"]] = relationship(
        "AssetBalance",
        back_populates="asset",
    )
    ledger_entries: Mapped[list["AssetLedgerEntry"]] = relationship(
        "AssetLedgerEntry",
        back_populates="asset",
    )
    deposits: Mapped[list["AssetDeposit"]] = relationship(
        "AssetDeposit",
        back_populates="asset",
    )


class AssetBalance(Base):
    __tablename__ = "asset_balances"
    __table_args__ = (
        UniqueConstraint("user_id", "asset_id", name="uq_asset_balance_user_asset"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"), index=True)
    balance_units: Mapped[int] = mapped_column(BigInteger, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utcnow,
        onupdate=utcnow,
    )

    user: Mapped[User] = relationship("User", back_populates="asset_balances")
    asset: Mapped[Asset] = relationship("Asset", back_populates="balances")


class AssetLedgerEntry(Base):
    __tablename__ = "asset_ledger_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"), index=True)
    entry_type: Mapped[str] = mapped_column(String(32), index=True)
    amount_units: Mapped[int] = mapped_column(BigInteger)
    direction: Mapped[str] = mapped_column(String(16), index=True)
    related_entity_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    related_entity_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    balance_after_units: Mapped[int] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    comment: Mapped[str | None] = mapped_column(String(500), nullable=True)

    user: Mapped[User] = relationship("User", back_populates="asset_ledger_entries")
    asset: Mapped[Asset] = relationship("Asset", back_populates="ledger_entries")


class AssetGift(Base):
    __tablename__ = "asset_gifts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    sender_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    receiver_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"), index=True)
    amount_units: Mapped[int] = mapped_column(BigInteger)
    fee_units: Mapped[int] = mapped_column(BigInteger, default=0)
    net_amount_units: Mapped[int] = mapped_column(BigInteger)
    message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="completed", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)

    sender: Mapped[User] = relationship(
        "User",
        back_populates="sent_asset_gifts",
        foreign_keys=[sender_id],
    )
    receiver: Mapped[User] = relationship(
        "User",
        back_populates="received_asset_gifts",
        foreign_keys=[receiver_id],
    )
    asset: Mapped[Asset] = relationship("Asset")


class AssetDeposit(Base):
    __tablename__ = "asset_deposits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"), index=True)
    wallet_address: Mapped[str] = mapped_column(String(128), index=True)
    target_wallet_address: Mapped[str] = mapped_column(String(128), index=True)
    amount_units: Mapped[int] = mapped_column(BigInteger)
    tx_hash: Mapped[str | None] = mapped_column(String(128), unique=True, index=True)
    comment: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    provider: Mapped[str] = mapped_column(String(64), index=True)
    network: Mapped[str] = mapped_column(String(32), index=True)
    failed_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    payout_status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    payout_tx_hash: Mapped[str | None] = mapped_column(String(128), unique=True, index=True)
    payout_failed_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    payout_sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    payout_confirmed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    user: Mapped[User] = relationship("User", back_populates="asset_deposits")
    asset: Mapped[Asset] = relationship("Asset", back_populates="deposits")


class ReferralReward(Base):
    __tablename__ = "referral_rewards"
    __table_args__ = (
        UniqueConstraint("purchase_id", name="uq_referral_reward_purchase_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    referrer_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    referred_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    purchase_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    purchase_amount_tdsd: Mapped[int] = mapped_column(BigInteger)
    reward_amount_tdsd: Mapped[int] = mapped_column(BigInteger)
    reward_percent: Mapped[float] = mapped_column(Numeric(8, 4), default=0)
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    credited_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    referrer: Mapped[User] = relationship(
        "User",
        back_populates="referral_rewards",
        foreign_keys=[referrer_user_id],
    )
    referred_user: Mapped[User] = relationship(
        "User",
        back_populates="referral_purchase_rewards",
        foreign_keys=[referred_user_id],
    )


class UserReveal(Base):
    __tablename__ = "user_reveals"
    __table_args__ = (
        UniqueConstraint(
            "viewer_user_id",
            "context_type",
            "context_id",
            "target_role",
            name="uq_user_reveal_viewer_context_target",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    viewer_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    revealed_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    context_type: Mapped[str] = mapped_column(String(64), index=True)
    context_id: Mapped[str] = mapped_column(String(64), index=True)
    target_role: Mapped[str] = mapped_column(String(32), index=True)
    price_units: Mapped[int] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)

    viewer: Mapped[User] = relationship("User", foreign_keys=[viewer_user_id])
    revealed_user: Mapped[User] = relationship("User", foreign_keys=[revealed_user_id])


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    sender_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    receiver_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    amount: Mapped[int] = mapped_column(Integer)
    message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)

    sender: Mapped[User] = relationship(
        "User",
        back_populates="sent_transactions",
        foreign_keys=[sender_id],
    )
    receiver: Mapped[User] = relationship(
        "User",
        back_populates="received_transactions",
        foreign_keys=[receiver_id],
    )


class TonDeposit(Base):
    __tablename__ = "ton_deposits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    wallet_address: Mapped[str] = mapped_column(String(128), index=True)
    target_wallet_address: Mapped[str] = mapped_column(String(128), index=True)
    network: Mapped[str] = mapped_column(String(32), default="testnet", index=True)
    amount_ton: Mapped[float] = mapped_column(Numeric(18, 9))
    amount_nano: Mapped[int] = mapped_column(BigInteger)
    tx_hash: Mapped[str | None] = mapped_column(String(128), unique=True, index=True)
    comment: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    failed_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    user: Mapped[User] = relationship("User", back_populates="ton_deposits")
