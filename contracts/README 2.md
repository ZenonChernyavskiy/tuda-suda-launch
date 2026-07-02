# TDSD Jetton Contracts

This folder contains the Stage 8 contract package for the Tuda Suda token
(`TDSD`). The application philosophy is social generosity and reputation; the
token is an ecosystem asset for gifts, not an investment product.

## Status

- Target network: TON testnet first.
- Token standard: TON Jetton.
- Included contracts: Master and Wallet source templates.
- Included operations: mint, burn notification handling, transfer path,
  metadata storage, and wallet address derivation shape.

Before mainnet, these contracts must be compiled with a TON toolchain, deployed
to testnet, verified against Jetton standard tooling, and externally audited.

## Suggested Tooling

Use Blueprint or another TON-compatible build system:

```bash
npm create ton@latest tdsd-contracts
```

Then copy the sources from `contracts/func` into the generated project and wire
them into the generated compile/deploy scripts.

## Deployment Flow

1. Compile the Jetton wallet code.
2. Build the metadata cell from `metadata/tdsd-metadata.json`.
3. Deploy the Jetton master contract with:
   - owner address
   - total supply `0`
   - metadata cell
   - wallet code cell
4. Mint a limited testnet supply to the treasury or project wallet.
5. Derive the project Jetton Wallet address from the master contract.
6. Set backend env:

```env
TDSD_JETTON_MASTER_ADDRESS=<deployed master address>
TDSD_PROJECT_JETTON_WALLET=<project jetton wallet address>
TDSD_DEPOSITS_ENABLED=true
```

7. Run migrations and `python production_seed.py`.

## Backend Integration

The backend does not mint tokens. It only:

- stores `TDSD` as an `Asset`;
- creates internal `AssetBalance` rows;
- verifies deposits through `JettonProvider`;
- records every change in `AssetLedgerEntry`;
- allows off-chain random gifts using `AssetGift`.

Withdrawals are intentionally not implemented.
