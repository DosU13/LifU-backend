from core.enums import CollectableRarity, Element


class DomainError(Exception):
    """Base for all game-rule violations. `code` matches the API error envelope."""

    code = "DOMAIN_ERROR"

    def __init__(self, message: str | None = None):
        super().__init__(message or self.code)


class NotFound(DomainError):
    code = "NOT_FOUND"


class AlreadyExists(DomainError):
    code = "ALREADY_EXISTS"


class InsufficientCoins(DomainError):
    code = "INSUFFICIENT_COINS"


class InsufficientCollectables(DomainError):
    code = "INSUFFICIENT_COLLECTABLES"


class InvalidMerge(DomainError):
    code = "INVALID_MERGE"


class MissingKey(DomainError):
    code = "MISSING_KEY"

    def __init__(self, element: Element, rarity: CollectableRarity):
        self.element = element
        self.rarity = rarity
        super().__init__(f"missing key: one {element.value} {rarity.name} required")


class DiscardAlreadyUsed(DomainError):
    code = "DISCARD_USED"


class AIResponseInvalid(DomainError):
    code = "AI_INVALID"
