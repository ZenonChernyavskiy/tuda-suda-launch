from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class MockTelegramUser(BaseModel):
    telegram_id: str
    username: str | None = None
    first_name: str | None = None


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
            raise ValueError("Можно отправить только 1, 5, 10 или 25 монет")
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


class PublicTransactionFeedItem(BaseModel):
    id: str
    source_type: Literal["virtual_gift", "asset_gift", "fee", "referral_reward"]
    created_at: datetime
    sender: str
    receiver: str
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
    target_wallet_address: str
    comment: str
    provider: str
    network: str
    status: Literal["pending"]


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
    tx_hash: str | None
    comment: str | None
    status: Literal["pending", "confirmed", "failed"]
    provider: str
    network: str
    failed_reason: str | None = None
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
