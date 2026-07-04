from dataclasses import dataclass
from decimal import Decimal, ROUND_DOWN

from .config import (
    BUY_COMMISSION_PERCENT,
    TDSD_ASSET_SYMBOL,
    TDSD_FIXED_PRICE_TON,
    TRANSFER_COMMISSION_PERCENT,
)


NANO_PER_TON = 1_000_000_000


@dataclass(frozen=True)
class PurchaseFeeQuote:
    total_amount_nano: int
    fee_amount_nano: int
    treasury_amount_nano: int
    purchase_amount_nano: int
    fee_percent: Decimal
    min_fee_ton: Decimal


@dataclass(frozen=True)
class BuyCommissionQuote:
    purchased_amount_units: int
    commission_amount_units: int
    treasury_amount_units: int
    credited_amount_units: int
    commission_percent: Decimal


@dataclass(frozen=True)
class TdsdFixedPriceQuote:
    gross_amount_units: int
    payment_amount_nano: int
    fixed_price_ton: Decimal


@dataclass(frozen=True)
class TransferFeeQuote:
    asset_symbol: str
    total_amount_units: int
    fee_amount_units: int
    treasury_amount_units: int
    recipient_amount_units: int
    fee_percent: Decimal


def decimal_to_nano(amount_ton: Decimal) -> int:
    quantized = amount_ton.quantize(Decimal("0.000000001"), rounding=ROUND_DOWN)
    return int(quantized * Decimal(NANO_PER_TON))


def decimal_percent_fee(amount_units: int, percent: Decimal) -> int:
    amount = Decimal(int(amount_units))
    fee = amount * percent / Decimal("100")
    return int(fee.to_integral_value(rounding=ROUND_DOWN))


def decimal_label(value: Decimal) -> str:
    return format(value.normalize(), "f").rstrip("0").rstrip(".") or "0"


def calculate_purchase_fee(amount_ton: Decimal) -> PurchaseFeeQuote:
    total_amount_nano = decimal_to_nano(amount_ton)
    if total_amount_nano <= 0:
        raise ValueError("Сумма покупки должна быть больше нуля")

    fee_amount_nano = decimal_percent_fee(total_amount_nano, BUY_COMMISSION_PERCENT)
    purchase_amount_nano = total_amount_nano - fee_amount_nano
    if purchase_amount_nano <= 0:
        raise ValueError("Сумма покупки должна быть больше комиссии сервиса")

    return PurchaseFeeQuote(
        total_amount_nano=total_amount_nano,
        fee_amount_nano=fee_amount_nano,
        treasury_amount_nano=fee_amount_nano,
        purchase_amount_nano=purchase_amount_nano,
        fee_percent=BUY_COMMISSION_PERCENT,
        min_fee_ton=Decimal("0"),
    )


def calculate_buy_commission(amount_units: int) -> BuyCommissionQuote:
    purchased_amount_units = int(amount_units)
    if purchased_amount_units <= 0:
        raise ValueError("Сумма покупки должна быть больше нуля")

    commission_amount_units = decimal_percent_fee(
        purchased_amount_units,
        BUY_COMMISSION_PERCENT,
    )
    credited_amount_units = purchased_amount_units - commission_amount_units
    if credited_amount_units <= 0:
        raise ValueError("Сумма покупки должна быть больше комиссии сервиса")

    return BuyCommissionQuote(
        purchased_amount_units=purchased_amount_units,
        commission_amount_units=commission_amount_units,
        treasury_amount_units=commission_amount_units,
        credited_amount_units=credited_amount_units,
        commission_percent=BUY_COMMISSION_PERCENT,
    )


def calculate_tdsd_fixed_price_quote(
    amount_units: int,
    decimals: int,
) -> TdsdFixedPriceQuote:
    gross_amount_units = int(amount_units)
    if gross_amount_units <= 0:
        raise ValueError("Сумма покупки TDSD должна быть больше нуля")
    if decimals < 0:
        raise ValueError("Некорректная точность TDSD")

    scale = Decimal(10) ** int(decimals)
    amount_tdsd = Decimal(gross_amount_units) / scale
    payment_ton = amount_tdsd * TDSD_FIXED_PRICE_TON
    payment_amount_nano = decimal_to_nano(payment_ton)
    if payment_amount_nano <= 0:
        raise ValueError("Сумма покупки TDSD слишком мала")

    return TdsdFixedPriceQuote(
        gross_amount_units=gross_amount_units,
        payment_amount_nano=payment_amount_nano,
        fixed_price_ton=TDSD_FIXED_PRICE_TON,
    )


def calculate_transfer_fee(
    asset_symbol: str,
    amount_units: int,
) -> TransferFeeQuote:
    symbol = asset_symbol.strip().upper()
    total_amount_units = int(amount_units)
    if total_amount_units <= 0:
        raise ValueError("Сумма перевода должна быть больше нуля")

    fee_percent = TRANSFER_COMMISSION_PERCENT if symbol == TDSD_ASSET_SYMBOL else Decimal("0")
    fee_amount_units = decimal_percent_fee(total_amount_units, fee_percent)
    recipient_amount_units = total_amount_units - fee_amount_units
    if recipient_amount_units <= 0:
        raise ValueError("Сумма перевода должна быть больше комиссии сервиса")

    return TransferFeeQuote(
        asset_symbol=symbol,
        total_amount_units=total_amount_units,
        fee_amount_units=fee_amount_units,
        treasury_amount_units=fee_amount_units,
        recipient_amount_units=recipient_amount_units,
        fee_percent=fee_percent,
    )
