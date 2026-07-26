from typing import Protocol, runtime_checkable

from core.entities import GeneratedContent
from core.enums import ReceptacleRarity


@runtime_checkable
class ContentProvider(Protocol):
    def fetch(self, rarity: ReceptacleRarity) -> GeneratedContent:
        """Content for a generated receptacle: a quote/fact for a Pouch, a

        music/art discovery for a Sack. Implementations must never raise —
        a provider failure has to degrade to local content rather than break
        a treasure buy.
        """
        ...
