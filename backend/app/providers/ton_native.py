import secrets
from decimal import Decimal, ROUND_DOWN

from .. import models
from ..config import (
    MAX_DEPOSIT_TON,
    MIN_DEPOSIT_TON,
    TON_NETWORK,
    get_tdsd_payment_wallet_address,
)
from ..ton import TonAddressValidationError, normalize_ton_wallet_address
from ..ton_service import TonCenterError, verify_deposit
from .base import (
    AssetProvider,
    DepositInstructions,
    DepositVerificationResult,
    ProviderError,
)


NANO_PER_TON = 1_000_000_000


def _ton_to_nano_units(amount_ton: Decimal) -> int:
    quantized = amount_ton.quantize(Decimal("0.000000001"), rounding=ROUND_DOWN)
    return int(quantized * Decimal(NANO_PER_TON))


class _TonDepositAdapter:
    def __init__(self, deposit: models.AssetDeposit) -> None:
        self.target_wallet_address = deposit.target_wallet_address
        self.amount_nano = int(deposit.amount_units or 0)
        self.comment = deposit.comment
        self.created_at = deposit.created_at


class TonNativeProvider(AssetProvider):
    provider_name = "ton_native"
    asset_type = "native"
    network = "ton_testnet"

    def create_deposit_instructions(
        self,
        asset: models.Asset,
        user: models.User,
        amount_units: int,
    ) -> DepositInstructions:
        if asset.symbol != "TON" or asset.asset_type != self.asset_type:
            raise ProviderError("TonNativeProvider поддерживает только native TON")
        if asset.network != self.network or TON_NETWORK != "testnet":
            raise ProviderError("TON deposits в MVP разрешены только в testnet")
        payment_wallet_address = get_tdsd_payment_wallet_address()
        if not payment_wallet_address:
            raise ProviderError("Адрес приема оплаты временно не настроен")

        amount_units = int(amount_units)
        if amount_units <= 0:
            raise ProviderError("Сумма депозита должна быть больше нуля")

        min_units = _ton_to_nano_units(MIN_DEPOSIT_TON)
        max_units = _ton_to_nano_units(MAX_DEPOSIT_TON)
        if amount_units < min_units:
            raise ProviderError(f"Минимальный депозит: {MIN_DEPOSIT_TON} TON")
        if amount_units > max_units:
            raise ProviderError(f"Максимальный депозит: {MAX_DEPOSIT_TON} TON")

        try:
            target_wallet_address = normalize_ton_wallet_address(payment_wallet_address)
        except TonAddressValidationError as exc:
            raise ProviderError(str(exc)) from exc

        comment = f"asset-deposit:{user.id}:{asset.symbol}:{secrets.token_urlsafe(8)}"
        return DepositInstructions(
            target_wallet_address=target_wallet_address,
            amount_units=amount_units,
            comment=comment,
            provider=self.provider_name,
            network=self.network,
        )

    def verify_deposit(
        self,
        deposit: models.AssetDeposit,
        user: models.User,
    ) -> DepositVerificationResult:
        try:
            search_result = verify_deposit(
                _TonDepositAdapter(deposit),
                deposit.wallet_address,
            )
        except TonCenterError as exc:
            return DepositVerificationResult(
                retryable_error=f"Последняя ошибка TON Center API: {str(exc)[:430]}"
            )

        if search_result.failed_reason:
            return DepositVerificationResult(failed_reason=search_result.failed_reason)
        if not search_result.matched:
            return DepositVerificationResult()

        return DepositVerificationResult(
            confirmed=True,
            tx_hash=search_result.matched.tx_hash,
        )
