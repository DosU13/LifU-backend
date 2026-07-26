import logging

from core.entities import GeneratedContent
from core.enums import ReceptacleRarity
from core.rng import Rng
from providers.art import ArtInstituteSource, DeviantArtSource
from providers.base import ContentProvider, ContentSource
from providers.fallback import FallbackContentProvider
from providers.music import ITunesSource, JamendoSource
from providers.quotes import UselessFactsSource, ZenQuotesSource

logger = logging.getLogger(__name__)


class ChainContentProvider:
    """Tries live sources in a shuffled order, then local content.

    Never raises: any source failure (network, timeout, rate limit, malformed
    payload) is logged and the next source is tried, so a treasure buy can
    always complete.
    """

    def __init__(
        self,
        pouch_sources: list[ContentSource],
        sack_sources: list[ContentSource],
        fallback: ContentProvider,
        rng: Rng,
    ) -> None:
        self._pouch_sources = pouch_sources
        self._sack_sources = sack_sources
        self._fallback = fallback
        self._rng = rng

    def fetch(self, rarity: ReceptacleRarity) -> GeneratedContent:
        sources = list(
            self._sack_sources if rarity is ReceptacleRarity.SACK else self._pouch_sources
        )
        # Shuffled rather than ordered so repeated drops vary between sources.
        self._rng.shuffle(sources)

        for source in sources:
            try:
                content = source.fetch()
            except Exception:  # noqa: BLE001 — any failure just means "try the next source"
                logger.warning("content source %s failed", type(source).__name__, exc_info=True)
                continue
            if content.text or content.url:
                return content
            logger.warning("content source %s returned empty content", type(source).__name__)

        return self._fallback.fetch(rarity)


def build_content_provider(
    rng: Rng,
    deviantart_client_id: str = "",
    deviantart_client_secret: str = "",
    jamendo_client_id: str = "",
) -> ChainContentProvider:
    """Assemble the provider chain, including only the sources that can work.

    The key-free sources are always present, so live content works without any
    credentials configured; DeviantArt and Jamendo join in when they are set.
    """
    pouch_sources: list[ContentSource] = [ZenQuotesSource(), UselessFactsSource()]

    sack_sources: list[ContentSource] = [ArtInstituteSource(rng), ITunesSource(rng)]
    if deviantart_client_id and deviantart_client_secret:
        sack_sources.append(
            DeviantArtSource(deviantart_client_id, deviantart_client_secret, rng)
        )
    if jamendo_client_id:
        sack_sources.append(JamendoSource(jamendo_client_id, rng))

    return ChainContentProvider(
        pouch_sources=pouch_sources,
        sack_sources=sack_sources,
        fallback=FallbackContentProvider(rng=rng),
        rng=rng,
    )
