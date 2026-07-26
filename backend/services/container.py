from functools import lru_cache

from django.conf import settings

from aiclients.base import AIClient
from aiclients.groq_client import GroqClient
from aiclients.random_client import RandomAIClient
from core.rng import Rng, SystemRng
from providers.base import ContentProvider
from providers.chain import build_content_provider
from repos.factory import RepoBundle, build_repos
from services.context import GameContext
from services.trial import get_trial_store

SESSION_OWNER_KEY = "is_owner"
TRIAL_TOKEN_HEADER = "HTTP_X_TRIAL_TOKEN"


@lru_cache(maxsize=1)
def get_repos() -> RepoBundle:
    """The owner's repositories, per REPO_BACKEND."""
    return build_repos(settings.REPO_BACKEND)


@lru_cache(maxsize=1)
def get_ai_client() -> AIClient:
    if settings.GROQ_API_KEY:
        return GroqClient(api_key=settings.GROQ_API_KEY, model=settings.GROQ_MODEL)
    return RandomAIClient()


@lru_cache(maxsize=1)
def get_rng() -> Rng:
    return SystemRng()


@lru_cache(maxsize=1)
def get_content_provider() -> ContentProvider:
    return build_content_provider(
        rng=get_rng(),
        deviantart_client_id=settings.DEVIANTART_CLIENT_ID,
        deviantart_client_secret=settings.DEVIANTART_CLIENT_SECRET,
        jamendo_client_id=settings.JAMENDO_CLIENT_ID,
    )


def owner_context() -> GameContext:
    """The real game: persistent repositories and the real AI.

    Built fresh each call but from cached collaborators, so the underlying
    state is shared while tests can still swap any single piece.
    """
    return GameContext(
        repos=get_repos(),
        ai=get_ai_client(),
        rng=get_rng(),
        content=get_content_provider(),
        timezone_name=settings.TIME_ZONE,
        is_trial=False,
    )


def context_for(request) -> GameContext | None:
    """Resolve the caller's world, or None if they are not entitled to one.

    An X-Trial-Token header is checked first: it is an explicit, deliberate
    credential, whereas the session cookie is ambient and gets attached to
    every request. If the owner opens a friend link in their own browser, the
    header is what they meant, and letting the cookie win would quietly serve
    the real save behind a "Trial" badge.
    """
    token = request.META.get(TRIAL_TOKEN_HEADER)
    if token:
        session = get_trial_store().get(token)
        if session is not None:
            return session.context
        return None  # a token was offered and it is not valid — do not fall back

    if request.session.get(SESSION_OWNER_KEY):
        return owner_context()
    return None
