"""A failing content provider must never break a treasure buy."""

from core.enums import ReceptacleRarity
from core.rng import SeededRng
from providers.chain import ChainContentProvider
from providers.fallback import FallbackContentProvider
from tests.services.test_treasure_service import CHEST, _build, _ScriptedRng, _treasure_with


class _AlwaysFailingSource:
    def fetch(self):
        raise ConnectionError("upstream is down")


def _broken_live_chain() -> ChainContentProvider:
    rng = SeededRng(1)
    return ChainContentProvider(
        pouch_sources=[_AlwaysFailingSource(), _AlwaysFailingSource()],
        sack_sources=[_AlwaysFailingSource()],
        fallback=FallbackContentProvider(rng=rng),
        rng=rng,
    )


def _buy_generated(content_provider):
    """Force a buy whose drop is a generated Pouch (all real tiers miss)."""
    rng = _ScriptedRng(randoms=[0.9, 0.9, 0.9, 0.9, 0.9], randints=[7])
    service, receptacles, treasures, _, _ = _build(rng=rng)
    service._content = content_provider
    treasure = _treasure_with(service, receptacles, treasures, [(10, CHEST)])
    return service.buy(treasure.id)


def test_buy_succeeds_when_every_live_source_fails():
    result = _buy_generated(_broken_live_chain())

    assert result.dropped_rarity is ReceptacleRarity.POUCH
    assert result.receptacle.is_generated is True
    assert result.receptacle.content is not None
    assert result.receptacle.content.text  # degraded to local content, still populated


def test_generated_receptacle_stores_all_content_fields():
    result = _buy_generated(FallbackContentProvider(rng=SeededRng(2)))

    content = result.receptacle.content
    assert content.kind is not None
    assert isinstance(content.title, str)
    assert isinstance(content.url, str)
    assert isinstance(content.author, str)
    assert isinstance(content.text, str)
