from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class MockTelegramUser(BaseModel):
    telegram_id: str
    username: str | None = None
    first_name: str | None = None
    photo_url: str | None = None


class TelegramAuthRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    init_data: str | None = Field(default=None, alias="initData")
    mock: bool = False
    mock_user: MockTelegramUser | None = None
    referral_param: str | None = Field(default=None, alias="referralParam", max_length=64)
    start_param: str | None = Field(default=None, alias="startParam", max_length=64)


class UserPublic(BaseModel):
    id: int
    telegram_id: str
    username: str | None
    first_name: str | None
    photo_url: str | None = None
    balance: int
    karma: int
    reputation: int
    community_weight: int
    total_sent: int
    total_received: int
    ton_balance_nano: int
    ton_balance: float
    ton_wallet_address: str | None
    ton_wallet_connected_at: datetime | None
    referral_code: str | None = None
    referred_by_user_id: int | None = None
    referred_at: datetime | None = None
    rank: str
    created_at: datetime
    last_active_at: datetime | None


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserPublic


class GiftSendRequest(BaseModel):
    amount: int = Field(ge=1)
    message: str | None = Field(default=None, max_length=500)

    @field_validator("amount")
    @classmethod
    def amount_must_be_allowed(cls, value: int) -> int:
        if value not in {1, 5, 10, 25}:
            raise ValueError("Можно отправить только 1, 5, 10 или 25 TDSD")
        return value

    @field_validator("message")
    @classmethod
    def clean_message(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class TransactionPublic(BaseModel):
    id: int
    amount: int
    message: str | None
    created_at: datetime
    type: Literal["sent", "received"]


class UserRevealTargetPublic(BaseModel):
    context_type: str
    context_id: str
    target_role: str
    price_units: int
    price_display: str
    label: str = "Раскрыть пользователя"


class UserRevealRequest(BaseModel):
    context_type: str = Field(min_length=1, max_length=64)
    context_id: str = Field(min_length=1, max_length=64)
    target_role: str = Field(min_length=1, max_length=32)


class PublicTransactionFeedItem(BaseModel):
    id: str
    source_type: Literal["virtual_gift", "asset_gift", "fee", "referral_reward"]
    created_at: datetime
    sender: str
    receiver: str
    sender_revealed: bool = False
    receiver_revealed: bool = False
    sender_reveal: UserRevealTargetPublic | None = None
    receiver_reveal: UserRevealTargetPublic | None = None
    token: str
    amount: str
    direction: str
    comment: str | None = None


class UserDashboard(BaseModel):
    user: UserPublic
    last_transactions: list[TransactionPublic]


class GiftSendResponse(BaseModel):
    message: str
    user: UserPublic
    transaction: TransactionPublic


class LeaderboardUser(BaseModel):
    id: int
    username: str | None
    first_name: str | None
    reveal_target: UserRevealTargetPublic | None = None
    karma: int
    total_sent: int
    total_received: int
    rank: str


class LeaderboardResponse(BaseModel):
    karma: list[LeaderboardUser]
    senders: list[LeaderboardUser]
    receivers: list[LeaderboardUser]


class HealthResponse(BaseModel):
    status: str
    database: str


class WalletConnectRequest(BaseModel):
    wallet_address: Any


class WalletResponse(BaseModel):
    wallet_address: str | None
    connected_at: datetime | None


class FeeConfigPublic(BaseModel):
    buy_commission_percent: str
    buy_fee_percent: str
    tdsd_fixed_price_ton: str
    tdsd_per_ton: str
    transfer_commission_percent: str
    purchase_fee_percent: str
    purchase_min_fee_ton: str
    transfer_fee_percent: str
    transfer_fee_asset_symbol: str
    payment_address: str
    project_ton_wallet_address: str | None = None
    treasury_wallet_address: str
    hot_wallet_address: str
    tdsd_jetton_master_address: str


class PurchaseFeeQuoteRequest(BaseModel):
    amount_ton: Decimal = Field(gt=0)


class PurchaseFeeQuoteResponse(BaseModel):
    total_amount_nano: int
    total_amount_ton: str
    fee_amount_nano: int
    fee_amount_ton: str
    treasury_amount_nano: int
    treasury_amount_ton: str
    purchase_amount_nano: int
    purchase_amount_ton: str
    fee_percent: str
    min_fee_ton: str


class TransferFeeQuoteRequest(BaseModel):
    asset_symbol: str = Field(min_length=1, max_length=32)
    amount_units: int = Field(gt=0)

    @field_validator("asset_symbol")
    @classmethod
    def clean_asset_symbol(cls, value: str) -> str:
        return value.strip().upper()


class TransferFeeQuoteResponse(BaseModel):
    asset_symbol: str
    total_amount_units: int
    total_amount_display: str
    fee_amount_units: int
    fee_amount_display: str
    treasury_amount_units: int
    treasury_amount_display: str
    recipient_amount_units: int
    recipient_amount_display: str
    fee_percent: str


class TonDepositCreateMockRequest(BaseModel):
    amount_ton: Decimal = Field(gt=0)
    tx_hash: str = Field(min_length=8, max_length=128)
    status: Literal["pending", "confirmed"] = "pending"
    wallet_address: Any | None = None

    @field_validator("tx_hash")
    @classmethod
    def clean_tx_hash(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("tx_hash не должен быть пустым")
        return value


class TonDepositPublic(BaseModel):
    id: int
    wallet_address: str
    target_wallet_address: str | None = None
    network: str = "testnet"
    amount_ton: float
    amount_nano: int | None = None
    tx_hash: str | None
    comment: str | None = None
    status: Literal["pending", "confirmed", "failed"]
    failed_reason: str | None = None
    created_at: datetime
    confirmed_at: datetime | None


class TonDepositCreateRequest(BaseModel):
    amount_ton: Decimal = Field(gt=0)


class TonDepositCreateResponse(BaseModel):
    deposit_id: int
    amount_ton: float
    amount_nano: int
    target_wallet_address: str
    comment: str
    status: Literal["pending"]
    network: str


class TonDepositVerifyResponse(BaseModel):
    deposit: TonDepositPublic
    ton_balance_nano: int
    ton_balance: float
    message: str


class TonBalanceResponse(BaseModel):
    ton_balance_nano: int
    ton_balance: float


class AssetDepositCreateRequest(BaseModel):
    asset_symbol: str = Field(min_length=1, max_length=32)
    amount_units: int = Field(gt=0)

    @field_validator("asset_symbol")
    @classmethod
    def clean_asset_symbol(cls, value: str) -> str:
        return value.strip().upper()


class AssetDepositCreateResponse(BaseModel):
    deposit_id: int
    asset_id: int
    asset_symbol: str
    symbol: str
    asset_name: str
    amount_units: int
    amount_display: str
    payment_amount_nano: int | None = None
    payment_amount_ton: str | None = None
    fixed_price_ton: str | None = None
    payment_address: str
    target_wallet_address: str
    comment: str
    provider: str
    network: str
    status: Literal["pending"]
    payout_status: Literal["pending", "sent", "confirmed", "failed"] = "pending"
    payout_tx_hash: str | None = None
    payout_failed_reason: str | None = None
    payout_sent_at: datetime | None = None
    payout_confirmed_at: datetime | None = None


class AssetDepositPublic(BaseModel):
    id: int
    asset_id: int
    symbol: str
    asset_name: str
    wallet_address: str
    target_wallet_address: str
    amount_units: int
    amount_display: str
    payment_amount_nano: int | None = None
    payment_amount_ton: str | None = None
    fixed_price_ton: str | None = None
    payment_address: str
    tx_hash: str | None
    comment: str | None
    status: Literal["pending", "confirmed", "failed"]
    provider: str
    network: str
    failed_reason: str | None = None
    payout_status: Literal["pending", "sent", "confirmed", "failed"] = "pending"
    payout_tx_hash: str | None = None
    payout_failed_reason: str | None = None
    payout_sent_at: datetime | None = None
    payout_confirmed_at: datetime | None = None
    created_at: datetime
    confirmed_at: datetime | None


class AssetPublic(BaseModel):
    id: int
    symbol: str
    name: str
    asset_type: Literal["native", "jetton", "internal"]
    network: str
    decimals: int
    contract_address: str | None
    provider_key: str | None
    metadata_json: Any | None = None
    display_order: int
    is_active: bool
    created_at: datetime


class AssetCreateRequest(BaseModel):
    symbol: str = Field(min_length=1, max_length=32)
    name: str = Field(min_length=1, max_length=128)
    asset_type: Literal["native", "jetton", "internal"]
    network: str = Field(min_length=1, max_length=32)
    decimals: int = Field(ge=0, le=18)
    contract_address: str | None = Field(default=None, max_length=128)
    provider_key: str | None = Field(default=None, max_length=64)
    metadata_json: Any | None = None
    display_order: int = 0
    is_active: bool = False

    @field_validator("symbol")
    @classmethod
    def clean_symbol(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("name", "network")
    @classmethod
    def clean_required_strings(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Поле не должно быть пустым")
        return value

    @field_validator("contract_address", "provider_key")
    @classmethod
    def clean_optional_strings(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class AssetBalancePublic(BaseModel):
    asset_id: int
    symbol: str
    name: str
    asset_type: Literal["native", "jetton", "internal"]
    network: str
    decimals: int
    contract_address: str | None
    balance_units: int
    balance_display: str


class UserRevealResponse(BaseModel):
    display_name: str
    revealed_user_id: int
    context_type: str
    context_id: str
    target_role: str
    price_units: int
    price_display: str
    charged: bool
    balance: AssetBalancePublic


class AssetDepositVerifyResponse(BaseModel):
    deposit: AssetDepositPublic
    asset_balance: AssetBalancePublic | None = None
    message: str


class AssetLedgerEntryPublic(BaseModel):
    id: int
    asset_id: int
    symbol: str
    name: str
    decimals: int
    entry_type: Literal[
        "deposit",
        "gift_sent",
        "gift_received",
        "adjustment",
        "fee",
        "fee_purchase",
        "fee_transfer",
        "treasury_income",
        "referral_reward",
        "referral_reward_pending",
        "referral_reward_credit",
        "user_reveal",
    ]
    amount_units: int
    amount_display: str
    direction: Literal["credit", "debit"]
    related_entity_type: str | None
    related_entity_id: int | None
    balance_after_units: int
    balance_after_display: str
    created_at: datetime
    comment: str | None


class AdminLedgerEntryPublic(BaseModel):
    id: int
    user_id: int
    username: str | None
    telegram_id: str
    asset_id: int
    asset_symbol: str
    asset_name: str
    entry_type: str
    direction: str
    amount_units: int
    amount_display: str
    balance_after_units: int
    balance_after_display: str
    related_entity_type: str | None
    related_entity_id: int | None
    comment: str | None
    created_at: datetime


class AdminUserPublic(BaseModel):
    id: int
    telegram_id: str
    username: str | None
    first_name: str | None
    balance: int
    karma: int
    reputation: int
    risk_score: int
    community_weight: int
    total_sent: int
    total_received: int
    ton_wallet_address: str | None
    created_at: datetime
    last_active_at: datetime | None


class AdminTransactionPublic(BaseModel):
    id: int
    sender_id: int
    receiver_id: int
    amount: int
    message: str | None
    created_at: datetime


class ReputationEventPublic(BaseModel):
    id: int
    user_id: int
    username: str | None
    event_type: str
    karma_delta: int
    reputation_delta: int
    risk_delta: int
    related_entity_type: str | None
    related_entity_id: int | None
    comment: str | None
    created_at: datetime


class AdminStatsPublic(BaseModel):
    users_count: int
    active_assets_count: int
    asset_gifts_count: int
    ledger_entries_count: int
    virtual_transactions_count: int
    deposits_count: int


class AdminDashboardUsersStats(BaseModel):
    total: int
    new_in_period: int
    active_in_period: int
    active_1d: int
    active_7d: int
    active_30d: int
    wallets_connected: int


class AdminDashboardGiftStats(BaseModel):
    count: int
    gross_units: int
    gross_display: str
    net_units: int
    net_display: str
    fee_units: int
    fee_display: str
    average_units: int
    average_display: str
    unique_senders: int
    unique_receivers: int


class AdminDashboardPurchaseStats(BaseModel):
    created: int
    pending_payment: int
    payment_confirmed: int
    successful: int
    payment_failed: int
    payout_pending: int
    payout_failed: int
    purchased_units: int
    purchased_display: str
    payment_amount_nano: int
    payment_amount_ton: str


class AdminDashboardRevenueStats(BaseModel):
    purchase_fee_units: int
    purchase_fee_display: str
    transfer_fee_units: int
    transfer_fee_display: str
    reveal_income_units: int
    reveal_income_display: str
    total_units: int
    total_display: str


class AdminDashboardReferralStats(BaseModel):
    invited_users: int
    credited_rewards: int
    credited_reward_units: int
    credited_reward_display: str


class AdminDashboardRevealStats(BaseModel):
    count: int
    income_units: int
    income_display: str


class AdminDashboardOverview(BaseModel):
    period: Literal["today", "7d", "30d", "all"]
    period_start: datetime | None
    generated_at: datetime
    asset_symbol: str
    users: AdminDashboardUsersStats
    gifts: AdminDashboardGiftStats
    purchases: AdminDashboardPurchaseStats
    revenue: AdminDashboardRevenueStats
    referrals: AdminDashboardReferralStats
    reveals: AdminDashboardRevealStats
    legacy_transactions_count: int


class AdminDashboardTimeSeriesPoint(BaseModel):
    date: date
    new_users: int
    gifts_count: int
    gift_volume_units: int
    gift_volume_display: str
    purchases_count: int
    purchase_volume_units: int
    purchase_volume_display: str


class AdminDashboardTimeSeries(BaseModel):
    days: int
    asset_symbol: str
    points: list[AdminDashboardTimeSeriesPoint]


class AdminDashboardGiftActivity(BaseModel):
    id: int
    sender: str
    receiver: str
    amount_display: str
    net_amount_display: str
    fee_display: str
    status: str
    created_at: datetime


class AdminDashboardPurchaseActivity(BaseModel):
    id: int
    user: str
    amount_display: str
    payment_amount_ton: str
    status: str
    payout_status: str
    error: str | None
    created_at: datetime
    confirmed_at: datetime | None


class AdminDashboardActivity(BaseModel):
    recent_gifts: list[AdminDashboardGiftActivity]
    recent_purchases: list[AdminDashboardPurchaseActivity]


class AssetGiftSendRequest(BaseModel):
    asset_symbol: str | None = Field(default=None, max_length=32)
    symbol: str | None = Field(default=None, max_length=32)
    amount_units: int = Field(gt=0)
    message: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def has_symbol(self) -> "AssetGiftSendRequest":
        if not (self.asset_symbol or self.symbol):
            raise ValueError("Передайте asset_symbol или symbol")
        return self

    @field_validator("asset_symbol", "symbol")
    @classmethod
    def clean_symbol(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip().upper()
        return value or None

    @field_validator("message")
    @classmethod
    def clean_message(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class AssetGiftPublic(BaseModel):
    id: int
    type: Literal["sent", "received"]
    symbol: str
    asset_name: str
    amount_units: int
    amount_display: str
    fee_units: int
    fee_display: str
    net_amount_units: int
    net_amount_display: str
    message: str | None
    status: Literal["completed", "failed", "cancelled"]
    counterparty_display_name: str
    counterparty_revealed: bool = False
    reveal_target: UserRevealTargetPublic | None = None
    created_at: datetime


class AssetGiftSendResponse(BaseModel):
    message: str
    gift: AssetGiftPublic
    sender_balance: AssetBalancePublic


class AssetGiftFeedItem(BaseModel):
    id: int
    symbol: str
    asset_name: str
    amount_units: int
    amount_display: str
    text: str
    created_at: datetime


class AssetGiftLeaderboardUser(BaseModel):
    id: int
    username: str | None
    first_name: str | None
    reveal_target: UserRevealTargetPublic | None = None
    amount_units: int
    amount_display: str


class AssetGiftLeaderboardResponse(BaseModel):
    symbol: str
    asset_name: str
    senders: list[AssetGiftLeaderboardUser]
    receivers: list[AssetGiftLeaderboardUser]


class ReferralInvitedUserPublic(BaseModel):
    user_id: int
    display_name: str
    username: str | None
    invited_at: datetime | None
    total_purchases_tdsd: int
    total_purchases_display: str
    total_reward_tdsd: int
    total_reward_display: str
    status: str


class ReferralRewardPublic(BaseModel):
    id: int
    referred_user_display_name: str
    purchase_amount_tdsd: int
    purchase_amount_display: str
    reward_amount_tdsd: int
    reward_amount_display: str
    reward_percent: str
    status: Literal["pending", "credited", "failed", "cancelled"]
    created_at: datetime
    credited_at: datetime | None


class ReferralDashboardResponse(BaseModel):
    referral_code: str
    referral_link: str
    referrals_enabled: bool
    reward_percent: str
    reward_asset_symbol: str
    invited_count: int
    total_reward_tdsd: int
    total_reward_display: str
    pending_reward_tdsd: int
    pending_reward_display: str
    invited_users: list[ReferralInvitedUserPublic]
    rewards: list[ReferralRewardPublic]
