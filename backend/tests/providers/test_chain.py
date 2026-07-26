import requests

from core.entities import GeneratedContent
from core.enums import GeneratedKind, ReceptacleRarity
from core.rng import SeededRng
from providers.art import ArtInstituteSource, DeviantArtSource
from providers.chain import ChainContentProvider, build_content_provider
from providers.fallback import FallbackContentProvider
from providers.music import ITunesSource, JamendoSource
from providers.quotes import UselessFactsSource, ZenQuotesSource


class _OkSource:
    def __init__(self, text="live content"):
        self.text = text
        self.calls = 0

    def fetch(self) -> GeneratedContent:
        self.calls += 1
        return GeneratedContent(
            kind=GeneratedKind.QUOTE, title="t", url="", author="a", text=self.text
        )


class _FailingSource:
    def __init__(self, exc=None):
        self.exc = exc or RuntimeError("boom")
        self.calls = 0

    def fetch(self) -> GeneratedContent:
        self.calls += 1
        raise self.exc


class _EmptySource:
    def fetch(self) -> GeneratedContent:
        return GeneratedContent(kind=GeneratedKind.QUOTE, title="", url="", author="", text="")


def _chain(pouch=None, sack=None) -> ChainContentProvider:
    rng = SeededRng(1)
    return ChainContentProvider(
        pouch_sources=pouch if pouch is not None else [],
        sack_sources=sack if sack is not None else [],
        fallback=FallbackContentProvider(rng=rng),
        rng=rng,
    )


def test_returns_live_content_when_a_source_succeeds():
    source = _OkSource()
    content = _chain(pouch=[source]).fetch(ReceptacleRarity.POUCH)

    assert content.text == "live content"
    assert source.calls == 1


def test_falls_through_to_the_next_source_on_failure():
    """Source order is shuffled, so run enough times that the failing source

    is definitely picked first at least once — live content must win anyway.
    """
    failing = _FailingSource()
    working = _OkSource()
    chain = _chain(pouch=[failing, working])

    for _ in range(20):
        assert chain.fetch(ReceptacleRarity.POUCH).text == "live content"

    assert failing.calls > 0  # it was tried and skipped, not merely ignored
    assert working.calls == 20


def test_falls_back_to_local_when_every_source_fails():
    sources = [_FailingSource(), _FailingSource()]
    content = _chain(pouch=sources).fetch(ReceptacleRarity.POUCH)

    assert content.text  # local content, never empty
    assert all(s.calls == 1 for s in sources)


def test_timeout_is_treated_like_any_other_failure():
    failing = _FailingSource(requests.Timeout("too slow"))
    content = _chain(pouch=[failing]).fetch(ReceptacleRarity.POUCH)

    assert content.text  # degraded to local content rather than raising
    assert failing.calls == 1


def test_malformed_payload_failure_falls_back():
    failing = _FailingSource(KeyError("missing field"))
    content = _chain(pouch=[failing]).fetch(ReceptacleRarity.POUCH)
    assert content.text


def test_empty_content_is_rejected_in_favour_of_the_next_source():
    working = _OkSource()
    content = _chain(pouch=[_EmptySource(), working]).fetch(ReceptacleRarity.POUCH)

    assert content.text == "live content"


def test_no_sources_at_all_still_returns_local_content():
    content = _chain(pouch=[]).fetch(ReceptacleRarity.POUCH)
    assert content.text


def test_sack_and_pouch_use_separate_source_lists():
    pouch_source = _OkSource("pouch content")
    sack_source = _OkSource("sack content")
    chain = _chain(pouch=[pouch_source], sack=[sack_source])

    assert chain.fetch(ReceptacleRarity.POUCH).text == "pouch content"
    assert chain.fetch(ReceptacleRarity.SACK).text == "sack content"


def test_fetch_never_raises_even_when_all_sources_explode():
    chain = _chain(pouch=[_FailingSource(), _FailingSource(), _FailingSource()])
    for _ in range(10):
        assert chain.fetch(ReceptacleRarity.POUCH).text


# --- builder ---


def test_builder_includes_key_free_sources_without_any_credentials():
    provider = build_content_provider(rng=SeededRng(1))

    pouch_types = {type(s) for s in provider._pouch_sources}
    sack_types = {type(s) for s in provider._sack_sources}

    assert pouch_types == {ZenQuotesSource, UselessFactsSource}
    assert sack_types == {ArtInstituteSource, ITunesSource}


def test_builder_adds_deviantart_only_when_both_credentials_present():
    without = build_content_provider(rng=SeededRng(1), deviantart_client_id="id")
    assert DeviantArtSource not in {type(s) for s in without._sack_sources}

    with_creds = build_content_provider(
        rng=SeededRng(1), deviantart_client_id="id", deviantart_client_secret="secret"
    )
    assert DeviantArtSource in {type(s) for s in with_creds._sack_sources}


def test_builder_adds_jamendo_when_client_id_present():
    provider = build_content_provider(rng=SeededRng(1), jamendo_client_id="abc")
    assert JamendoSource in {type(s) for s in provider._sack_sources}
