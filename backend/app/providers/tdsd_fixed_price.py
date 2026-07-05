import secrets

from .. import models
from ..config import TDSD_ASSET_SYMBOL, TON_NETWORK, get_tdsd_payment_wallet_address
from ..fee_service import calculate_tdsd_fixed_price_quote
from ..ton import TonAddressValidationError, normalize_ton_wallet_address
from ..ton_service import TonCenterError, verify_deposit as verify_ton_payment
from .base import (
    AssetProvider,
    DepositInstructions,
    DepositVerificationResult,
    ProviderError,
)


class _TdsdTonPaymentAdapter:
    def __init__(self, deposit: models.AssetDeposit) -> None:
        quote = calculate_tdsd_fixed_price_quote(
            int(deposit.amount_units or 0),
            deposit.asset.decimals,
        )
        self.target_wallet_address = deposit.target_wallet_address
        self.amount_nano = quote.payment_amount_nano
        self.comment = deposit.comment
        self.created_at = deposit.created_at


class TdsdFixedPriceProvider(AssetProvider):
    provider_name = "tdsd_fixed_price"
    asset_type = "jetton"

    def __init__(self, network: str) -> None:
        self.network = network

    def create_deposit_instructions(
        self,
        asset: models.Asset,
        user: models.User,
        amount_units: int,
    ) -> DepositInstructions:
        if asset.symbol != TDSD_ASSET_SYMBOL:
            raise ProviderError("Покупка доступна только для TDSD")
        payment_wallet_address = get_tdsd_payment_wallet_address()
        if not payment_wallet_address:
            raise ProviderError("Покупка TDSD временно недоступна")

        try:
            calculate_tdsd_fixed_price_quote(amount_units, asset.decimals)
            target_wallet_address = normalize_ton_wallet_address(payment_wallet_address)
        except (ValueError, TonAddressValidationError) as exc:
            raise ProviderError(str(exc)) from exc

        return DepositInstructions(
            target_wallet_address=target_wallet_address,
            amount_units=int(amount_units),
            comment=f"tdsd-buy:{user.id}:{asset.symbol}:{secrets.token_urlsafe(8)}",
            provider=self.provider_name,
            network=f"ton_{TON_NETWORK}",
        )

    def verify_deposit(
        self,
        deposit: models.AssetDeposit,
        user: models.User,
    ) -> DepositVerificationResult:
        try:
            result = verify_ton_payment(
                _TdsdTonPaymentAdapter(deposit),
                user.ton_wallet_address or deposit.wallet_address,
            )
        except (ValueError, TonCenterError):
            return DepositVerificationResult(
                retryable_error="Не удалось проверить покупку TDSD. Попробуйте позже."
            )

        if result.failed_reason:
            return DepositVerificationResult(failed_reason=result.failed_reason)
        if not result.matched:
            return DepositVerificationResult()

        return DepositVerificationResult(
            confirmed=True,
            tx_hash=result.matched.tx_hash,
        )
