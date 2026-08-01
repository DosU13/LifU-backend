"""The reward↔receptacle link must stay broken in both directions.

The game only works if opening a receptacle tells you something you did not
already know. That needs two halves and both are load-bearing:

  * a receptacle never reveals its contents until it is opened, and
  * the rewards list never reveals which receptacle a reward went into.

Sealing only one half is worthless: whichever endpoint stays open re-joins the
pair. These tests pin both halves, and are written against the response key
sets rather than their values so a field cannot be quietly reintroduced.
"""

from django.urls import reverse

from core.enums import ReceptacleState

# Anything that describes what is inside a receptacle.
CONTENT_FIELDS = {"reward_text", "value", "content"}

# Anything that identifies which receptacle a reward became.
RECEPTACLE_FIELDS = {"virtue", "rarity", "value", "id", "state", "key_needed"}


def _make_reward(client, text="a weekend in the mountains", **kw):
    response = client.post(reverse("rewards"), {"text": text, **kw}, format="json")
    assert response.status_code == 200, response.content
    return response.json()


def _receptacles(client, state=None):
    url = reverse("receptacles")
    if state:
        url += f"?state={state}"
    response = client.get(url)
    assert response.status_code == 200, response.content
    return response.json()["receptacles"]


# --- half one: a receptacle hides its contents ---


def test_creating_a_reward_never_reveals_the_receptacle_it_became(client):
    """The most direct leak: being told 'that became a Vault of Serenity'."""
    body = _make_reward(client)

    assert RECEPTACLE_FIELDS.isdisjoint(body.keys()), (
        f"POST /api/rewards leaked receptacle fields: "
        f"{RECEPTACLE_FIELDS & body.keys()}"
    )
    assert body["text"] == "a weekend in the mountains"


def test_own_unopened_receptacle_withholds_its_contents(client):
    """Not just secret gifts — a reward you wrote yourself is hidden too.

    Rarity is apportioned by value, so a visible reward beside a visible
    rarity would rank the owner's entire wishlist for them.
    """
    _make_reward(client, text="the expensive running shoes")

    for receptacle in _receptacles(client, state=ReceptacleState.IN_POOL.value):
        assert receptacle["reward_text"] is None
        assert receptacle["value"] is None
        assert receptacle["content"] is None
        # ...while still saying enough to know how to open it.
        assert receptacle["virtue"]
        assert receptacle["rarity"]
        assert receptacle["key_needed"]["element"]


def test_state_endpoint_withholds_contents_too(client):
    """/api/state serves the same receptacles and must not be a way around it."""
    _make_reward(client, text="a day where nothing is scheduled")

    body = client.get(reverse("state")).json()
    for receptacle in body["dropped_receptacles"]:
        assert receptacle["reward_text"] is None
        assert receptacle["value"] is None


def test_secret_gift_stays_hidden_from_the_owner(client):
    """The original rule, still holding under the stricter one."""
    client.post(reverse("friends"), {"name": "alex"}, format="json")
    _make_reward(client, text="something only alex knows", is_secret=True, friend_name="alex")

    for receptacle in _receptacles(client, state=ReceptacleState.IN_POOL.value):
        assert receptacle["reward_text"] is None


# --- half two: a reward hides its receptacle ---


def test_rewards_list_never_carries_receptacle_identity(client):
    _make_reward(client, text="dinner at the impossible place")

    rewards = client.get(reverse("rewards")).json()["rewards"]
    assert rewards, "expected the reward to be listed"

    for reward in rewards:
        leaked = RECEPTACLE_FIELDS & reward.keys()
        assert not leaked, f"rewards list leaked receptacle fields: {leaked}"


def test_rewards_list_shows_the_owner_their_own_text(client):
    """The admin page is where the owner reads what they asked for."""
    _make_reward(client, text="new headphones")

    rewards = client.get(reverse("rewards")).json()["rewards"]
    assert [r["text"] for r in rewards] == ["new headphones"]
    assert rewards[0]["is_secret"] is False
    assert rewards[0]["is_opened"] is False


def test_rewards_list_masks_a_friends_secret_gift(client):
    """The owner did not write it, so they must not read it early."""
    client.post(reverse("friends"), {"name": "sam"}, format="json")
    _make_reward(client, text="a gift from sam", is_secret=True, friend_name="sam")

    rewards = client.get(reverse("rewards")).json()["rewards"]
    assert len(rewards) == 1
    assert rewards[0]["text"] is None
    assert rewards[0]["is_secret"] is True
    assert rewards[0]["friend_name"] == "sam"


def test_generated_receptacles_are_not_rewards(client):
    """Auto-generated pouches hold quotes and facts, not things the owner wants."""
    _make_reward(client, text="a real reward")

    rewards = client.get(reverse("rewards")).json()["rewards"]
    assert all(r["text"] != "" for r in rewards)
    assert len(rewards) == 1


# --- opening is what reveals ---


def test_opening_reveals_the_contents(client, monkeypatch):
    """Everything withheld above has to actually arrive on open."""
    from core.enums import CollectableRarity
    from core.mappings import key_for_receptacle

    _make_reward(client, text="the reward worth waiting for")
    receptacle = _receptacles(client, state=ReceptacleState.IN_POOL.value)[0]

    # Put the matching key in the wallet and move the receptacle to DROPPED,
    # which is the only state open() accepts.
    from services import container

    ctx = container.owner_context()
    stored = ctx.repos.receptacles.get(receptacle["id"])
    stored.state = ReceptacleState.DROPPED
    ctx.repos.receptacles.update(stored)

    element, rarity = key_for_receptacle(stored.virtue, stored.rarity)
    ctx.repos.collectables.adjust({(element, CollectableRarity(rarity)): 1})

    response = client.post(reverse("receptacle-open", args=[stored.id]))
    assert response.status_code == 200, response.content

    opened = response.json()["receptacle"]
    assert opened["reward_text"] == "the reward worth waiting for"
    assert opened["value"] is not None
    assert opened["opened_at"] is not None
