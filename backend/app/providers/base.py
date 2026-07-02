from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..models import Asset, AssetDeposit, User


class ProviderError(ValueError):
    pass


@dataclass(frozen=True)
class DepositInstructions:
    target_wallet_address: str
    amount_units: int
    comment: str
    provider: str
    network: str


@dataclass(frozen=True)
class DepositVerificationResult:
    confirmed: bool = False
    tx_hash: str | None = None
    failed_reason: str | None = None
    retryable_error: str | None = None


class AssetProvider(ABC):
    provider_name: str
    asset_type: str
    network: str

    @abstractmethod
    def create_deposit_instructions(
        self,
        asset: "Asset",
        user: "User",
        amount_units: int,
    ) -> DepositInstructions:
        raise NotImplementedError

    @abstractmethod
    def verify_deposit(
        self,
        deposit: "AssetDeposit",
        user: "User",
    ) -> DepositVerificationResult:
        raise NotImplementedError

    def send_withdrawal(self, *args: object, **kwargs: object) -> None:
        # Stage 6 intentionally prepares the API shape only. Withdrawals must wait
        # for product rules, treasury accounting, and contract-level security review.
        raise NotImplementedError("Withdrawals are not implemented in the MVP")
