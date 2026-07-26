"""Art sources for generated Sacks.

DeviantArt needs credentials; the Art Institute of Chicago does not, so there
is always a live art source available. Both pick a random page/offset rather
than a fixed catalogue, so what shows up stays a genuine surprise.
"""

import requests

from core.entities import GeneratedContent
from core.enums import GeneratedKind
from core.rng import Rng
from providers.base import HTTP_TIMEOUT_SECONDS

ARTIC_ARTWORKS_URL = "https://api.artic.edu/api/v1/artworks"
ARTIC_IIIF_TEMPLATE = "https://www.artic.edu/iiif/2/{image_id}/full/843,/0/default.jpg"
ARTIC_PAGE_URL = "https://www.artic.edu/artworks/{artwork_id}"
ARTIC_MAX_PAGE = 400  # the collection runs to tens of thousands of works

DEVIANTART_TOKEN_URL = "https://www.deviantart.com/oauth2/token"
DEVIANTART_TOPIC_URL = "https://www.deviantart.com/api/v1/oauth2/browse/topic"
DEVIANTART_TOPICS = (
    "digital-art",
    "traditional-art",
    "illustration",
    "fantasy",
    "sci-fi",
    "photography",
    "drawings",
)
DEVIANTART_MAX_OFFSET = 120


class ArtInstituteSource:
    """Art Institute of Chicago open API. No key required."""

    def __init__(self, rng: Rng) -> None:
        self._rng = rng

    def fetch(self) -> GeneratedContent:
        response = requests.get(
            ARTIC_ARTWORKS_URL,
            params={
                "page": self._rng.randint(1, ARTIC_MAX_PAGE),
                "limit": 20,
                "fields": "id,title,artist_title,image_id",
            },
            timeout=HTTP_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        candidates = [item for item in response.json().get("data", []) if item.get("image_id")]
        if not candidates:
            raise ValueError("Art Institute returned no artworks with images")

        item = self._rng.choice(candidates)
        return GeneratedContent(
            kind=GeneratedKind.ART,
            title=item.get("title") or "Untitled",
            url=ARTIC_IIIF_TEMPLATE.format(image_id=item["image_id"]),
            author=item.get("artist_title") or "Unknown",
            text=ARTIC_PAGE_URL.format(artwork_id=item.get("id", "")),
        )


class DeviantArtSource:
    """DeviantArt browse API. Requires DEVIANTART_CLIENT_ID/SECRET."""

    def __init__(self, client_id: str, client_secret: str, rng: Rng) -> None:
        self._client_id = client_id
        self._client_secret = client_secret
        self._rng = rng

    def _access_token(self) -> str:
        response = requests.post(
            DEVIANTART_TOKEN_URL,
            data={
                "grant_type": "client_credentials",
                "client_id": self._client_id,
                "client_secret": self._client_secret,
            },
            timeout=HTTP_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        token = response.json().get("access_token")
        if not token:
            raise ValueError("DeviantArt did not return an access token")
        return token

    def fetch(self) -> GeneratedContent:
        response = requests.get(
            DEVIANTART_TOPIC_URL,
            params={
                "topic": self._rng.choice(list(DEVIANTART_TOPICS)),
                "limit": 24,
                "offset": self._rng.randint(0, DEVIANTART_MAX_OFFSET),
                "access_token": self._access_token(),
            },
            timeout=HTTP_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        candidates = [
            item
            for item in response.json().get("results", [])
            if item.get("content", {}).get("src")
        ]
        if not candidates:
            raise ValueError("DeviantArt returned no deviations with images")

        item = self._rng.choice(candidates)
        return GeneratedContent(
            kind=GeneratedKind.ART,
            title=item.get("title") or "Untitled",
            url=item["content"]["src"],
            author=(item.get("author") or {}).get("username") or "Unknown",
            text=item.get("url") or "",
        )
