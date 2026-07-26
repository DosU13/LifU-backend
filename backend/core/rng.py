import random
from collections.abc import Sequence
from typing import Protocol, TypeVar, runtime_checkable

T = TypeVar("T")


@runtime_checkable
class Rng(Protocol):
    """All randomness in services goes through this — never call `random` directly."""

    def random(self) -> float: ...

    def randint(self, a: int, b: int) -> int: ...

    def choice(self, seq: Sequence[T]) -> T: ...

    def shuffle(self, seq: list) -> None: ...


class SystemRng:
    """Production Rng, backed by a fresh, unseeded random.Random."""

    def __init__(self) -> None:
        self._random = random.Random()

    def random(self) -> float:
        return self._random.random()

    def randint(self, a: int, b: int) -> int:
        return self._random.randint(a, b)

    def choice(self, seq: Sequence[T]) -> T:
        return self._random.choice(seq)

    def shuffle(self, seq: list) -> None:
        self._random.shuffle(seq)


class SeededRng(SystemRng):
    """Deterministic Rng for tests — same seed always yields the same sequence."""

    def __init__(self, seed: int) -> None:
        self._random = random.Random(seed)
