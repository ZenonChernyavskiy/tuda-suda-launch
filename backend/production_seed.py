from app.config import (
    SEED_TDSD_ASSET,
    TDSD_ASSET_NAME,
    TDSD_ASSET_SYMBOL,
    TDSD_DECIMALS,
    TDSD_DEPOSITS_ENABLED,
    TDSD_JETTON_MASTER_ADDRESS,
    TDSD_NETWORK,
)
from app.database import SessionLocal
from app.models import Asset


def upsert_asset(
    *,
    symbol: str,
    name: str,
    asset_type: str,
    network: str,
    decimals: int,
    contract_address: str | None,
    provider_key: str,
    display_order: int,
    is_active: bool,
) -> None:
    db = SessionLocal()
    try:
        asset = db.query(Asset).filter(Asset.symbol == symbol).first()
        if asset:
            asset.name = name
            asset.asset_type = asset_type
            asset.network = network
            asset.decimals = decimals
            asset.contract_address = contract_address or None
            asset.provider_key = provider_key
            asset.display_order = display_order
            asset.is_active = is_active
        else:
            db.add(
                Asset(
                    symbol=symbol,
                    name=name,
                    asset_type=asset_type,
                    network=network,
                    decimals=decimals,
                    contract_address=contract_address or None,
                    provider_key=provider_key,
                    display_order=display_order,
                    is_active=is_active,
                )
            )
        db.commit()
    finally:
        db.close()


def run() -> None:
    upsert_asset(
        symbol="TON",
        name="Toncoin",
        asset_type="native",
        network="ton_testnet",
        decimals=9,
        contract_address=None,
        provider_key="ton_native",
        display_order=0,
        is_active=True,
    )
    if SEED_TDSD_ASSET:
        tdsd_provider_key = "jetton" if TDSD_DEPOSITS_ENABLED else "tdsd_fixed_price"
        upsert_asset(
            symbol=TDSD_ASSET_SYMBOL,
            name=TDSD_ASSET_NAME,
            asset_type="jetton",
            network=TDSD_NETWORK,
            decimals=TDSD_DECIMALS,
            contract_address=TDSD_JETTON_MASTER_ADDRESS or None,
            provider_key=tdsd_provider_key,
            display_order=10,
            is_active=not TDSD_DEPOSITS_ENABLED or bool(TDSD_JETTON_MASTER_ADDRESS),
        )
    print("Production seed complete: assets are ready.")


if __name__ == "__main__":
    run()
