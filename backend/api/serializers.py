from rest_framework import serializers

from core.entities import CollectableStock
from core.enums import CollectableRarity, Element, TaskVirtue


def _stringify_keys(d: dict) -> dict:
    return {key.value: value for key, value in d.items()}


def serialize_stocks(stock: CollectableStock) -> dict[str, int]:
    return {f"{element.value}_{rarity.name}": count for (element, rarity), count in stock.items()}


class TaskCreateRequestSerializer(serializers.Serializer):
    text = serializers.CharField(allow_blank=False, trim_whitespace=True, max_length=4000)


class TaskSerializer(serializers.Serializer):
    """Full task record, as returned by the task history list."""

    id = serializers.CharField()
    text = serializers.CharField()
    created_at = serializers.DateTimeField()
    value = serializers.IntegerField()
    virtues = serializers.SerializerMethodField()
    fragments_awarded = serializers.SerializerMethodField()

    def get_virtues(self, task) -> dict[str, int]:
        return _stringify_keys(task.virtues)

    def get_fragments_awarded(self, task) -> dict[str, int]:
        return _stringify_keys(task.fragments_awarded)


class TaskCompletionResponseSerializer(serializers.Serializer):
    """Response for POST /api/tasks — task carries only value+virtues here."""

    task = serializers.SerializerMethodField()
    fragments_awarded = serializers.SerializerMethodField()

    def get_task(self, task) -> dict:
        return {"value": task.value, "virtues": _stringify_keys(task.virtues)}

    def get_fragments_awarded(self, task) -> dict[str, int]:
        return _stringify_keys(task.fragments_awarded)


class TaskListResponseSerializer(serializers.Serializer):
    tasks = TaskSerializer(many=True)


class StatsResponseSerializer(serializers.Serializer):
    per_day = serializers.DictField(child=serializers.IntegerField())
    virtue_means = serializers.SerializerMethodField()
    streak = serializers.IntegerField()

    def get_virtue_means(self, stats) -> dict[str, float]:
        return {virtue.value: stats.virtue_means[virtue] for virtue in TaskVirtue}


class CollectablesStateResponseSerializer(serializers.Serializer):
    stocks = serializers.DictField(child=serializers.IntegerField())
    coins = serializers.IntegerField()


class MergeRequestSerializer(serializers.Serializer):
    element = serializers.ChoiceField(choices=[e.value for e in Element])
    rarity = serializers.ChoiceField(choices=[r.name for r in CollectableRarity])

    def validate_element(self, value: str) -> Element:
        return Element(value)

    def validate_rarity(self, value: str) -> CollectableRarity:
        return CollectableRarity[value]


class HarmonyRequestSerializer(serializers.Serializer):
    rarity = serializers.ChoiceField(choices=[r.name for r in CollectableRarity])

    def validate_rarity(self, value: str) -> CollectableRarity:
        return CollectableRarity[value]


class CombineRequestSerializer(serializers.Serializer):
    element_a = serializers.ChoiceField(choices=[e.value for e in Element])
    element_b = serializers.ChoiceField(choices=[e.value for e in Element])
    rarity = serializers.ChoiceField(choices=[r.name for r in CollectableRarity])

    def validate_element_a(self, value: str) -> Element:
        return Element(value)

    def validate_element_b(self, value: str) -> Element:
        return Element(value)

    def validate_rarity(self, value: str) -> CollectableRarity:
        return CollectableRarity[value]


class SellRequestSerializer(serializers.Serializer):
    element = serializers.ChoiceField(choices=[e.value for e in Element])
    rarity = serializers.ChoiceField(choices=[r.name for r in CollectableRarity])
    count = serializers.IntegerField(min_value=1)

    def validate_element(self, value: str) -> Element:
        return Element(value)

    def validate_rarity(self, value: str) -> CollectableRarity:
        return CollectableRarity[value]
