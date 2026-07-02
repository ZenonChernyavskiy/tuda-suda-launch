# Codex Prompt — Stage 6: Asset Engine v2 / Provider Abstraction

You are an experienced full-stack developer. Continue the Telegram Mini App project "Tuda-Suda".

Current state:
- Stage 1: virtual gifts MVP exists.
- Stage 2: TON Connect exists.
- Stage 3: TON testnet deposits exist.
- Stage 4: Asset-based economy exists: `Asset`, `AssetBalance`, `AssetLedgerEntry`.
- Stage 5: internal off-chain asset gifts exist: `AssetGift`, gift history, gift leaderboard, gift feed, ledger debit/credit.

Goal of Stage 6:
Prepare the app for a future custom TON Jetton token, without implementing the Jetton smart contract yet.

IMPORTANT:
- Do NOT create a Jetton smart contract now.
- Do NOT implement withdrawals now.
- Do NOT switch to mainnet now.
- Do NOT remove existing TON testnet deposit flow.
- Do NOT break Stage 1–5 functionality.
- The goal is architecture: make deposits and asset operations provider-based and asset-agnostic.

## Task 1. Introduce provider abstraction

Create a backend module, for example:

```text
backend/app/providers/
  __init__.py
  base.py
  ton_native.py
  registry.py
```

`base.py` should define a provider interface/class with methods such as:

- `asset_type`
- `network`
- `create_deposit_instructions(asset, user, amount_units)`
- `verify_deposit(deposit, user)`
- future TODO: `send_withdrawal(...)`

`ton_native.py` should wrap the existing TON native deposit verification logic.

`registry.py` should return the correct provider for an `Asset`.

For now:
- `asset_type = native`
- `network = ton_testnet`
- provider = `TonNativeProvider`

Later:
- `asset_type = jetton`
- provider = `JettonProvider`

## Task 2. Prepare generic AssetDeposit model

Keep `TonDeposit` for backward compatibility, but add a generic model:

`AssetDeposit`:
- id
- user_id
- asset_id
- wallet_address
- target_wallet_address
- amount_units
- tx_hash
- comment
- status
- provider
- network
- failed_reason
- created_at
- confirmed_at

Status:
- pending
- confirmed
- failed

Important:
- Use integer `amount_units`, not float.
- For TON this is nanotons.
- For future Jetton this is smallest token units.

## Task 3. Add generic deposit endpoints

Add:

`POST /asset-deposits/create`

Request:
```json
{
  "asset_symbol": "TON",
  "amount_units": 100000000
}
```

Response:
- deposit_id
- asset symbol
- amount_units
- amount_display
- target_wallet_address
- comment
- provider
- network
- status

Add:

`POST /asset-deposits/{deposit_id}/verify`

Logic:
- get deposit
- get asset
- get provider from registry
- verify via provider
- if confirmed:
  - credit `AssetBalance`
  - create `AssetLedgerEntry` with `entry_type = deposit`
  - set `confirmed_at`

Add:

`GET /asset-deposits`

Returns current user's generic deposits.

## Task 4. Keep old TON endpoints as compatibility wrappers

Existing endpoints:
- `/ton/deposits/create`
- `/ton/deposits/{id}/verify`
- `/ton/deposits`
- `/ton/balance`

Should keep working.

But internally, where possible, route new logic through the asset/provider layer.

Do not delete `TonDeposit` yet.

## Task 5. Frontend

Add or prepare a generic deposit UI:

- user selects asset from active assets;
- for now only TON is available;
- create asset deposit;
- send transaction through TON Connect if provider is `ton_native`;
- verify deposit;
- show deposit history.

The old TON deposit UI can remain, but new UI should be asset-oriented where possible.

## Task 6. Seed future token placeholder support

Do not create a real token automatically.

But add documentation and optional dev-only seed helper showing how a future token would be represented:

```text
symbol = TUDA
name = Tuda Token
asset_type = jetton
network = ton_testnet
contract_address = <Jetton Master address>
decimals = 9
```

No smart contract deployment yet.

## Task 7. README

Add section:

`Stage 6: Asset Engine v2 and Provider Abstraction`

Explain:
- why provider abstraction exists;
- how TON native deposits work now;
- how Jetton deposits will be added later;
- why `AssetDeposit` is generic;
- what still remains before launching a custom token.

## Task 8. Testing

Verify:
- backend compiles;
- frontend builds;
- old TON deposits still work;
- generic asset deposit create/list endpoints work;
- asset gift flow from Stage 5 still works;
- balances and ledger remain correct.

## Final report

After implementation, report:
1. files changed;
2. new models;
3. new endpoints;
4. provider architecture;
5. how old TON endpoints remain compatible;
6. how future Jetton support will be added;
7. what Stage 7 should be.
