import pytest

from core.enums import BASE_ELEMENTS, COMBINED_ELEMENTS, CollectableRarity, Element
from core.errors import InsufficientCollectables, InvalidMerge
from core.mappings import COMBINED_ELEMENT
from core.rng import SeededRng
from repos.memory import MemoryCollectableRepository
from services.merger_service import MergerService


class _ScriptedRng:
    """Returns a fixed sequence of `random()` values, then raises if exhausted."""

    def __init__(self, values: list[float]) -> None:
        self._values = list(values)

    def random(self) -> float:
        return self._values.pop(0)


def _repo_with_stock(stock: dict) -> MemoryCollectableRepository:
    repo = MemoryCollectableRepository()
    repo.adjust(stock)
    return repo


# --- merge_up: 3 -> 1 ---


@pytest.mark.parametrize(
    "element",
    [Element.FIRE, Element.HARMONY, Element.GROWTH],
    ids=["base", "harmony", "combined"],
)
def test_merge_up_consumes_3_produces_1_for_any_element_kind(element):
    repo = _repo_with_stock({(element, CollectableRarity.FRAGMENT): 3})
    service = MergerService(collectables=repo, rng=SeededRng(1))

    next_rarity = service.merge_up(element, CollectableRarity.FRAGMENT)

    assert next_rarity == CollectableRarity.SHARD
    stock = repo.get_all()
    assert stock[(element, CollectableRarity.FRAGMENT)] == 0
    assert stock[(element, CollectableRarity.SHARD)] == 1


def test_merge_up_rejects_core():
    repo = _repo_with_stock({(Element.FIRE, CollectableRarity.CORE): 3})
    service = MergerService(collectables=repo, rng=SeededRng(1))

    with pytest.raises(InvalidMerge):
        service.merge_up(Element.FIRE, CollectableRarity.CORE)

    # nothing should have been touched
    assert repo.get_all()[(Element.FIRE, CollectableRarity.CORE)] == 3


def test_merge_up_insufficient_stock_mutates_nothing():
    repo = _repo_with_stock({(Element.FIRE, CollectableRarity.FRAGMENT): 2})
    service = MergerService(collectables=repo, rng=SeededRng(1))

    with pytest.raises(InsufficientCollectables):
        service.merge_up(Element.FIRE, CollectableRarity.FRAGMENT)

    stock = repo.get_all()
    assert stock[(Element.FIRE, CollectableRarity.FRAGMENT)] == 2
    assert stock[(Element.FIRE, CollectableRarity.SHARD)] == 0


# --- merge_harmony ---


def test_harmony_merge_consumes_1_of_each_base_element():
    stock = {(e, CollectableRarity.FRAGMENT): 1 for e in BASE_ELEMENTS}
    repo = _repo_with_stock(stock)
    # fails immediately -> 0 extras
    service = MergerService(collectables=repo, rng=_ScriptedRng([0.9]))

    result = service.merge_harmony(CollectableRarity.FRAGMENT)

    assert result.extras == 0
    assert result.harmony_yield == 5
    new_stock = repo.get_all()
    for element in BASE_ELEMENTS:
        assert new_stock[(element, CollectableRarity.FRAGMENT)] == 0
    assert new_stock[(Element.HARMONY, CollectableRarity.FRAGMENT)] == 5


def test_harmony_merge_extras_sequence_is_pinned_by_rng():
    stock = {(e, CollectableRarity.FRAGMENT): 1 for e in BASE_ELEMENTS}
    repo = _repo_with_stock(stock)
    # succeed, succeed, succeed, fail -> 3 extras
    service = MergerService(collectables=repo, rng=_ScriptedRng([0.1, 0.2, 0.3, 0.9]))

    result = service.merge_harmony(CollectableRarity.FRAGMENT)

    assert result.extras == 3
    assert result.harmony_yield == 8
    assert repo.get_all()[(Element.HARMONY, CollectableRarity.FRAGMENT)] == 8


def test_harmony_merge_extras_capped():
    stock = {(e, CollectableRarity.FRAGMENT): 1 for e in BASE_ELEMENTS}
    repo = _repo_with_stock(stock)
    # always "succeeds" — extras must stop at HARMONY_EXTRA_CAP regardless
    service = MergerService(collectables=repo, rng=_ScriptedRng([0.0] * 1000))

    result = service.merge_harmony(CollectableRarity.FRAGMENT)

    assert result.extras == 64  # HARMONY_EXTRA_CAP
    assert result.harmony_yield == 5 + 64


def test_harmony_merge_insufficient_stock_mutates_nothing():
    stock = {(e, CollectableRarity.FRAGMENT): 1 for e in BASE_ELEMENTS}
    del stock[(Element.EARTH, CollectableRarity.FRAGMENT)]  # missing one element
    repo = _repo_with_stock(stock)
    service = MergerService(collectables=repo, rng=_ScriptedRng([0.9]))

    with pytest.raises(InsufficientCollectables):
        service.merge_harmony(CollectableRarity.FRAGMENT)

    new_stock = repo.get_all()
    for element in BASE_ELEMENTS:
        if element != Element.EARTH:
            assert new_stock[(element, CollectableRarity.FRAGMENT)] == 1
    assert new_stock[(Element.HARMONY, CollectableRarity.FRAGMENT)] == 0


# --- combine ---


@pytest.mark.parametrize(("pair", "expected"), COMBINED_ELEMENT.items())
def test_combine_produces_correct_element_for_all_10_pairs(pair, expected):
    a, b = tuple(pair)
    repo = _repo_with_stock(
        {
            (a, CollectableRarity.SHARD): 1,
            (b, CollectableRarity.SHARD): 1,
            (Element.HARMONY, CollectableRarity.SHARD): 1,
        }
    )
    service = MergerService(collectables=repo, rng=SeededRng(1))

    result = service.combine(a, b, CollectableRarity.SHARD)

    assert result == expected
    assert result in COMBINED_ELEMENTS
    stock = repo.get_all()
    assert stock[(a, CollectableRarity.SHARD)] == 0
    assert stock[(b, CollectableRarity.SHARD)] == 0
    assert stock[(Element.HARMONY, CollectableRarity.SHARD)] == 0
    assert stock[(expected, CollectableRarity.SHARD)] == 1


def test_combine_rejects_invalid_pair():
    repo = _repo_with_stock(
        {
            (Element.FIRE, CollectableRarity.SHARD): 5,
            (Element.HARMONY, CollectableRarity.SHARD): 5,
        }
    )
    service = MergerService(collectables=repo, rng=SeededRng(1))

    with pytest.raises(InvalidMerge):
        service.combine(Element.FIRE, Element.FIRE, CollectableRarity.SHARD)

    stock = repo.get_all()
    assert stock[(Element.FIRE, CollectableRarity.SHARD)] == 5  # untouched


def test_combine_insufficient_stock_mutates_nothing():
    repo = _repo_with_stock(
        {
            (Element.EARTH, CollectableRarity.SHARD): 1,
            (Element.WATER, CollectableRarity.SHARD): 1,
            # no Harmony in stock
        }
    )
    service = MergerService(collectables=repo, rng=SeededRng(1))

    with pytest.raises(InsufficientCollectables):
        service.combine(Element.EARTH, Element.WATER, CollectableRarity.SHARD)

    stock = repo.get_all()
    assert stock[(Element.EARTH, CollectableRarity.SHARD)] == 1
    assert stock[(Element.WATER, CollectableRarity.SHARD)] == 1
    assert stock[(Element.GROWTH, CollectableRarity.SHARD)] == 0
