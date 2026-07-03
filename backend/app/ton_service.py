import base64
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .config import TONCENTER_API_KEY, TONCENTER_API_URL, TONCENTER_TX_LIMIT


class TonCenterError(RuntimeError):
    pass


@dataclass
class MatchedTonTransaction:
    tx_hash: str
    source: str | None
    destination: str | None
    value_nano: int
    comment: str | None


@dataclass
class TonTransactionSearchResult:
    matched: MatchedTonTransaction | None = None
    failed_reason: str | None = None


def _toncenter_get(method: str, params: dict[str, Any]) -> Any:
    url = f"{TONCENTER_API_URL}/{method}?{urlencode(params)}"
    headers = {"Accept": "application/json"}
    if TONCENTER_API_KEY:
        headers["X-API-Key"] = TONCENTER_API_KEY

    request = Request(url, headers=headers)
    try:
        with urlopen(request, timeout=15) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise TonCenterError(f"TON Center HTTP {exc.code}: {detail}") from exc
    except (URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise TonCenterError(f"TON Center request failed: {exc}") from exc

    if not payload.get("ok"):
        raise TonCenterError(str(payload.get("error") or payload))
    return payload.get("result")


def get_recent_transactions(address: str, limit: int | None = None) -> list[dict[str, Any]]:
    tx_limit = limit or TONCENTER_TX_LIMIT
    result = _toncenter_get("getTransactions", {"address": address, "limit": tx_limit})
    return result if isinstance(result, list) else []


def get_address_forms(address: str) -> set[str]:
    forms = {address}
    try:
        result = _toncenter_get("detectAddress", {"address": address})
    except TonCenterError:
        return forms

    if not isinstance(result, dict):
        return forms

    for key in ("raw_form", "given_type"):
        value = result.get(key)
        if isinstance(value, str):
            forms.add(value)

    for key in ("bounceable", "non_bounceable"):
        value = result.get(key)
        if isinstance(value, dict):
            for nested in ("b64", "b64url"):
                nested_value = value.get(nested)
                if isinstance(nested_value, str):
                    forms.add(nested_value)

    return {item for item in forms if item}


def _addresses_match(left: str | None, right_forms: set[str]) -> bool:
    return bool(left and left in right_forms)


def _extract_tx_hash(transaction: dict[str, Any]) -> str | None:
    tx_id = transaction.get("transaction_id")
    if isinstance(tx_id, dict) and isinstance(tx_id.get("hash"), str):
        return tx_id["hash"]
    if isinstance(transaction.get("hash"), str):
        return transaction["hash"]
    return None


def _extract_comment(in_msg: dict[str, Any]) -> str | None:
    for key in ("message", "comment"):
        value = in_msg.get(key)
        if isinstance(value, str) and value:
            return value

    decoded_body = in_msg.get("decoded_body")
    if isinstance(decoded_body, dict):
        for key in ("text", "comment"):
            value = decoded_body.get(key)
            if isinstance(value, str) and value:
                return value

    msg_data = in_msg.get("msg_data")
    if isinstance(msg_data, dict):
        value = msg_data.get("text")
        if isinstance(value, str) and value:
            try:
                return base64.b64decode(value).decode("utf-8")
            except Exception:
                return value
    return None


def _transaction_after_deposit(transaction: dict[str, Any], deposit: Any) -> bool:
    created_at = getattr(deposit, "created_at", None)
    utime = transaction.get("utime")
    try:
        tx_timestamp = int(utime)
    except (TypeError, ValueError):
        return True

    if not isinstance(created_at, datetime):
        return True

    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    # Small leeway avoids rejecting transactions mined around the same second.
    return tx_timestamp >= int(created_at.timestamp()) - 60


def find_matching_deposit_transaction(
    deposit: Any,
    user_wallet_address: str,
) -> TonTransactionSearchResult:
    target_forms = get_address_forms(deposit.target_wallet_address)
    sender_forms = get_address_forms(user_wallet_address)
    transactions = get_recent_transactions(deposit.target_wallet_address)

    for transaction in transactions:
        in_msg = transaction.get("in_msg")
        if not isinstance(in_msg, dict):
            continue

        tx_hash = _extract_tx_hash(transaction)
        source = in_msg.get("source")
        destination = in_msg.get("destination")
        value_raw = in_msg.get("value") or 0
        try:
            value_nano = int(value_raw)
        except (TypeError, ValueError):
            value_nano = 0
        comment = _extract_comment(in_msg)

        if not tx_hash:
            continue

        destination_matches = _addresses_match(destination, target_forms)
        source_matches = _addresses_match(source, sender_forms)
        amount_matches = value_nano >= int(deposit.amount_nano)
        comment_matches = comment == deposit.comment

        if comment_matches:
            if not destination_matches:
                return TonTransactionSearchResult(
                    failed_reason="Получатель транзакции не совпадает с кошельком проекта"
                )
            if not source_matches:
                return TonTransactionSearchResult(
                    failed_reason="Отправитель транзакции не совпадает с сохраненным кошельком"
                )
            if not amount_matches:
                return TonTransactionSearchResult(
                    failed_reason="Сумма транзакции меньше ожидаемой"
                )

            return TonTransactionSearchResult(
                matched=MatchedTonTransaction(
                    tx_hash=tx_hash,
                    source=source,
                    destination=destination,
                    value_nano=value_nano,
                    comment=comment,
                )
            )

        if (
            destination_matches
            and source_matches
            and amount_matches
            and _transaction_after_deposit(transaction, deposit)
        ):
            # A similar transaction without the expected memo can happen by user mistake.
            # It should not immediately fail the deposit because the correct transaction
            # may still arrive before timeout.
            pass

    # Keep pending on memo mismatch; the API response can surface the hint through logs later,
    # but failing here would block a valid retry with the correct memo.
    return TonTransactionSearchResult()


def verify_deposit(deposit: Any, user_wallet_address: str) -> TonTransactionSearchResult:
    return find_matching_deposit_transaction(deposit, user_wallet_address)


def _decoded_comment(payload: Any) -> str | None:
    if not isinstance(payload, dict):
        return None
    for key in ("comment", "text", "message"):
        value = payload.get(key)
        if isinstance(value, str) and value:
            return value
    for key in ("forward_payload", "payload", "custom_payload"):
        nested = payload.get(key)
        comment = _decoded_comment(nested)
        if comment:
            return comment
    return None


def _decoded_amount(payload: Any) -> int:
    if not isinstance(payload, dict):
        return 0
    for key in ("amount", "jetton_amount"):
        value = payload.get(key)
        try:
            return int(value)
        except (TypeError, ValueError):
            continue
    for value in payload.values():
        amount = _decoded_amount(value)
        if amount:
            return amount
    return 0


def _decoded_sender(payload: Any) -> str | None:
    if not isinstance(payload, dict):
        return None
    for key in ("sender", "from", "owner", "response_destination"):
        value = payload.get(key)
        if isinstance(value, str) and (":" in value or value.startswith(("EQ", "UQ", "kQ"))):
            return value
    for value in payload.values():
        sender = _decoded_sender(value)
        if sender:
            return sender
    return None


def find_matching_jetton_deposit_transaction(
    deposit: Any,
    user_wallet_address: str,
    project_jetton_wallet: str,
) -> TonTransactionSearchResult:
    sender_forms = get_address_forms(user_wallet_address)
    target_forms = get_address_forms(project_jetton_wallet)
    transactions = get_recent_transactions(project_jetton_wallet)

    for transaction in transactions:
        in_msg = transaction.get("in_msg")
        if not isinstance(in_msg, dict):
            continue
        tx_hash = _extract_tx_hash(transaction)
        if not tx_hash:
            continue
        decoded = in_msg.get("decoded_body")
        comment = _decoded_comment(decoded) or _extract_comment(in_msg)
        amount_units = _decoded_amount(decoded)
        sender = _decoded_sender(decoded) or in_msg.get("source")
        destination = in_msg.get("destination")

        if comment != deposit.comment:
            continue
        if not _addresses_match(destination, target_forms):
            return TonTransactionSearchResult(
                failed_reason="Получатель пополнения TDSD не совпадает с ожидаемым адресом"
            )
        if sender and not _addresses_match(sender, sender_forms):
            return TonTransactionSearchResult(
                failed_reason="Отправитель пополнения не совпадает с сохраненным кошельком"
            )
        if amount_units < int(deposit.amount_units or 0):
            return TonTransactionSearchResult(
                failed_reason="Сумма пополнения TDSD меньше ожидаемой"
            )
        if not _transaction_after_deposit(transaction, deposit):
            continue
        return TonTransactionSearchResult(
            matched=MatchedTonTransaction(
                tx_hash=tx_hash,
                source=sender,
                destination=destination,
                value_nano=amount_units,
                comment=comment,
            )
        )

    return TonTransactionSearchResult()


def verify_jetton_deposit(
    deposit: Any,
    user_wallet_address: str,
    project_jetton_wallet: str,
) -> TonTransactionSearchResult:
    return find_matching_jetton_deposit_transaction(
        deposit,
        user_wallet_address,
        project_jetton_wallet,
    )
