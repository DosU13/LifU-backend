import time
from collections.abc import Callable
from dataclasses import dataclass

from aiclients.base import AIClient
from aiclients.prompts import (
    RETRY_CORRECTIVE_TEMPLATE,
    REWARD_CLASSIFIER_SYSTEM,
    SECRET_GIFT_PREFIX,
    TASK_VALUER_SYSTEM,
)
from core.constants import AI_MAX_RETRIES, SECRET_MIN_VALUE
from core.enums import TaskVirtue, Virtue
from core.errors import AIResponseInvalid

_TASK_KEYS = {"Value", "Awareness", "Curiosity", "Willpower", "Compassion", "Discipline"}
_REWARD_KEYS = {"Value", "Class"}
_VIRTUE_BY_NAME = {v.name: v for v in Virtue}

# Backoff before retrying a transient (network/client) failure — e.g. a rate
# limit — where retrying the identical request has a real chance of working.
_TRANSIENT_RETRY_DELAY_SECONDS = 0.5


def _clamp(n: int) -> int:
    return max(0, min(100, n))


def _is_plain_int(value: object) -> bool:
    # bool is a subclass of int in Python — reject it explicitly.
    return isinstance(value, int) and not isinstance(value, bool)


@dataclass
class TaskValuationResult:
    value: int
    virtues: dict[TaskVirtue, int]


@dataclass
class RewardClassificationResult:
    value: int
    classes: list[Virtue]


def _missing_or_extra_key_reason(data: dict, expected_keys: set[str]) -> str | None:
    missing = expected_keys - set(data.keys())
    if missing:
        return f"missing key {sorted(missing)[0]!r}"
    extra = set(data.keys()) - expected_keys
    if extra:
        return f"unexpected key {sorted(extra)[0]!r}"
    return None


def _validate_task_structure(data: object) -> tuple[dict[str, int] | None, str | None]:
    if not isinstance(data, dict):
        return None, "response was not a JSON object"
    key_reason = _missing_or_extra_key_reason(data, _TASK_KEYS)
    if key_reason:
        return None, key_reason
    fields: dict[str, int] = {}
    for key in _TASK_KEYS:
        value = data[key]
        if not _is_plain_int(value):
            return None, f"{key!r} was not an integer"
        fields[key] = value
    return fields, None


def _validate_reward_structure(data: object) -> tuple[dict | None, str | None]:
    if not isinstance(data, dict):
        return None, "response was not a JSON object"
    key_reason = _missing_or_extra_key_reason(data, _REWARD_KEYS)
    if key_reason:
        return None, key_reason
    value = data["Value"]
    if not _is_plain_int(value):
        return None, "'Value' was not an integer"
    classes = data["Class"]
    if not isinstance(classes, list) or not all(isinstance(c, str) for c in classes):
        return None, "'Class' was not a list of strings"
    return {"Value": value, "Class": classes}, None


def _filter_classes(raw: list[str]) -> list[Virtue]:
    """Filter to the 10-virtue enum, case-insensitive, deduped, truncated to 3."""
    result: list[Virtue] = []
    for name in raw:
        virtue = _VIRTUE_BY_NAME.get(name.strip().upper())
        if virtue is not None and virtue not in result:
            result.append(virtue)
        if len(result) == 3:
            break
    return result


def _call_with_retries(
    ai: AIClient,
    system: str,
    initial_message: str,
    validate: Callable[[object], tuple[dict | None, str | None]],
    label: str,
) -> dict:
    """Call `ai.complete_json`, retrying up to AI_MAX_RETRIES times.

    Two distinct failure modes are handled differently:
    - transient (the client itself raised — network error, rate limit, non-
      JSON text): retried with the ORIGINAL message unchanged, after a short
      backoff, since nothing about the request was actually wrong.
    - structural (the client returned a dict but `validate` rejected its
      shape): retried with a corrective note appended, per ARCHITECTURE §8.

    Returns the validated fields dict, or raises AIResponseInvalid once
    retries are exhausted.
    """
    message = initial_message
    reason = "unknown failure"
    for attempt in range(AI_MAX_RETRIES + 1):
        try:
            data = ai.complete_json(system, message)
        except Exception as exc:  # noqa: BLE001 — any client failure means "try again"
            reason = f"the AI client failed ({exc})"
            if attempt < AI_MAX_RETRIES:
                time.sleep(_TRANSIENT_RETRY_DELAY_SECONDS)
            continue

        fields, structural_reason = validate(data)
        if fields is not None:
            return fields
        reason = structural_reason
        message = f"{initial_message}\n\n{RETRY_CORRECTIVE_TEMPLATE.format(reason=reason)}"

    raise AIResponseInvalid(f"{label} returned invalid output after retries: {reason}")


def get_task_valuation(ai: AIClient, task_text: str) -> TaskValuationResult:
    """Call the Task Valuer AI and return a validated, clamped result."""
    fields = _call_with_retries(
        ai, TASK_VALUER_SYSTEM, task_text, _validate_task_structure, "Task Valuer"
    )
    return TaskValuationResult(
        value=_clamp(fields["Value"]),
        virtues={
            TaskVirtue.AWARENESS: _clamp(fields["Awareness"]),
            TaskVirtue.CURIOSITY: _clamp(fields["Curiosity"]),
            TaskVirtue.WILLPOWER: _clamp(fields["Willpower"]),
            TaskVirtue.COMPASSION: _clamp(fields["Compassion"]),
            TaskVirtue.DISCIPLINE: _clamp(fields["Discipline"]),
        },
    )


def get_reward_classification(
    ai: AIClient, reward_text: str, is_secret: bool
) -> RewardClassificationResult:
    """Call the Reward Classifier AI and return a validated, clamped result.

    Secret gifts are floored to SECRET_MIN_VALUE — that adjustment never
    triggers a retry.
    """
    base_message = f"{SECRET_GIFT_PREFIX}{reward_text}" if is_secret else reward_text

    def _validate_with_class_filter(data: object) -> tuple[dict | None, str | None]:
        fields, reason = _validate_reward_structure(data)
        if fields is None:
            return None, reason
        classes = _filter_classes(fields["Class"])
        if not classes:
            return None, "'Class' contained no allowed words"
        return {"Value": fields["Value"], "Class": classes}, None

    fields = _call_with_retries(
        ai, REWARD_CLASSIFIER_SYSTEM, base_message, _validate_with_class_filter, "Reward Classifier"
    )
    value = _clamp(fields["Value"])
    if is_secret and value <= 50:
        value = SECRET_MIN_VALUE
    return RewardClassificationResult(value=value, classes=fields["Class"])
