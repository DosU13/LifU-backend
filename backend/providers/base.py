from typing import Protocol, runtime_checkable

from core.entities import GeneratedContent
from core.enums import ReceptacleRarity

# Every outbound HTTP call in this package uses this timeout. A slow provider
# must never hold up a treasure buy.
HTTP_TIMEOUT_SECONDS = 6.0


@runtime_checkable
class ContentProvider(Protocol):
    def fetch(self, rarity: ReceptacleRarity) -> GeneratedContent:
        """Content for a generated receptacle: a quote/fact for a Pouch, a

        music/art discovery for a Sack. Implementations must never raise —
        a provider failure has to degrade to local content rather than break
        a treasure buy.
        """
        ...


@runtime_checkable
class ContentSource(Protocol):
    """A single upstream (one API). Unlike ContentProvider, this MAY raise —

    the chain in providers/chain.py catches and moves on to the next source.
    """

    def fetch(self) -> GeneratedContent: ...
