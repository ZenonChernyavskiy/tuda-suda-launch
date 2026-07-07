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
    logger.info("Loading tonsdk for TDSD hot wallet payout")
    try:
        from tonsdk.boc import Cell
        from tonsdk.contract.wallet import WalletVersionEnum, Wallets
        from tonsdk.utils import Address, bytes_to_b64str
    except Exception as exc:
        logger.exception(
            "Failed to load tonsdk for TDSD hot wallet payout "
            "exception_type=%s exception=%s",
            type(exc).__name__,
            str(exc),
        )
        raise HotWalletPayoutUnavailable(PUBLIC_UNAVAILABLE_MESSAGE) from exc

    logger.info("tonsdk loaded for TDSD hot wallet payout")
    return _TonSdk(
        Address=Address,
        Cell=Cell,
        Wallets=Wallets,
        WalletVersionEnum=WalletVersionEnum,
        bytes_to_b64str=bytes_to_b64str,
    )


def _mnemonic_words() -> list[str]:
    logger.info(
        "Checking HOT_WALLET_MNEMONIC presence for TDSD hot wallet payout "
        "hot_wallet_address=%s",
        HOT_WALLET_ADDRESS,
    )
    if not HOT_WALLET_MNEMONIC:
        logger.error(
            "HOT_WALLET_MNEMONIC is not configured for TDSD hot wallet payout "
            "hot_wallet_address=%s",
            HOT_WALLET_ADDRESS,
        )
        raise HotWalletPayoutUnavailable(PUBLIC_UNAVAILABLE_MESSAGE)

    words = HOT_WALLET_MNEMONIC.replace("\n", " ").split()
    if len(words) < 12:
        logger.error(
            "HOT_WALLET_MNEMONIC has invalid word count for TDSD hot wallet payout "
            "hot_wallet_address=%s word_count=%s",
            HOT_WALLET_ADDRESS,
            len(words),
        )
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
    logger.info(
        "Preparing hot wallet contract for TDSD payout hot_wallet_address=%s",
        HOT_WALLET_ADDRESS,
    )
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
        logger.exception(
            "Failed to create hot wallet contract from mnemonic "
            "hot_wallet_address=%s exception_type=%s exception=%s",
            HOT_WALLET_ADDRESS,
            type(exc).__name__,
            str(exc),
        )
        raise HotWalletPayoutUnavailable(PUBLIC_UNAVAILABLE_MESSAGE) from exc

    wallet = wallet_data[3]
    logger.info(
        "Checking HOT_WALLET_ADDRESS against mnemonic-derived wallet "
        "hot_wallet_address=%s",
        HOT_WALLET_ADDRESS,
    )
    configured_address = normalize_ton_wallet_address(HOT_WALLET_ADDRESS)
    generated_variants = _wallet_address_variants(wallet.address)
    configured_variants = get_address_forms(configured_address)
    if generated_variants.isdisjoint(configured_variants):
        logger.error(
            "HOT_WALLET_ADDRESS does not match HOT_WALLET_MNEMONIC wallet "
            "hot_wallet_address=%s",
            HOT_WALLET_ADDRESS,
        )
        raise HotWalletPayoutUnavailable(PUBLIC_UNAVAILABLE_MESSAGE)
    logger.info(
        "Hot wallet contract is ready for TDSD payout hot_wallet_address=%s",
        HOT_WALLET_ADDRESS,
    )
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
        logger.exception(
            "Failed to parse jetton wallet address from Toncenter BOC "
            "exception_type=%s exception=%s",
            type(exc).__name__,
            str(exc),
        )
        raise HotWalletPayoutUnavailable(PUBLIC_UNAVAILABLE_MESSAGE) from exc
    return _address_to_string(address)


def get_jetton_wallet_address(owner_wallet_address: str) -> str:
    logger.info(
        "Resolving TDSD jetton wallet address owner_wallet_address=%s "
        "jetton_master_address=%s",
        owner_wallet_address,
        TDSD_JETTON_MASTER_ADDRESS,
    )
    sdk = _load_tonsdk()
    try:
        master_address = normalize_ton_wallet_address(TDSD_JETTON_MASTER_ADDRESS)
        owner_address = normalize_ton_wallet_address(owner_wallet_address)
    except TonAddressValidationError as exc:
        logger.exception(
            "Invalid TON address while resolving TDSD jetton wallet "
            "owner_wallet_address=%s jetton_master_address=%s exception_type=%s "
            "exception=%s",
            owner_wallet_address,
            TDSD_JETTON_MASTER_ADDRESS,
            type(exc).__name__,
            str(exc),
        )
        raise HotWalletPayoutUnavailable(PUBLIC_UNAVAILABLE_MESSAGE) from exc
    stack = [["tvm.Slice", _address_stack_cell_b64(sdk, owner_address)]]

    try:
        logger.info(
            "Calling Toncenter get_wallet_address for TDSD jetton wallet "
            "owner_wallet_address=%s jetton_master_address=%s",
            owner_address,
            master_address,
        )
        result = run_get_method(master_address, "get_wallet_address", stack)
    except TonCenterError as exc:
        logger.exception(
            "Toncenter get_wallet_address failed for TDSD jetton wallet "
            "owner_wallet_address=%s jetton_master_address=%s exception_type=%s "
            "exception=%s",
            owner_address,
            master_address,
            type(exc).__name__,
            str(exc),
        )
        raise HotWalletPayoutUnavailable(PUBLIC_UNAVAILABLE_MESSAGE) from exc

    result_stack = result.get("stack") if isinstance(result, dict) else None
    logger.info(
        "Toncenter get_wallet_address response received for TDSD jetton wallet "
        "owner_wallet_address=%s jetton_master_address=%s has_stack=%s "
        "stack_length=%s result_type=%s",
        owner_address,
        master_address,
        bool(result_stack),
        len(result_stack) if isinstance(result_stack, list) else 0,
        type(result).__name__,
    )
    if not result_stack:
        logger.error(
            "Toncenter get_wallet_address returned empty stack for TDSD jetton wallet "
            "owner_wallet_address=%s jetton_master_address=%s response_type=%s",
            owner_address,
            master_address,
            type(result).__name__,
        )
        raise HotWalletPayoutUnavailable(PUBLIC_UNAVAILABLE_MESSAGE)

    boc_base64 = _stack_item_boc_base64(result_stack[0])
    if not boc_base64:
        logger.error(
            "Toncenter get_wallet_address stack has no BOC for TDSD jetton wallet "
            "owner_wallet_address=%s jetton_master_address=%s",
            owner_address,
            master_address,
        )
        raise HotWalletPayoutUnavailable(PUBLIC_UNAVAILABLE_MESSAGE)
    jetton_wallet_address = normalize_ton_wallet_address(
        _read_address_from_boc(sdk, boc_base64)
    )
    logger.info(
        "Resolved TDSD jetton wallet address owner_wallet_address=%s "
        "jetton_wallet_address=%s",
        owner_address,
        jetton_wallet_address,
    )
    return jetton_wallet_address


def _hot_wallet_seqno() -> int:
    try:
        logger.info(
            "Requesting hot wallet seqno from Toncenter hot_wallet_address=%s",
            HOT_WALLET_ADDRESS,
        )
        info = get_wallet_information(HOT_WALLET_ADDRESS)
    except TonCenterError as exc:
        logger.exception(
            "Toncenter wallet information request failed for hot wallet "
            "hot_wallet_address=%s exception_type=%s exception=%s",
            HOT_WALLET_ADDRESS,
            type(exc).__name__,
            str(exc),
        )
        raise HotWalletPayoutFailed(PUBLIC_SEND_FAILED_MESSAGE) from exc

    try:
        seqno = int(info.get("seqno") or 0)
    except (TypeError, ValueError) as exc:
        logger.exception(
            "Could not parse hot wallet seqno from Toncenter response "
            "hot_wallet_address=%s response_keys=%s exception_type=%s exception=%s",
            HOT_WALLET_ADDRESS,
            sorted(info.keys()) if isinstance(info, dict) else [],
            type(exc).__name__,
            str(exc),
        )
        raise HotWalletPayoutFailed(PUBLIC_SEND_FAILED_MESSAGE) from exc
    logger.info(
        "Received hot wallet seqno from Toncenter hot_wallet_address=%s seqno=%s "
        "response_keys=%s",
        HOT_WALLET_ADDRESS,
        seqno,
        sorted(info.keys()) if isinstance(info, dict) else [],
    )
    return seqno


def _build_jetton_transfer_body(
    sdk: _TonSdk,
    recipient_wallet_address: str,
    amount_units: int,
    query_id: int,
) -> object:
    logger.info(
        "Building TDSD jetton transfer payload hot_wallet_address=%s "
        "recipient_wallet_address=%s amount_units=%s query_id=%s",
        HOT_WALLET_ADDRESS,
        recipient_wallet_address,
        amount_units,
        query_id,
    )
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
    logger.info(
        "Starting TDSD hot wallet payout purchase_id=%s hot_wallet_address=%s "
        "recipient_wallet_address=%s amount_units=%s",
        purchase_id,
        HOT_WALLET_ADDRESS,
        recipient_wallet_address,
        amount_units,
    )
    if amount_units <= 0:
        logger.error(
            "TDSD hot wallet payout amount is not positive purchase_id=%s "
            "hot_wallet_address=%s recipient_wallet_address=%s amount_units=%s",
            purchase_id,
            HOT_WALLET_ADDRESS,
            recipient_wallet_address,
            amount_units,
        )
        raise HotWalletPayoutFailed(PUBLIC_SEND_FAILED_MESSAGE)

    sdk = _load_tonsdk()
    try:
        logger.info(
            "Validating payout addresses purchase_id=%s hot_wallet_address=%s "
            "recipient_wallet_address=%s",
            purchase_id,
            HOT_WALLET_ADDRESS,
            recipient_wallet_address,
        )
        recipient_wallet = normalize_ton_wallet_address(recipient_wallet_address)
        normalize_ton_wallet_address(HOT_WALLET_ADDRESS)
    except TonAddressValidationError as exc:
        logger.exception(
            "Invalid payout address for TDSD hot wallet payout purchase_id=%s "
            "hot_wallet_address=%s recipient_wallet_address=%s exception_type=%s "
            "exception=%s",
            purchase_id,
            HOT_WALLET_ADDRESS,
            recipient_wallet_address,
            type(exc).__name__,
            str(exc),
        )
        raise HotWalletPayoutUnavailable(PUBLIC_UNAVAILABLE_MESSAGE) from exc

    try:
        wallet = _hot_wallet_contract(sdk)
        logger.info(
            "Resolving hot wallet TDSD jetton wallet purchase_id=%s "
            "hot_wallet_address=%s",
            purchase_id,
            HOT_WALLET_ADDRESS,
        )
        hot_jetton_wallet = get_jetton_wallet_address(HOT_WALLET_ADDRESS)
        logger.info(
            "Resolving recipient TDSD jetton wallet purchase_id=%s "
            "recipient_wallet_address=%s",
            purchase_id,
            recipient_wallet,
        )
        recipient_jetton_wallet = get_jetton_wallet_address(recipient_wallet)
        query_id = (int(time.time()) << 32) + int(purchase_id)
        payload = _build_jetton_transfer_body(
            sdk=sdk,
            recipient_wallet_address=recipient_wallet,
            amount_units=amount_units,
            query_id=query_id,
        )
    except HotWalletPayoutUnavailable as exc:
        logger.exception(
            "TDSD hot wallet payout unavailable during preparation "
            "purchase_id=%s hot_wallet_address=%s recipient_wallet_address=%s "
            "amount_units=%s exception_type=%s exception=%s",
            purchase_id,
            HOT_WALLET_ADDRESS,
            recipient_wallet_address,
            amount_units,
            type(exc).__name__,
            str(exc),
        )
        raise
    except Exception as exc:
        logger.exception(
            "TDSD hot wallet payout preparation failed purchase_id=%s "
            "hot_wallet_address=%s recipient_wallet_address=%s amount_units=%s "
            "exception_type=%s exception=%s",
            purchase_id,
            HOT_WALLET_ADDRESS,
            recipient_wallet_address,
            amount_units,
            type(exc).__name__,
            str(exc),
        )
        raise

    try:
        seqno = _hot_wallet_seqno()
        logger.info(
            "Creating TDSD jetton transfer message purchase_id=%s "
            "hot_wallet_address=%s hot_jetton_wallet_address=%s "
            "recipient_wallet_address=%s recipient_jetton_wallet_address=%s "
            "amount_units=%s query_id=%s seqno=%s",
            purchase_id,
            HOT_WALLET_ADDRESS,
            hot_jetton_wallet,
            recipient_wallet,
            recipient_jetton_wallet,
            amount_units,
            query_id,
            seqno,
        )
        message = wallet.create_transfer_message(
            to_addr=hot_jetton_wallet,
            amount=decimal_to_nano(HOT_WALLET_JETTON_TRANSFER_GAS_TON),
            seqno=seqno,
            payload=payload,
        )["message"]
        message_hash = sdk.bytes_to_b64str(message.bytes_hash())
        boc_base64 = sdk.bytes_to_b64str(message.to_boc(False))
        logger.info(
            "Sending TDSD hot wallet payout message purchase_id=%s "
            "hot_wallet_address=%s recipient_wallet_address=%s amount_units=%s "
            "message_hash=%s message_size=%s",
            purchase_id,
            HOT_WALLET_ADDRESS,
            recipient_wallet,
            amount_units,
            message_hash,
            len(boc_base64),
        )
        send_result = send_boc(boc_base64)
        logger.info(
            "Toncenter send BOC response for TDSD hot wallet payout "
            "purchase_id=%s hot_wallet_address=%s recipient_wallet_address=%s "
            "amount_units=%s message_hash=%s result_type=%s accepted=%s",
            purchase_id,
            HOT_WALLET_ADDRESS,
            recipient_wallet,
            amount_units,
            message_hash,
            type(send_result).__name__,
            send_result is not None,
        )
    except HotWalletPayoutUnavailable as exc:
        logger.exception(
            "TDSD hot wallet payout unavailable during send purchase_id=%s "
            "hot_wallet_address=%s recipient_wallet_address=%s amount_units=%s "
            "exception_type=%s exception=%s",
            purchase_id,
            HOT_WALLET_ADDRESS,
            recipient_wallet_address,
            amount_units,
            type(exc).__name__,
            str(exc),
        )
        raise
    except Exception as exc:
        logger.exception(
            "TDSD hot wallet payout send failed purchase_id=%s "
            "hot_wallet_address=%s recipient_wallet_address=%s amount_units=%s "
            "exception_type=%s exception=%s",
            purchase_id,
            HOT_WALLET_ADDRESS,
            recipient_wallet_address,
            amount_units,
            type(exc).__name__,
            str(exc),
        )
        raise HotWalletPayoutFailed(PUBLIC_SEND_FAILED_MESSAGE) from exc

    logger.info(
        "TDSD hot wallet payout sent purchase_id=%s hot_wallet_address=%s "
        "recipient_wallet_address=%s amount_units=%s message_hash=%s "
        "hot_jetton_wallet_address=%s recipient_jetton_wallet_address=%s",
        purchase_id,
        HOT_WALLET_ADDRESS,
        recipient_wallet,
        amount_units,
        message_hash,
        hot_jetton_wallet,
        recipient_jetton_wallet,
    )
    return HotWalletPayoutResult(
        tx_hash=message_hash,
        hot_jetton_wallet_address=hot_jetton_wallet,
        recipient_jetton_wallet_address=recipient_jetton_wallet,
    )
