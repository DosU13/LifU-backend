"""Music sources for generated Sacks.

Jamendo needs a client id; the iTunes Search API does not, so there is always
a live music source available.
"""

import requests

from core.entities import GeneratedContent
from core.enums import GeneratedKind
from core.rng import Rng
from providers.base import HTTP_TIMEOUT_SECONDS

JAMENDO_TRACKS_URL = "https://api.jamendo.com/v3.0/tracks/"
JAMENDO_MAX_OFFSET = 600

ITUNES_SEARCH_URL = "https://itunes.apple.com/search"
# Broad genres only — the specific track stays the surprise.
ITUNES_TERMS = (
    "ambient",
    "jazz",
    "lo-fi",
    "classical",
    "folk",
    "electronic",
    "post-rock",
    "soul",
    "piano",
    "synthwave",
)


class JamendoSource:
    """Free/creative-commons music. Requires JAMENDO_CLIENT_ID."""

    def __init__(self, client_id: str, rng: Rng) -> None:
        self._client_id = client_id
        self._rng = rng

    def fetch(self) -> GeneratedContent:
        response = requests.get(
            JAMENDO_TRACKS_URL,
            params={
                "client_id": self._client_id,
                "format": "json",
                "limit": 20,
                "offset": self._rng.randint(0, JAMENDO_MAX_OFFSET),
                "order": "popularity_total",
            },
            timeout=HTTP_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        candidates = [track for track in response.json().get("results", []) if track.get("name")]
        if not candidates:
            raise ValueError("Jamendo returned no tracks")

        track = self._rng.choice(candidates)
        return GeneratedContent(
            kind=GeneratedKind.MUSIC,
            title=track.get("name") or "Untitled",
            url=track.get("shareurl") or track.get("audio") or "",
            author=track.get("artist_name") or "Unknown",
            text=track.get("album_name") or "",
        )


class ITunesSource:
    """iTunes Search API. No key required."""

    def __init__(self, rng: Rng) -> None:
        self._rng = rng

    def fetch(self) -> GeneratedContent:
        response = requests.get(
            ITUNES_SEARCH_URL,
            params={
                "term": self._rng.choice(list(ITUNES_TERMS)),
                "media": "music",
                "limit": 50,
            },
            timeout=HTTP_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        candidates = [
            track for track in response.json().get("results", []) if track.get("trackName")
        ]
        if not candidates:
            raise ValueError("iTunes returned no tracks")

        track = self._rng.choice(candidates)
        return GeneratedContent(
            kind=GeneratedKind.MUSIC,
            title=track["trackName"],
            url=track.get("trackViewUrl") or track.get("previewUrl") or "",
            author=track.get("artistName") or "Unknown",
            text=track.get("collectionName") or "",
        )
