from .. import models
from .base import AssetProvider, ProviderError
from .jetton import JettonProvider
from .ton_native import TonNativeProvider


def get_provider_for_asset(asset: models.Asset) -> AssetProvider:
    if asset.asset_type == "native" and asset.network == "ton_testnet":
        return TonNativeProvider()
    if asset.asset_type == "jetton":
        return JettonProvider(asset.network)

    raise ProviderError(
        f"Для актива {asset.symbol} пока нет deposit provider"
    )
