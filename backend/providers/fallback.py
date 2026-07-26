"""Local content, used when live providers fail or are not configured.

Deliberately small and generic — the real surprise comes from the live
providers in Phase 10. Kept short so it never becomes the primary source.
"""

from core.entities import GeneratedContent
from core.enums import GeneratedKind, ReceptacleRarity
from core.rng import Rng, SystemRng

QUOTES: list[tuple[str, str]] = [
    ("Small steps every day still cross the mountain.", "Unknown"),
    ("You do not rise to the level of your goals; you fall to your systems.", "Unknown"),
    ("The obstacle is the way.", "Marcus Aurelius"),
    ("What you do every day matters more than what you do once in a while.", "Unknown"),
    ("Begin again, as many times as it takes.", "Unknown"),
]

FACTS: list[str] = [
    "Octopuses have three hearts, and two of them stop beating when they swim.",
    "Honey never spoils — edible jars have been found in ancient tombs.",
    "A day on Venus is longer than a year on Venus.",
    "Bananas are berries, but strawberries are not.",
    "The Eiffel Tower can be about 15 cm taller in summer as the iron expands.",
]


class FallbackContentProvider:
    """Never fails, never hits the network."""

    def __init__(self, rng: Rng | None = None) -> None:
        self._rng = rng or SystemRng()

    def fetch(self, rarity: ReceptacleRarity) -> GeneratedContent:
        if rarity is ReceptacleRarity.SACK:
            return self._discovery()
        return self._quote_or_fact()

    def _quote_or_fact(self) -> GeneratedContent:
        if self._rng.random() < 0.5:
            text, author = self._rng.choice(QUOTES)
            return GeneratedContent(
                kind=GeneratedKind.QUOTE, title="A thought", url="", author=author, text=text
            )
        return GeneratedContent(
            kind=GeneratedKind.FACT,
            title="Did you know?",
            url="",
            author="",
            text=self._rng.choice(FACTS),
        )

    def _discovery(self) -> GeneratedContent:
        # Placeholder discovery until the live music/art providers land (Phase 10).
        text, author = self._rng.choice(QUOTES)
        return GeneratedContent(
            kind=GeneratedKind.QUOTE, title="A thought", url="", author=author, text=text
        )
