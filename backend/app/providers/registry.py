from .. import models
from ..config import TDSD_ASSET_SYMBOL, TDSD_DEPOSITS_ENABLED
from .base import AssetProvider, ProviderError
from .jetton import JettonProvider
from .tdsd_fixed_price import TdsdFixedPriceProvider
from .ton_native import TonNativeProvider


def get_provider_for_asset(asset: models.Asset) -> AssetProvider:
    if asset.asset_type == "native" and asset.network == "ton_testnet":
        return TonNativeProvider()
    if asset.symbol == TDSD_ASSET_SYMBOL and not TDSD_DEPOSITS_ENABLED:
        return TdsdFixedPriceProvider(asset.network)
    if asset.asset_type == "jetton":
        return JettonProvider(asset.network)

    raise ProviderError(
        f"Для актива {asset.symbol} пока нет deposit provider"
    )
