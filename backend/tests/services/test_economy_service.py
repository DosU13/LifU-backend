import pytest

from core.enums import CollectableRarity, Element
from core.errors import InsufficientCollectables
from repos.memory import MemoryCollectableRepository, MemoryWalletRepository
from services.economy_service import EconomyService

BASE_ROW = [1, 3, 9, 27, 81, 243]
COMBINED_ROW = [3, 9, 27, 81, 243, 729]


def _make_service(
    stock: dict,
) -> tuple[EconomyService, MemoryCollectableRepository, MemoryWalletRepository]:
    collectables = MemoryCollectableRepository()
    collectables.adjust(stock)
    wallet = MemoryWalletRepository()
    return EconomyService(collectables=collectables, wallet=wallet), collectables, wallet


@pytest.mark.parametrize("rarity_index", range(6))
def test_sell_credits_exact_base_row_price(rarity_index):
    rarity = CollectableRarity(rarity_index)
    service, collectables, wallet = _make_service({(Element.FIRE, rarity): 1})

    new_balance = service.sell(Element.FIRE, rarity, count=1)

    assert new_balance == BASE_ROW[rarity_index]
    assert wallet.get_coins() == BASE_ROW[rarity_index]
    assert collectables.get_all()[(Element.FIRE, rarity)] == 0


@pytest.mark.parametrize("rarity_index", range(6))
def test_sell_credits_exact_combined_row_price(rarity_index):
    rarity = CollectableRarity(rarity_index)
    service, collectables, wallet = _make_service({(Element.GROWTH, rarity): 1})

    new_balance = service.sell(Element.GROWTH, rarity, count=1)

    assert new_balance == COMBINED_ROW[rarity_index]
    assert collectables.get_all()[(Element.GROWTH, rarity)] == 0


def test_sell_multiplies_price_by_count():
    service, collectables, wallet = _make_service({(Element.EARTH, CollectableRarity.CRYSTAL): 5})

    new_balance = service.sell(Element.EARTH, CollectableRarity.CRYSTAL, count=4)

    assert new_balance == 9 * 4
    assert collectables.get_all()[(Element.EARTH, CollectableRarity.CRYSTAL)] == 1


def test_sell_insufficient_stock_mutates_nothing():
    service, collectables, wallet = _make_service({(Element.FIRE, CollectableRarity.FRAGMENT): 2})

    with pytest.raises(InsufficientCollectables):
        service.sell(Element.FIRE, CollectableRarity.FRAGMENT, count=3)

    assert collectables.get_all()[(Element.FIRE, CollectableRarity.FRAGMENT)] == 2
    assert wallet.get_coins() == 0


@pytest.mark.parametrize("bad_count", [0, -1])
def test_sell_rejects_non_positive_count(bad_count):
    service, collectables, wallet = _make_service({(Element.FIRE, CollectableRarity.FRAGMENT): 5})

    with pytest.raises(ValueError):
        service.sell(Element.FIRE, CollectableRarity.FRAGMENT, count=bad_count)

    assert collectables.get_all()[(Element.FIRE, CollectableRarity.FRAGMENT)] == 5
    assert wallet.get_coins() == 0
