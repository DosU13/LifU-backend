from core.enums import CollectableRarity, Element
from core.mappings import sell_price
from repos.interfaces import CollectableRepository, WalletRepository


class EconomyService:
    def __init__(self, collectables: CollectableRepository, wallet: WalletRepository) -> None:
        self._collectables = collectables
        self._wallet = wallet

    def sell(self, element: Element, rarity: CollectableRarity, count: int) -> int:
        """Sell `count` collectables for coins (ARCHITECTURE §4). Returns the new coin balance."""
        if count <= 0:
            raise ValueError("count must be positive")
        self._collectables.adjust({(element, rarity): -count})
        return self._wallet.adjust(sell_price(element, rarity) * count)
