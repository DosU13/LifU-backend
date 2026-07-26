from aiclients.prompts import REWARD_CLASSIFIER_SYSTEM, TASK_VALUER_SYSTEM
from core.enums import Virtue
from core.rng import Rng, SystemRng


class RandomAIClient:
    """Trial-mode AI client — no network, returns plausible random values.

    Distinguishes which schema to generate by exact match against the two
    known system prompts (the service layer always calls with one of them).
    """

    def __init__(self, rng: Rng | None = None) -> None:
        self._rng = rng or SystemRng()

    def complete_json(self, system: str, user: str) -> dict:
        if system == TASK_VALUER_SYSTEM:
            return self._random_task()
        if system == REWARD_CLASSIFIER_SYSTEM:
            return self._random_reward()
        raise ValueError("RandomAIClient received an unrecognized system prompt")

    def _random_task(self) -> dict:
        return {
            "Value": self._rng.randint(0, 100),
            "Awareness": self._rng.randint(0, 100),
            "Curiosity": self._rng.randint(0, 100),
            "Willpower": self._rng.randint(0, 100),
            "Compassion": self._rng.randint(0, 100),
            "Discipline": self._rng.randint(0, 100),
        }

    def _random_reward(self) -> dict:
        virtues = list(Virtue)
        self._rng.shuffle(virtues)
        count = self._rng.randint(1, 3)
        chosen = virtues[:count]
        return {
            "Value": self._rng.randint(0, 100),
            "Class": [v.name.title() for v in chosen],
        }
