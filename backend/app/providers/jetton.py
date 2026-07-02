import secrets

from .. import models
from ..config import (
    TDSD_DEPOSITS_ENABLED,
    TDSD_JETTON_MASTER_ADDRESS,
    TDSD_NETWORK,
    TDSD_PROJECT_JETTON_WALLET,
)
from ..ton import TonAddressValidationError, normalize_ton_wallet_address
from ..ton_service import TonCenterError, verify_jetton_deposit
from .base import (
    AssetProvider,
    DepositInstructions,
    DepositVerificationResult,
    ProviderError,
)


class JettonProvider(AssetProvider):
    provider_name = "jetton"
    asset_type = "jetton"

    def __init__(self, network: str) -> None:
        self.network = network

    def create_deposit_instructions(
        self,
        asset: models.Asset,
        user: models.User,
        amount_units: int,
    ) -> DepositInstructions:
        if not TDSD_DEPOSITS_ENABLED:
            raise ProviderError("Jetton deposits are disabled until TDSD contract deployment is verified")
        if asset.network != TDSD_NETWORK:
            raise ProviderError("Jetton provider network does not match configured TDSD_NETWORK")
        if not asset.contract_address or asset.contract_address != TDSD_JETTON_MASTER_ADDRESS:
            raise ProviderError("TDSD Jetton Master address is not configured for this asset")
        if not TDSD_PROJECT_JETTON_WALLET:
            raise ProviderError("TDSD_PROJECT_JETTON_WALLET is not configured")
        amount_units = int(amount_units)
        if amount_units <= 0:
            raise ProviderError("Сумма Jetton deposit должна быть больше нуля")

        try:
            target_wallet_address = normalize_ton_wallet_address(TDSD_PROJECT_JETTON_WALLET)
        except TonAddressValidationError as exc:
            raise ProviderError(str(exc)) from exc

        return DepositInstructions(
            target_wallet_address=target_wallet_address,
            amount_units=amount_units,
            comment=f"tdsd-deposit:{user.id}:{asset.symbol}:{secrets.token_urlsafe(8)}",
            provider=self.provider_name,
            network=self.network,
        )

    def verify_deposit(
        self,
        deposit: models.AssetDeposit,
        user: models.User,
    ) -> DepositVerificationResult:
        if not TDSD_DEPOSITS_ENABLED:
            raise ProviderError("Jetton deposits are disabled until TDSD contract deployment is verified")
        try:
            result = verify_jetton_deposit(
                deposit,
                user.ton_wallet_address or deposit.wallet_address,
                TDSD_PROJECT_JETTON_WALLET,
            )
        except TonCenterError as exc:
            return DepositVerificationResult(
                retryable_error=f"Последняя ошибка TON Center API: {str(exc)[:430]}"
            )

        if result.failed_reason:
            return DepositVerificationResult(failed_reason=result.failed_reason)
        if not result.matched:
            return DepositVerificationResult()
        return DepositVerificationResult(
            confirmed=True,
            tx_hash=result.matched.tx_hash,
        )
