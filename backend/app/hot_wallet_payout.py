import base64
import logging
import time
from dataclasses import dataclass

from .config import (
    HOT_WALLET_ADDRESS,
    HOT_WALLET_JETTON_TRANSFER_GAS_TON,
    HOT_WALLET_MNEMONIC,
    TDSD_JETTON_MASTER_ADDRESS,
    TON_NETWORK,
)
from .fee_service import decimal_to_nano
from .ton import TonAddressValidationError, normalize_ton_wallet_address
from .ton_service import (
    TonCenterError,
    get_address_forms,
    get_wallet_information,
    run_get_method,
    send_boc,
)


logger = logging.getLogger("tuda_suda.hot_wallet_payout")

JETTON_TRANSFER_OP = 0x0F8A7EA5
FORWARD_TON_NANO = 1
PUBLIC_UNAVAILABLE_MESSAGE = "Автоматическая выплата временно недоступна"
PUBLIC_SEND_FAILED_MESSAGE = "Ошибка отправки, обратитесь в поддержку"


class HotWalletPayoutUnavailable(RuntimeError):
    pass


class HotWalletPayoutFailed(RuntimeError):
    pass


@dataclass(frozen=True)
class HotWalletPayoutResult:
    tx_hash: str
    hot_jetton_wallet_address: str
    recipient_jetton_wallet_address: str


@dataclass(frozen=True)
class _TonSdk:
    Address: object
    Cell: object
    Wallets: object
    WalletVersionEnum: object
    bytes_to_b64str: object


def _load_tonsdk() -> _TonSdk:
    try:
        from tonsdk.boc import Cell
        from tonsdk.contract.wallet import WalletVersionEnum, Wallets
        from tonsdk.utils import Address, bytes_to_b64str
    except Exception as exc:
        raise HotWalletPayoutUnavailable(PUBLIC_UNAVAILABLE_MESSAGE) from exc

    return _TonSdk(
        Address=Address,
        Cell=Cell,
        Wallets=Wallets,
        WalletVersionEnum=WalletVersionEnum,
        bytes_to_b64str=bytes_to_b64str,
    )


def _mnemonic_words() -> list[str]:
    if not HOT_WALLET_MNEMONIC:
        raise HotWalletPayoutUnavailable(PUBLIC_UNAVAILABLE_MESSAGE)

    words = HOT_WALLET_MNEMONIC.replace("\n", " ").split()
    if len(words) < 12:
        raise HotWalletPayoutUnavailable(PUBLIC_UNAVAILABLE_MESSAGE)
    return words


def _address_to_string(address: object, *, bounceable: bool = True) -> str:
    if hasattr(address, "to_string"):
        try:
            return address.to_string(
                is_user_friendly=True,
                is_url_safe=True,
                is_bounceable=bounceable,
                is_test_only=TON_NETWORK == "testnet",
            )
        except TypeError:
            return address.to_string()
    return str(address)


def _wallet_address_variants(wallet_address: object) -> set[str]:
    variants = {str(wallet_address)}
    if not hasattr(wallet_address, "to_string"):
        return variants

    for is_user_friendly in (True, False):
        for is_url_safe in (True, False):
            for is_bounceable in (True, False):
                for is_test_only in (True, False):
                    try:
                        variants.add(
                            wallet_address.to_string(
                                is_user_friendly=is_user_friendly,
                                is_url_safe=is_url_safe,
                                is_bounceable=is_bounceable,
                                is_test_only=is_test_only,
                            )
                        )
                    except TypeError:
                        continue
    return {value for value in variants if value}


def _hot_wallet_contract(sdk: _TonSdk) -> object:
    words = _mnemonic_words()
    try:
        wallet_data = sdk.Wallets.from_mnemonics(
            words,
            sdk.WalletVersionEnum.v4r2,
            workchain=0,
        )
    except TypeError:
        wallet_data = sdk.Wallets.from_mnemonics(
            words,
            sdk.WalletVersionEnum.v4r2,
            0,
        )
    except Exception as exc:
        raise HotWalletPayoutUnavailable(PUBLIC_UNAVAILABLE_MESSAGE) from exc

    wallet = wallet_data[3]
    configured_address = normalize_ton_wallet_address(HOT_WALLET_ADDRESS)
    generated_variants = _wallet_address_variants(wallet.address)
    configured_variants = get_address_forms(configured_address)
    if generated_variants.isdisjoint(configured_variants):
        logger.error("HOT_WALLET_ADDRESS does not match HOT_WALLET_MNEMONIC wallet")
        raise HotWalletPayoutUnavailable(PUBLIC_UNAVAILABLE_MESSAGE)
    return wallet


def _address_stack_cell_b64(sdk: _TonSdk, address: str) -> str:
    cell = sdk.Cell()
    cell.bits.write_address(sdk.Address(address))
    return sdk.bytes_to_b64str(cell.to_boc(False))


def _stack_item_boc_base64(item: object) -> str | None:
    if isinstance(item, dict):
        for key in ("bytes", "boc", "cell"):
            value = item.get(key)
            if isinstance(value, str):
                return value
        return None
    if isinstance(item, (list, tuple)):
        for value in item[1:]:
            extracted = _stack_item_boc_base64(value)
            if extracted:
                return extracted
    if isinstance(item, str):
        return item
    return None


def _read_address_from_boc(sdk: _TonSdk, boc_base64: str) -> str:
    try:
        cell = sdk.Cell.one_from_boc(base64.b64decode(boc_base64))
        parsed = cell.begin_parse()
        address = parsed.read_msg_addr()
    except Exception as exc:
        raise HotWalletPayoutUnavailable(PUBLIC_UNAVAILABLE_MESSAGE) from exc
    return _address_to_string(address)


def get_jetton_wallet_address(owner_wallet_address: str) -> str:
    sdk = _load_tonsdk()
    try:
        master_address = normalize_ton_wallet_address(TDSD_JETTON_MASTER_ADDRESS)
        owner_address = normalize_ton_wallet_address(owner_wallet_address)
    except TonAddressValidationError as exc:
        raise HotWalletPayoutUnavailable(PUBLIC_UNAVAILABLE_MESSAGE) from exc
    stack = [["tvm.Slice", _address_stack_cell_b64(sdk, owner_address)]]

    try:
        result = run_get_method(master_address, "get_wallet_address", stack)
    except TonCenterError as exc:
        raise HotWalletPayoutUnavailable(PUBLIC_UNAVAILABLE_MESSAGE) from exc

    result_stack = result.get("stack") if isinstance(result, dict) else None
    if not result_stack:
        raise HotWalletPayoutUnavailable(PUBLIC_UNAVAILABLE_MESSAGE)

    boc_base64 = _stack_item_boc_base64(result_stack[0])
    if not boc_base64:
        raise HotWalletPayoutUnavailable(PUBLIC_UNAVAILABLE_MESSAGE)
    return normalize_ton_wallet_address(_read_address_from_boc(sdk, boc_base64))


def _hot_wallet_seqno() -> int:
    try:
        info = get_wallet_information(HOT_WALLET_ADDRESS)
    except TonCenterError as exc:
        raise HotWalletPayoutFailed(PUBLIC_SEND_FAILED_MESSAGE) from exc

    try:
        return int(info.get("seqno") or 0)
    except (TypeError, ValueError) as exc:
        raise HotWalletPayoutFailed(PUBLIC_SEND_FAILED_MESSAGE) from exc


def _build_jetton_transfer_body(
    sdk: _TonSdk,
    recipient_wallet_address: str,
    amount_units: int,
    query_id: int,
) -> object:
    body = sdk.Cell()
    body.bits.write_uint(JETTON_TRANSFER_OP, 32)
    body.bits.write_uint(query_id, 64)
    body.bits.write_coins(int(amount_units))
    # Standard jetton transfer destination is the recipient owner wallet.
    body.bits.write_address(sdk.Address(recipient_wallet_address))
    body.bits.write_address(sdk.Address(HOT_WALLET_ADDRESS))
    body.bits.write_bit(0)
    body.bits.write_coins(FORWARD_TON_NANO)
    body.bits.write_bit(0)
    return body


def send_tdsd_from_hot_wallet(
    *,
    recipient_wallet_address: str,
    amount_units: int,
    purchase_id: int,
) -> HotWalletPayoutResult:
    amount_units = int(amount_units)
    if amount_units <= 0:
        raise HotWalletPayoutFailed(PUBLIC_SEND_FAILED_MESSAGE)

    sdk = _load_tonsdk()
    try:
        recipient_wallet = normalize_ton_wallet_address(recipient_wallet_address)
        normalize_ton_wallet_address(HOT_WALLET_ADDRESS)
    except TonAddressValidationError as exc:
        raise HotWalletPayoutUnavailable(PUBLIC_UNAVAILABLE_MESSAGE) from exc

    wallet = _hot_wallet_contract(sdk)
    hot_jetton_wallet = get_jetton_wallet_address(HOT_WALLET_ADDRESS)
    recipient_jetton_wallet = get_jetton_wallet_address(recipient_wallet)
    query_id = (int(time.time()) << 32) + int(purchase_id)
    payload = _build_jetton_transfer_body(
        sdk=sdk,
        recipient_wallet_address=recipient_wallet,
        amount_units=amount_units,
        query_id=query_id,
    )

    try:
        message = wallet.create_transfer_message(
            to_addr=hot_jetton_wallet,
            amount=decimal_to_nano(HOT_WALLET_JETTON_TRANSFER_GAS_TON),
            seqno=_hot_wallet_seqno(),
            payload=payload,
        )["message"]
        message_hash = sdk.bytes_to_b64str(message.bytes_hash())
        boc_base64 = sdk.bytes_to_b64str(message.to_boc(False))
        send_boc(boc_base64)
    except HotWalletPayoutUnavailable:
        raise
    except Exception as exc:
        raise HotWalletPayoutFailed(PUBLIC_SEND_FAILED_MESSAGE) from exc

    return HotWalletPayoutResult(
        tx_hash=message_hash,
        hot_jetton_wallet_address=hot_jetton_wallet,
        recipient_jetton_wallet_address=recipient_jetton_wallet,
    )
