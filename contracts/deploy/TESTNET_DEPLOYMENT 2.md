# TDSD Testnet Deployment

This is the deployment checklist for the TDSD Jetton contract package.

## Prerequisites

- TON testnet wallet funded with test TON.
- Blueprint or another TON contract build system.
- Owner wallet address.
- Public metadata URL or on-chain metadata cell.

## Steps

1. Create a clean TON contract project.
2. Copy:
   - `contracts/func/tdsd-jetton-master.fc`
   - `contracts/func/tdsd-jetton-wallet.fc`
   - `contracts/metadata/tdsd-metadata.json`
3. Compile wallet code first.
4. Compile master code with the wallet code cell embedded in initial data.
5. Deploy master contract to testnet.
6. Call `get_jetton_data` and verify:
   - admin address is correct;
   - content points to TDSD metadata;
   - wallet code hash is stable.
7. Mint test supply only from the admin wallet.
8. Derive project Jetton Wallet address for the backend treasury wallet.
9. Configure backend:

```env
TDSD_JETTON_MASTER_ADDRESS=<master>
TDSD_PROJECT_JETTON_WALLET=<project jetton wallet>
TDSD_DEPOSITS_ENABLED=true
```

10. Run:

```bash
alembic upgrade head
python production_seed.py
```

11. Test a TDSD deposit with a small amount and verify that:
   - `AssetDeposit` becomes `confirmed`;
   - `AssetBalance` increases;
   - `AssetLedgerEntry` contains `entry_type=deposit`.

## Verification

Use a testnet explorer and Jetton standard getters:

- `get_jetton_data`
- `get_wallet_address(owner)`
- wallet `get_wallet_data`

The deployed contract must not be promoted to mainnet before an external audit.
