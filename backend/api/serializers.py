from rest_framework import serializers

from core.enums import TaskVirtue


def _stringify_keys(d: dict) -> dict:
    return {key.value: value for key, value in d.items()}


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
