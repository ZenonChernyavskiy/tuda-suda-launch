# Stage 5 Audit — Internal Asset Gifts

## Verdict
Stage 5 is mostly implemented correctly: the app now supports internal off-chain `AssetGift` transfers using `AssetBalance` and `AssetLedgerEntry` instead of direct blockchain transfers.

I verified:
- backend Python modules compile;
- FastAPI app imports successfully;
- frontend builds with `npm run build`;
- `/assets`, `/assets/balances`, `/asset-gifts/send`, `/asset-gifts`, `/asset-gifts/leaderboard` work in a local TestClient flow;
- sender balance is debited and receiver balance is credited;
- ledger entries are created;
- old TON deposit flow is not removed.

## Fixes applied in this audited version

1. Added missing asset gift limits:
   - `MAX_GIFTS_PER_DAY`
   - `MAX_GIFTS_PER_HOUR`
   - `MIN_ASSET_GIFT_UNITS`

2. Added missing endpoints required by the Stage 5 plan:
   - `GET /asset-gifts/history`
   - `GET /asset-gifts/feed`

3. Added public feed schema:
   - `AssetGiftFeedItem`

4. Updated env examples with gift limit variables.

## Current architecture

The important Stage 5 flow is:

```text
User
  -> AssetBalance
  -> AssetGift
  -> AssetLedgerEntry sender debit
  -> AssetLedgerEntry receiver credit
  -> Karma update
```

Blockchain is still only used for deposits. Gifts are internal off-chain operations in the database.

## Important notes

### Fee logic
`GIFT_FEE_BPS` exists and default is `0`. The current fee implementation is acceptable for default zero-fee MVP. Before enabling non-zero fees in production, implement a proper treasury balance flow so ledger accounting remains clean.

### Gift feed
`/asset-gifts/feed` is intentionally anonymized. It does not expose sender or receiver identity.

### Legacy gifts
The old `/gift/send` virtual-coin flow remains available for compatibility. The product should now prioritize `AssetGift`.

## Recommended next stage
Stage 6 should not be Jetton yet. It should be Asset Engine v2 / Provider abstraction:

- abstract deposits away from `TonDeposit` into `AssetDeposit`;
- introduce provider modules: `TonNativeProvider`, later `JettonProvider`;
- prepare the system so adding TUDA/BLOOM Jetton does not require rewriting business logic;
- improve admin/debug tooling and database auditability.
