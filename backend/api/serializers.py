from rest_framework import serializers

from core.entities import CollectableStock, Receptacle
from core.enums import CollectableRarity, Element, ReceptacleState, TaskVirtue
from core.mappings import key_for_receptacle

# Shared choice sets. Named once so the generated OpenAPI schema reuses a
# single ElementEnum rather than inventing ElementBEnum for each field.
ELEMENT_CHOICES = [(e.value, e.value) for e in Element]
COLLECTABLE_RARITY_CHOICES = [(r.name, r.name) for r in CollectableRarity]


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
    element = serializers.ChoiceField(choices=ELEMENT_CHOICES)
    rarity = serializers.ChoiceField(choices=COLLECTABLE_RARITY_CHOICES)

    def validate_element(self, value: str) -> Element:
        return Element(value)

    def validate_rarity(self, value: str) -> CollectableRarity:
        return CollectableRarity[value]


class HarmonyRequestSerializer(serializers.Serializer):
    rarity = serializers.ChoiceField(choices=COLLECTABLE_RARITY_CHOICES)

    def validate_rarity(self, value: str) -> CollectableRarity:
        return CollectableRarity[value]


class CombineRequestSerializer(serializers.Serializer):
    element_a = serializers.ChoiceField(choices=ELEMENT_CHOICES)
    element_b = serializers.ChoiceField(choices=ELEMENT_CHOICES)
    rarity = serializers.ChoiceField(choices=COLLECTABLE_RARITY_CHOICES)

    def validate_element_a(self, value: str) -> Element:
        return Element(value)

    def validate_element_b(self, value: str) -> Element:
        return Element(value)

    def validate_rarity(self, value: str) -> CollectableRarity:
        return CollectableRarity[value]


class SellRequestSerializer(serializers.Serializer):
    element = serializers.ChoiceField(choices=ELEMENT_CHOICES)
    rarity = serializers.ChoiceField(choices=COLLECTABLE_RARITY_CHOICES)
    count = serializers.IntegerField(min_value=1)

    def validate_element(self, value: str) -> Element:
        return Element(value)

    def validate_rarity(self, value: str) -> CollectableRarity:
        return CollectableRarity[value]


class RewardCreateRequestSerializer(serializers.Serializer):
    text = serializers.CharField(allow_blank=False, trim_whitespace=True, max_length=4000)
    is_secret = serializers.BooleanField(default=False)
    friend_name = serializers.CharField(required=False, allow_null=True, max_length=100)


def _serialize_content(content) -> dict | None:
    if content is None:
        return None
    return {
        "kind": content.kind.value,
        "title": content.title,
        "url": content.url,
        "author": content.author,
        "text": content.text,
    }


def serialize_receptacle(receptacle: Receptacle) -> dict:
    """Serialize a receptacle for the API.

    Privacy rule (ARCHITECTURE §2): an unopened receptacle reveals only what is
    needed to open it — its virtue, its rarity and therefore its key — and
    nothing whatsoever about what is inside.

    This is stricter than withholding secret gifts alone. Rewards the owner
    wrote themselves must be withheld too, because rarity is recalculated by
    value: pairing a visible reward with a visible rarity would rank every
    reward they own, and there would be nothing left to find out on opening.
    The admin page is the mirror of this — see `serialize_reward`, which shows
    the text and hides the receptacle.
    """
    is_opened = receptacle.state is ReceptacleState.OPENED
    key_element, key_rarity = key_for_receptacle(receptacle.virtue, receptacle.rarity)

    return {
        "id": receptacle.id,
        "state": receptacle.state.value,
        "virtue": receptacle.virtue.value,
        "rarity": receptacle.rarity.name,
        "is_generated": receptacle.is_generated,
        "is_secret": receptacle.is_secret,
        "friend_name": receptacle.friend_name,
        "created_at": receptacle.created_at,
        "opened_at": receptacle.opened_at,
        "key_needed": {"element": key_element.value, "rarity": key_rarity.name},
        # Everything below describes the contents, so it appears only once the
        # receptacle has been opened.
        "value": receptacle.value if is_opened else None,
        "reward_text": receptacle.reward_text if is_opened else None,
        "content": _serialize_content(receptacle.content) if is_opened else None,
    }


def serialize_reward(receptacle: Receptacle) -> dict:
    """A reward as its author sees it on the admin page.

    Carries no virtue, rarity, value or receptacle id on purpose: which
    receptacle a reward was sealed into is exactly the thing that has to stay
    hidden, and since rarity is apportioned by value, exposing it would rank
    the owner's whole wishlist for them.

    A friend's secret gift still withholds its text here — the owner did not
    write it and must not read it before opening.
    """
    is_opened = receptacle.state is ReceptacleState.OPENED
    hide_text = receptacle.is_secret and not is_opened
    return {
        "text": None if hide_text else receptacle.reward_text,
        "is_secret": receptacle.is_secret,
        "friend_name": receptacle.friend_name,
        "created_at": receptacle.created_at,
        "is_opened": is_opened,
    }


# --- response schemas (documentation for /api/docs) ---
# These describe what the views return. The views build plain dicts, so these
# are not used to serialise — they exist so drf-spectacular documents real
# shapes instead of a bare object.


class ErrorBodySerializer(serializers.Serializer):
    code = serializers.CharField()
    message = serializers.CharField()


class ErrorResponseSerializer(serializers.Serializer):
    error = ErrorBodySerializer()


class KeyRequirementSerializer(serializers.Serializer):
    element = serializers.ChoiceField(choices=ELEMENT_CHOICES)
    rarity = serializers.ChoiceField(choices=COLLECTABLE_RARITY_CHOICES)


class GeneratedContentSerializer(serializers.Serializer):
    kind = serializers.CharField()
    title = serializers.CharField()
    url = serializers.CharField()
    author = serializers.CharField()
    text = serializers.CharField()


class ReceptacleResponseSerializer(serializers.Serializer):
    id = serializers.CharField()
    state = serializers.CharField()
    virtue = serializers.CharField()
    rarity = serializers.CharField()
    is_generated = serializers.BooleanField()
    is_secret = serializers.BooleanField()
    friend_name = serializers.CharField(allow_null=True)
    created_at = serializers.DateTimeField()
    opened_at = serializers.DateTimeField(allow_null=True)
    key_needed = KeyRequirementSerializer()
    value = serializers.IntegerField(
        allow_null=True, help_text="Null until opened — it describes the contents."
    )
    reward_text = serializers.CharField(
        allow_null=True, help_text="Null until opened. The whole point is not knowing."
    )
    content = GeneratedContentSerializer(
        required=False, allow_null=True, help_text="Generated contents; null until opened."
    )


class RewardResponseSerializer(serializers.Serializer):
    """A reward on the admin page. Deliberately says nothing about receptacles."""

    text = serializers.CharField(
        allow_null=True, help_text="Null for a friend's secret gift until it is opened."
    )
    is_secret = serializers.BooleanField()
    friend_name = serializers.CharField(allow_null=True)
    created_at = serializers.DateTimeField()
    is_opened = serializers.BooleanField()


class RewardListResponseSerializer(serializers.Serializer):
    rewards = RewardResponseSerializer(many=True)


class ReceptacleListResponseSerializer(serializers.Serializer):
    receptacles = ReceptacleResponseSerializer(many=True)


class StocksResponseSerializer(serializers.Serializer):
    stocks = serializers.DictField(
        child=serializers.IntegerField(),
        help_text='All 96 counters, keyed "ELEMENT_RARITY" (e.g. "FIRE_SHARD").',
    )


class SellResponseSerializer(StocksResponseSerializer):
    coins = serializers.IntegerField()


class HarmonyResponseSerializer(StocksResponseSerializer):
    yield_ = serializers.IntegerField(
        source="yield", help_text="Total harmony produced: 5 plus the extras rolled."
    )
    extras = serializers.IntegerField(
        help_text="How many times the build-up succeeded. Replay this many extra bursts."
    )


class CombineResponseSerializer(StocksResponseSerializer):
    result_element = serializers.CharField()


class TreasureContentSerializer(serializers.Serializer):
    virtue = serializers.CharField()
    rarity = serializers.CharField()
    is_secret = serializers.BooleanField()
    friend_name = serializers.CharField(allow_null=True)


class TreasureSerializer(serializers.Serializer):
    id = serializers.CharField()
    slot = serializers.IntegerField()
    price = serializers.IntegerField(help_text="Fixed when the treasure was generated.")
    pity = serializers.DictField(child=serializers.IntegerField())
    contents = TreasureContentSerializer(
        many=True, help_text="Deliberately omits value and reward text."
    )


class TreasureListResponseSerializer(serializers.Serializer):
    treasures = TreasureSerializer(many=True)


class TreasureBuyResponseSerializer(serializers.Serializer):
    drop = ReceptacleResponseSerializer()
    dropped_rarity = serializers.CharField(
        help_text="The rarity actually won. Recalculation may relabel the receptacle afterwards."
    )
    was_pity = serializers.BooleanField()
    price_paid = serializers.IntegerField()
    coins = serializers.IntegerField()
    pity = serializers.DictField(child=serializers.IntegerField())
    treasure_gone = serializers.BooleanField()


class TreasureDiscardResponseSerializer(serializers.Serializer):
    new_treasure = TreasureSerializer(allow_null=True)


class ReceptacleOpenResponseSerializer(serializers.Serializer):
    receptacle = ReceptacleResponseSerializer()
    coins_gained = serializers.IntegerField()
    coins = serializers.IntegerField()


class StateResponseSerializer(serializers.Serializer):
    coins = serializers.IntegerField()
    stocks = serializers.DictField(child=serializers.IntegerField())
    treasures = TreasureSerializer(many=True)
    dropped_receptacles = ReceptacleResponseSerializer(many=True)
    stats = StatsResponseSerializer()


class FriendLinkSerializer(serializers.Serializer):
    name = serializers.CharField()
    url = serializers.CharField()


class FriendLinkListResponseSerializer(serializers.Serializer):
    friends = FriendLinkSerializer(many=True)


class PublicFriendResponseSerializer(serializers.Serializer):
    valid = serializers.BooleanField()
    name = serializers.CharField()


class TrialSessionResponseSerializer(serializers.Serializer):
    token = serializers.CharField(help_text="Send as the X-Trial-Token header.")
    friend_name = serializers.CharField()
    expires_at = serializers.DateTimeField()


class OkResponseSerializer(serializers.Serializer):
    ok = serializers.BooleanField()


class SessionResponseSerializer(serializers.Serializer):
    authenticated = serializers.BooleanField()
    is_trial = serializers.BooleanField()
