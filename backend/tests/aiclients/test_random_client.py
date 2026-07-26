import pytest

from aiclients.base import AIClient
from aiclients.prompts import REWARD_CLASSIFIER_SYSTEM, TASK_VALUER_SYSTEM
from aiclients.random_client import RandomAIClient
from core.enums import Virtue
from core.rng import SeededRng

_TASK_KEYS = {"Value", "Awareness", "Curiosity", "Willpower", "Compassion", "Discipline"}
_VIRTUE_NAMES = {v.name.title() for v in Virtue}


def test_satisfies_ai_client_protocol():
    assert isinstance(RandomAIClient(), AIClient)


def test_task_prompt_returns_valid_shape_and_range():
    client = RandomAIClient(rng=SeededRng(1))
    for _ in range(50):
        data = client.complete_json(TASK_VALUER_SYSTEM, "did something")
        assert set(data.keys()) == _TASK_KEYS
        for key in _TASK_KEYS:
            assert isinstance(data[key], int)
            assert 0 <= data[key] <= 100


def test_reward_prompt_returns_valid_shape_and_range():
    client = RandomAIClient(rng=SeededRng(2))
    for _ in range(50):
        data = client.complete_json(REWARD_CLASSIFIER_SYSTEM, "a nice surprise")
        assert set(data.keys()) == {"Value", "Class"}
        assert isinstance(data["Value"], int)
        assert 0 <= data["Value"] <= 100
        assert 1 <= len(data["Class"]) <= 3
        assert len(set(data["Class"])) == len(data["Class"])  # no duplicates
        assert all(c in _VIRTUE_NAMES for c in data["Class"])


def test_unrecognized_system_prompt_raises():
    client = RandomAIClient(rng=SeededRng(3))
    with pytest.raises(ValueError):
        client.complete_json("some other prompt", "u")


def test_deterministic_with_same_seed():
    a = RandomAIClient(rng=SeededRng(42))
    b = RandomAIClient(rng=SeededRng(42))
    seq_a = [a.complete_json(TASK_VALUER_SYSTEM, "x") for _ in range(5)]
    seq_b = [b.complete_json(TASK_VALUER_SYSTEM, "x") for _ in range(5)]
    assert seq_a == seq_b
