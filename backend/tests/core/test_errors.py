import pytest

from core.enums import CollectableRarity, Element
from core.errors import (
    AIResponseInvalid,
    AlreadyExists,
    DiscardAlreadyUsed,
    DomainError,
    InsufficientCoins,
    InsufficientCollectables,
    InvalidMerge,
    MissingKey,
    NotFound,
)


@pytest.mark.parametrize(
    ("exc_cls", "code"),
    [
        (NotFound, "NOT_FOUND"),
        (AlreadyExists, "ALREADY_EXISTS"),
        (InsufficientCoins, "INSUFFICIENT_COINS"),
        (InsufficientCollectables, "INSUFFICIENT_COLLECTABLES"),
        (InvalidMerge, "INVALID_MERGE"),
        (DiscardAlreadyUsed, "DISCARD_USED"),
        (AIResponseInvalid, "AI_INVALID"),
    ],
)
def test_error_subclasses_domain_error_with_correct_code(exc_cls, code):
    assert issubclass(exc_cls, DomainError)
    assert exc_cls.code == code
    err = exc_cls()
    assert isinstance(err, DomainError)
    assert str(err) == code


def test_missing_key_carries_element_and_rarity():
    err = MissingKey(Element.OCEAN, CollectableRarity.ESSENCE)
    assert err.code == "MISSING_KEY"
    assert err.element == Element.OCEAN
    assert err.rarity == CollectableRarity.ESSENCE
    assert "OCEAN" in str(err)
