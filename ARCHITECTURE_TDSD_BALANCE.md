# ARCHITECTURE_TDSD_BALANCE

## Current TDSD Model

Tuda Suda uses an internal TDSD ledger for in-app actions and a hot-wallet payout flow for on-chain delivery.

The application source of truth for in-app operations is:

- `asset_balances` — user-visible in-app TDSD balance;
- `asset_ledger_entries` — append-only accounting trail for credits, debits, fees and service income;
- `asset_deposits` — purchase/deposit lifecycle, including on-chain payment confirmation and payout status.

On-chain TDSD delivery is tracked separately through `asset_deposits.payout_status`, `payout_tx_hash`, `payout_sent_at` and `payout_failed_reason`.

## Purchase Flow

1. User creates a TDSD purchase.
2. Backend returns the hot wallet public payment address.
3. User sends TON to the hot wallet.
4. Backend verifies the TON transaction.
5. Backend calculates TDSD by the fixed price `1 TDSD = 0.1 TON`.
6. Backend applies purchase fee according to `PURCHASE_FEE_PERCENT`.
7. Backend credits the internal TDSD ledger and starts hot-wallet TDSD payout.
8. Backend stores payout status as `pending`, `sent`, `confirmed` or `failed`.

## Balance Meaning

The in-app TDSD balance is the balance available for app features such as gifts and user reveal payments.

The on-chain TDSD balance is the balance in the user's TON wallet. It must not be described as guaranteed by the app unless the related payout has a successful on-chain transaction and reconciliation confirms it.

If a hot-wallet payout fails after a verified purchase, the internal ledger and on-chain delivery can temporarily diverge. Such deposits must be visible for support/reconciliation through `asset_deposits.payout_status` and ledger entries.

## Reconciliation Rules

Production reconciliation should check:

- every confirmed TDSD purchase has a final payout status;
- every `sent`/`confirmed` payout has a unique `payout_tx_hash`;
- failed payouts are retried manually or by a controlled retry job;
- ledger credits for purchases are linked to `asset_deposits`;
- public UI uses Russian user-facing statuses and does not expose technical payout errors.

## Security Rules

- Internal debits from `asset_balances` must use atomic balance updates.
- `HOT_WALLET_MNEMONIC` is backend-only and must never be logged or sent to frontend.
- Frontend can receive only the public payment address.
- `PROJECT_TON_WALLET` is deprecated; `HOT_WALLET_ADDRESS` is the payment address.
