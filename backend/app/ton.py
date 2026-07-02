import re
from typing import Any


TON_USER_FRIENDLY_RE = re.compile(r"^(EQ|UQ|kQ)[A-Za-z0-9_-]{46}$")
TON_RAW_RE = re.compile(r"^(0|-1):[0-9a-fA-F]{64}$")


class TonAddressValidationError(ValueError):
    pass


def normalize_ton_wallet_address(address: Any) -> str:
    if not isinstance(address, str):
        raise TonAddressValidationError("TON-адрес должен быть строкой")

    normalized = address.strip()
    if not normalized:
        raise TonAddressValidationError("TON-адрес не должен быть пустым")

    if ":" in normalized:
        if not TON_RAW_RE.fullmatch(normalized):
            raise TonAddressValidationError(
                "Raw TON-адрес должен быть в формате 0:<64 hex> или -1:<64 hex>",
            )
        return normalized

    if not TON_USER_FRIENDLY_RE.fullmatch(normalized):
        raise TonAddressValidationError(
            "TON-адрес должен быть user-friendly адресом длиной 48 символов "
            "с префиксом EQ, UQ или kQ, либо raw адресом workchain:hash",
        )

    return normalized


def validate_ton_wallet_address(address: Any) -> bool:
    normalize_ton_wallet_address(address)
    return True
