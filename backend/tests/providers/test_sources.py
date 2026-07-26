"""Every source is tested against mocked HTTP — this suite never hits the network."""

import pytest
import requests

from core.enums import GeneratedKind
from core.rng import SeededRng
from providers.art import ArtInstituteSource, DeviantArtSource
from providers.music import ITunesSource, JamendoSource
from providers.quotes import UselessFactsSource, ZenQuotesSource


class _Response:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")

    def json(self):
        return self._payload


def _patch_get(monkeypatch, module, payload, status_code=200, capture=None):
    def fake_get(url, params=None, timeout=None, **kwargs):
        if capture is not None:
            capture.update(url=url, params=params, timeout=timeout)
        return _Response(payload, status_code)

    monkeypatch.setattr(f"providers.{module}.requests.get", fake_get)


# --- quotes ---


def test_zenquotes_parses_quote(monkeypatch):
    _patch_get(monkeypatch, "quotes", [{"q": "  Keep going.  ", "a": " Someone "}])

    content = ZenQuotesSource().fetch()

    assert content.kind is GeneratedKind.QUOTE
    assert content.text == "Keep going."
    assert content.author == "Someone"


def test_zenquotes_rejects_empty_quote(monkeypatch):
    _patch_get(monkeypatch, "quotes", [{"q": "   ", "a": "x"}])
    with pytest.raises(ValueError):
        ZenQuotesSource().fetch()


def test_zenquotes_propagates_http_error(monkeypatch):
    _patch_get(monkeypatch, "quotes", [], status_code=500)
    with pytest.raises(requests.HTTPError):
        ZenQuotesSource().fetch()


def test_useless_facts_parses_fact(monkeypatch):
    _patch_get(
        monkeypatch,
        "quotes",
        {"text": "Honey never spoils.", "source_url": "https://example.test/f"},
    )

    content = UselessFactsSource().fetch()

    assert content.kind is GeneratedKind.FACT
    assert content.text == "Honey never spoils."
    assert content.url == "https://example.test/f"


# --- art ---


def test_art_institute_builds_image_url(monkeypatch):
    captured = {}
    _patch_get(
        monkeypatch,
        "art",
        {
            "data": [
                {"id": 7, "title": "Starry Field", "artist_title": "A. Painter", "image_id": "abc"},
            ]
        },
        capture=captured,
    )

    content = ArtInstituteSource(SeededRng(1)).fetch()

    assert content.kind is GeneratedKind.ART
    assert content.title == "Starry Field"
    assert content.author == "A. Painter"
    assert content.url == "https://www.artic.edu/iiif/2/abc/full/843,/0/default.jpg"
    assert content.text == "https://www.artic.edu/artworks/7"
    assert 1 <= captured["params"]["page"] <= 400  # random page, for genuine variety


def test_art_institute_skips_artworks_without_images(monkeypatch):
    _patch_get(
        monkeypatch,
        "art",
        {"data": [{"id": 1, "title": "No Image", "artist_title": "X", "image_id": None}]},
    )
    with pytest.raises(ValueError):
        ArtInstituteSource(SeededRng(1)).fetch()


def test_deviantart_uses_token_then_browses(monkeypatch):
    def fake_post(url, data=None, timeout=None, **kwargs):
        assert data["grant_type"] == "client_credentials"
        return _Response({"access_token": "tok-123"})

    captured = {}
    monkeypatch.setattr("providers.art.requests.post", fake_post)
    _patch_get(
        monkeypatch,
        "art",
        {
            "results": [
                {
                    "title": "Neon City",
                    "url": "https://deviantart.test/neon",
                    "author": {"username": "artist1"},
                    "content": {"src": "https://img.test/neon.jpg"},
                }
            ]
        },
        capture=captured,
    )

    content = DeviantArtSource("id", "secret", SeededRng(1)).fetch()

    assert content.title == "Neon City"
    assert content.author == "artist1"
    assert content.url == "https://img.test/neon.jpg"
    assert captured["params"]["access_token"] == "tok-123"


def test_deviantart_raises_without_access_token(monkeypatch):
    monkeypatch.setattr(
        "providers.art.requests.post", lambda *a, **k: _Response({"error": "nope"})
    )
    with pytest.raises(ValueError):
        DeviantArtSource("id", "secret", SeededRng(1)).fetch()


# --- music ---


def test_itunes_parses_track(monkeypatch):
    _patch_get(
        monkeypatch,
        "music",
        {
            "results": [
                {
                    "trackName": "Blue Hour",
                    "artistName": "Someone",
                    "trackViewUrl": "https://itunes.test/t",
                    "collectionName": "Dawn",
                }
            ]
        },
    )

    content = ITunesSource(SeededRng(1)).fetch()

    assert content.kind is GeneratedKind.MUSIC
    assert content.title == "Blue Hour"
    assert content.author == "Someone"
    assert content.url == "https://itunes.test/t"


def test_itunes_raises_on_empty_results(monkeypatch):
    _patch_get(monkeypatch, "music", {"results": []})
    with pytest.raises(ValueError):
        ITunesSource(SeededRng(1)).fetch()


def test_jamendo_parses_track_and_sends_client_id(monkeypatch):
    captured = {}
    _patch_get(
        monkeypatch,
        "music",
        {
            "results": [
                {
                    "name": "Sunrise",
                    "artist_name": "Band",
                    "shareurl": "https://jamendo.test/s",
                    "album_name": "Morning",
                }
            ]
        },
        capture=captured,
    )

    content = JamendoSource("client-abc", SeededRng(1)).fetch()

    assert content.title == "Sunrise"
    assert content.author == "Band"
    assert captured["params"]["client_id"] == "client-abc"


def test_all_sources_use_a_timeout(monkeypatch):
    captured = {}
    _patch_get(monkeypatch, "quotes", [{"q": "x", "a": "y"}], capture=captured)
    ZenQuotesSource().fetch()
    assert captured["timeout"] == 6.0
