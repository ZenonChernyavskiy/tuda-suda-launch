# TDSD Jetton Contracts

This folder is the TON testnet contract workspace for the Tuda Suda token
(`TDSD`). TDSD is an ecosystem token for gifts, internal balances, karma and
transparent ledger records. It is not positioned as an investment asset.

The workspace uses Blueprint-compatible scripts around two FunC contracts:

- `func/tdsd-jetton-master.fc`
- `func/tdsd-jetton-wallet.fc`

It includes wrappers, compile targets, sandbox tests and operational scripts for
deploy, mint, transfer, burn and getter checks.

## Safety Status

This package is prepared for testnet validation. It is not mainnet-ready until:

- `npm install` completes in a normal networked environment;
- `npm run build` and `npm test` pass;
- the deployed testnet contract is verified with TON explorers and getters;
- an external TON smart-contract security audit is completed.

No private keys, seed phrases or mnemonics must be committed to this repository.
Use a local wallet provider, hardware wallet or CI secret store.

## Install

```bash
cd tuda-suda/contracts
npm install
cp .env.contracts.example .env.contracts
```

Fill `.env.contracts` with public addresses and test values only. Keep wallet
mnemonics outside the repository.

## Build And Test

```bash
npm run build
npm test
```

The tests run the Jetton master and wallet in TON sandbox and verify:

- deploy;
- `get_jetton_data`;
- deterministic wallet address derivation;
- mint to a user Jetton wallet;
- wallet `get_wallet_data`.

## Deploy To Testnet

1. Fund a TON testnet wallet with test TON.
2. Set `TDSD_METADATA_URL` in `.env.contracts`.
3. Optionally set:

```env
TDSD_OWNER_ADDRESS=<admin wallet address>
TDSD_PROJECT_WALLET_ADDRESS=<project TON wallet owner>
```

4. Deploy:

```bash
npm run deploy:testnet
```

The script prints backend env values:

```env
TDSD_JETTON_MASTER_ADDRESS=<deployed master>
TDSD_PROJECT_JETTON_WALLET=<derived project jetton wallet>
TDSD_DEPOSITS_ENABLED=true
```

## Mint Test Supply

Only the admin wallet can mint.

```env
TDSD_JETTON_MASTER_ADDRESS=<master>
TDSD_MINT_RECIPIENT=<recipient owner wallet>
TDSD_MINT_AMOUNT_UNITS=1000000000000
```

```bash
npm run mint:testnet
```

## Transfer

```env
TDSD_JETTON_MASTER_ADDRESS=<master>
TDSD_TRANSFER_DESTINATION_OWNER=<recipient owner wallet>
TDSD_TRANSFER_AMOUNT_UNITS=10000000000
TDSD_TRANSFER_MEMO=Tuda Suda test transfer
```

```bash
npm run transfer:testnet
```

For backend deposit testing, send TDSD to the project owner wallet or project
Jetton wallet flow described in `deploy/TESTNET_DEPLOYMENT.md`, with the deposit
memo produced by the backend.

## Burn

```env
TDSD_JETTON_MASTER_ADDRESS=<master>
TDSD_BURN_AMOUNT_UNITS=1000000000
```

```bash
npm run burn:testnet
```

## Getters

```env
TDSD_JETTON_MASTER_ADDRESS=<master>
TDSD_WALLET_OWNER=<optional owner wallet>
```

```bash
npm run get:data
```

The getter script prints master data, code hashes, derived wallet address and
wallet balance if `TDSD_WALLET_OWNER` is set.

## Connect To Backend

After deploy and verification:

```env
SEED_TDSD_ASSET=true
TDSD_ASSET_SYMBOL=TDSD
TDSD_ASSET_NAME=Tuda Suda Token
TDSD_DECIMALS=9
TDSD_NETWORK=ton_testnet
TDSD_JETTON_MASTER_ADDRESS=<Jetton Master>
TDSD_PROJECT_JETTON_WALLET=<Project Jetton Wallet>
TDSD_DEPOSITS_ENABLED=true
```

Then run:

```bash
cd ../backend
alembic upgrade head
python production_seed.py
```

The backend will activate TDSD as an `Asset`, verify deposits via
`JettonProvider`, credit `AssetBalance`, and write `AssetLedgerEntry` records.

## Mainnet Rule

Do not deploy this contract to mainnet until testnet E2E checks and an external
security audit are complete.
