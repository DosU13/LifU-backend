"""Live calibration tests against the real Groq API — see docs/AI_PROMPTS.md §4-5.

Skipped entirely unless GROQ_API_KEY is set. These check the *prompts* land in
sane ranges on a real model; the validation pipeline itself is fully covered
offline in test_validation.py with FakeAIClient.
"""

import os

import pytest

from aiclients.groq_client import GroqClient
from aiclients.validation import get_reward_classification, get_task_valuation
from core.enums import TaskVirtue, Virtue

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")

pytestmark = [
    pytest.mark.groq,
    pytest.mark.skipif(
        not GROQ_API_KEY, reason="GROQ_API_KEY not set — skipping live AI calibration"
    ),
]


@pytest.fixture(scope="module")
def client():
    return GroqClient(api_key=GROQ_API_KEY, model=GROQ_MODEL)


@pytest.mark.parametrize(
    ("text", "value_range", "high_virtue", "high_range"),
    [
        ("Took out the trash", (1, 5), TaskVirtue.DISCIPLINE, (10, 60)),
        (
            "Went for a 10km run even though it was raining",
            (8, 25),
            TaskVirtue.WILLPOWER,
            (55, 100),
        ),
        (
            "Finished writing the last chapter of my thesis after two weeks of daily work",
            (55, 95),
            TaskVirtue.DISCIPLINE,
            (55, 100),
        ),
        ("Meditated for 20 minutes this morning", (4, 18), TaskVirtue.AWARENESS, (65, 100)),
        (
            "Called my grandma and helped her buy groceries for the week",
            (5, 25),
            TaskVirtue.COMPASSION,
            (65, 100),
        ),
    ],
)
def test_task_valuer_calibration(client, text, value_range, high_virtue, high_range):
    result = get_task_valuation(client, text)
    assert value_range[0] <= result.value <= value_range[1]
    assert high_range[0] <= result.virtues[high_virtue] <= high_range[1]


def test_task_valuer_nonsense_input_scores_near_zero(client):
    result = get_task_valuation(client, "asdf jkl")
    assert result.value <= 2


@pytest.mark.parametrize(
    ("text", "is_secret", "value_range", "allowed_classes"),
    [
        (
            "A motivational quote about persistence",
            False,
            (1, 8),
            {Virtue.INSPIRATION, Virtue.DETERMINATION, Virtue.REFLECTION},
        ),
        (
            "Movie night with popcorn and no phone",
            False,
            (8, 30),
            {Virtue.SERENITY, Virtue.PRESENCE, Virtue.FREEDOM, Virtue.VITALITY},
        ),
        (
            "I promise a lunch by me if you open this chest",
            True,
            (60, 95),
            {Virtue.NURTURING, Virtue.SERENITY, Virtue.VITALITY, Virtue.INSPIRATION},
        ),
        (
            "Just a little motivational message for you!",
            True,
            (51, 75),
            {Virtue.INSPIRATION, Virtue.NURTURING, Virtue.REFLECTION},
        ),
        (
            "Finally buy myself that hiking backpack I've been eyeing for months",
            False,
            (25, 60),
            {Virtue.FREEDOM, Virtue.VITALITY, Virtue.DETERMINATION, Virtue.INSPIRATION},
        ),
    ],
)
def test_reward_classifier_calibration(client, text, is_secret, value_range, allowed_classes):
    result = get_reward_classification(client, text, is_secret=is_secret)
    assert value_range[0] <= result.value <= value_range[1]
    assert 1 <= len(result.classes) <= 3
    assert set(result.classes) & allowed_classes
