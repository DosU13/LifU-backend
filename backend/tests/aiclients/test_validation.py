import json

import pytest

from aiclients.fake import FakeAIClient
from aiclients.validation import (
    RewardClassificationResult,
    TaskValuationResult,
    get_reward_classification,
    get_task_valuation,
)
from core.constants import AI_MAX_RETRIES, SECRET_MIN_VALUE
from core.enums import TaskVirtue, Virtue
from core.errors import AIResponseInvalid


def _valid_task(**overrides) -> dict:
    data = {
        "Value": 10,
        "Awareness": 20,
        "Curiosity": 30,
        "Willpower": 40,
        "Compassion": 50,
        "Discipline": 60,
    }
    data.update(overrides)
    return data


def _valid_reward(**overrides) -> dict:
    data = {"Value": 20, "Class": ["Serenity"]}
    data.update(overrides)
    return data


# --- Task Valuer: happy path ---


def test_valid_task_response_passes_through():
    ai = FakeAIClient([_valid_task()])
    result = get_task_valuation(ai, "went for a run")
    assert result == TaskValuationResult(
        value=10,
        virtues={
            TaskVirtue.AWARENESS: 20,
            TaskVirtue.CURIOSITY: 30,
            TaskVirtue.WILLPOWER: 40,
            TaskVirtue.COMPASSION: 50,
            TaskVirtue.DISCIPLINE: 60,
        },
    )
    assert len(ai.calls) == 1


def test_task_out_of_range_values_are_clamped_without_retry():
    ai = FakeAIClient([_valid_task(Value=150, Awareness=-20)])
    result = get_task_valuation(ai, "text")
    assert result.value == 100
    assert result.virtues[TaskVirtue.AWARENESS] == 0
    assert len(ai.calls) == 1  # clamping must not trigger a retry


@pytest.mark.parametrize(
    "bad_response",
    [
        {"Value": 10, "Awareness": 20, "Curiosity": 30, "Willpower": 40, "Compassion": 50},
        {**_valid_task(), "Discipline": "high"},
        {**_valid_task(), "Discipline": True},
        "not a dict",
    ],
    ids=["missing_key", "bad_type_string", "bad_type_bool", "not_a_dict"],
)
def test_task_structural_failure_retries_then_recovers(bad_response):
    ai = FakeAIClient([bad_response, _valid_task()])
    result = get_task_valuation(ai, "text")
    assert result.value == 10
    assert len(ai.calls) == 2
    # the retry message must include a corrective instruction
    assert "invalid" in ai.calls[1][1].lower()


def test_task_unparseable_json_retries_then_recovers():
    ai = FakeAIClient([json.JSONDecodeError("bad", "doc", 0), _valid_task()])
    result = get_task_valuation(ai, "text")
    assert result.value == 10
    assert len(ai.calls) == 2


def test_task_transient_failure_retries_with_unchanged_message():
    """A network/client-level failure (e.g. a rate limit) isn't the model's fault —

    retry with the exact same message, not a "your JSON was invalid" correction.
    """
    ai = FakeAIClient([RuntimeError("429 rate limited"), _valid_task()])
    result = get_task_valuation(ai, "original task text")
    assert result.value == 10
    assert len(ai.calls) == 2
    assert ai.calls[1][1] == "original task text"


def test_task_structural_failure_exhausts_retries_and_raises():
    ai = FakeAIClient([{"bad": 1}] * (AI_MAX_RETRIES + 1))
    with pytest.raises(AIResponseInvalid):
        get_task_valuation(ai, "text")
    assert len(ai.calls) == AI_MAX_RETRIES + 1


# --- Reward Classifier: happy path ---


def test_valid_reward_response_passes_through():
    ai = FakeAIClient([_valid_reward(Value=20, Class=["Serenity"])])
    result = get_reward_classification(ai, "a quiet evening", is_secret=False)
    assert result == RewardClassificationResult(value=20, classes=[Virtue.SERENITY])
    assert len(ai.calls) == 1


def test_reward_value_clamped_without_retry():
    ai = FakeAIClient([_valid_reward(Value=500)])
    result = get_reward_classification(ai, "text", is_secret=False)
    assert result.value == 100
    assert len(ai.calls) == 1


def test_reward_class_filtered_deduped_and_truncated_to_3():
    ai = FakeAIClient(
        [
            _valid_reward(
                Class=[
                    "Nurturing",
                    "nurturing",  # duplicate, case-insensitive
                    "Bogus",  # not an allowed word
                    "Serenity",
                    "Determination",
                    "Freedom",  # would be 4th valid entry — dropped by truncation
                ]
            )
        ]
    )
    result = get_reward_classification(ai, "text", is_secret=False)
    assert result.classes == [Virtue.NURTURING, Virtue.SERENITY, Virtue.DETERMINATION]
    assert len(ai.calls) == 1


def test_reward_empty_class_after_filtering_retries_then_recovers():
    ai = FakeAIClient([_valid_reward(Class=["Bogus", "AlsoBogus"]), _valid_reward()])
    result = get_reward_classification(ai, "text", is_secret=False)
    assert result.classes == [Virtue.SERENITY]
    assert len(ai.calls) == 2


@pytest.mark.parametrize(
    "bad_response",
    [
        {"Value": 20},
        {**_valid_reward(), "Value": "high"},
        {**_valid_reward(), "Class": "Serenity"},
        {**_valid_reward(), "Class": [1, 2]},
    ],
    ids=["missing_key", "bad_value_type", "class_not_list", "class_not_strings"],
)
def test_reward_structural_failure_retries_then_recovers(bad_response):
    ai = FakeAIClient([bad_response, _valid_reward()])
    result = get_reward_classification(ai, "text", is_secret=False)
    assert result.classes == [Virtue.SERENITY]
    assert len(ai.calls) == 2


def test_reward_transient_failure_retries_with_unchanged_message():
    ai = FakeAIClient([RuntimeError("429 rate limited"), _valid_reward()])
    result = get_reward_classification(ai, "original reward text", is_secret=False)
    assert result.classes == [Virtue.SERENITY]
    assert len(ai.calls) == 2
    assert ai.calls[1][1] == "original reward text"


def test_reward_structural_failure_exhausts_retries_and_raises():
    ai = FakeAIClient([{"bad": 1}] * (AI_MAX_RETRIES + 1))
    with pytest.raises(AIResponseInvalid):
        get_reward_classification(ai, "text", is_secret=False)
    assert len(ai.calls) == AI_MAX_RETRIES + 1


# --- Secret gift value floor ---


def test_secret_gift_low_value_is_forced_to_secret_minimum():
    ai = FakeAIClient([_valid_reward(Value=5)])
    result = get_reward_classification(ai, "just a nice note", is_secret=True)
    assert result.value == SECRET_MIN_VALUE
    assert len(ai.calls) == 1  # forcing the floor must not trigger a retry


def test_secret_gift_already_above_floor_is_untouched():
    ai = FakeAIClient([_valid_reward(Value=85)])
    result = get_reward_classification(ai, "a secret lunch", is_secret=True)
    assert result.value == 85


def test_secret_gift_wraps_user_message_with_prefix():
    ai = FakeAIClient([_valid_reward()])
    get_reward_classification(ai, "surprise!", is_secret=True)
    assert ai.calls[0][1] == "[SECRET GIFT FROM A FRIEND]\nsurprise!"


def test_non_secret_reward_does_not_wrap_message():
    ai = FakeAIClient([_valid_reward()])
    get_reward_classification(ai, "surprise!", is_secret=False)
    assert ai.calls[0][1] == "surprise!"
