"""Trial sandboxes for friend links.

Each trial visitor gets their own in-memory world with a random AI: nothing
touches the real database or Groq, and everything is lost when the token
expires or the process restarts. That is intentional — the trial exists so
friends can try the mechanics, not to keep a save.
"""

import secrets
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from aiclients.random_client import RandomAIClient
from core.entities import Receptacle
from core.enums import (
    BASE_ELEMENTS,
    CollectableRarity,
    ReceptacleRarity,
    ReceptacleState,
    Virtue,
)
from core.rng import Rng, SystemRng
from providers.fallback import FallbackContentProvider
from repos.factory import build_repos
from services.context import GameContext
from services.rarity_service import RarityService

TRIAL_TTL = timedelta(hours=24)

STARTER_COINS = 100
STARTER_FRAGMENTS_PER_ELEMENT = 5
# Varied values so the rarity ratio has something to work with immediately.
STARTER_REWARDS: tuple[tuple[str, int, Virtue], ...] = (
    ("A long walk somewhere new", 15, Virtue.FREEDOM),
    ("Favourite meal, no cooking", 30, Virtue.NURTURING),
    ("An afternoon with no plans at all", 45, Virtue.SERENITY),
    ("That album you keep meaning to hear", 55, Virtue.INSPIRATION),
    ("A day trip you have been putting off", 70, Virtue.VITALITY),
    ("Something you have wanted for months", 85, Virtue.DETERMINATION),
)


@dataclass
class TrialSession:
    token: str
    friend_name: str
    context: GameContext
    expires_at: datetime


def seed_trial_world(context: GameContext) -> None:
    """Give a fresh trial context enough to actually play with."""
    context.repos.wallet.adjust(STARTER_COINS)
    context.repos.collectables.adjust(
        {
            (element, CollectableRarity.FRAGMENT): STARTER_FRAGMENTS_PER_ELEMENT
            for element in BASE_ELEMENTS
        }
    )

    now = datetime.now(timezone.utc)
    for index, (text, value, virtue) in enumerate(STARTER_REWARDS):
        context.repos.receptacles.add(
            Receptacle(
                id="",
                state=ReceptacleState.IN_POOL,
                virtue=virtue,
                rarity=ReceptacleRarity.CHEST,  # placeholder; recalculated below
                value=value,
                is_generated=False,
                is_secret=False,
                friend_name=None,
                reward_text=text,
                content=None,
                treasure_id=None,
                created_at=now + timedelta(seconds=index),
            )
        )
    RarityService(context.repos.receptacles).recalculate()


class TrialStore:
    """Process-local trial sessions, pruned on access."""

    def __init__(self, ttl: timedelta = TRIAL_TTL) -> None:
        self._sessions: dict[str, TrialSession] = {}
        self._ttl = ttl
        self._lock = threading.Lock()

    def create(self, friend_name: str, rng: Rng | None = None) -> TrialSession:
        rng = rng or SystemRng()
        context = GameContext(
            repos=build_repos("memory"),
            ai=RandomAIClient(rng=rng),
            rng=rng,
            content=FallbackContentProvider(rng=rng),
            is_trial=True,
        )
        seed_trial_world(context)

        session = TrialSession(
            token=secrets.token_urlsafe(24),
            friend_name=friend_name,
            context=context,
            expires_at=datetime.now(timezone.utc) + self._ttl,
        )
        with self._lock:
            self._sessions[session.token] = session
        return session

    def get(self, token: str) -> TrialSession | None:
        now = datetime.now(timezone.utc)
        with self._lock:
            expired = [t for t, s in self._sessions.items() if s.expires_at <= now]
            for stale_token in expired:
                del self._sessions[stale_token]
            return self._sessions.get(token)

    def clear(self) -> None:
        with self._lock:
            self._sessions.clear()


_store = TrialStore()


def get_trial_store() -> TrialStore:
    return _store
