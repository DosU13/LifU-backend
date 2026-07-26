from django.urls import reverse

from aiclients.fake import FakeAIClient
from services import container


def _valid_task_response(**overrides) -> dict:
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


def _use_fake_ai(monkeypatch, responses):
    fake = FakeAIClient(responses)
    monkeypatch.setattr(container, "get_ai_client", lambda: fake)
    return fake


def test_post_task_happy_path(client, monkeypatch):
    _use_fake_ai(monkeypatch, [_valid_task_response()])

    response = client.post(reverse("tasks"), {"text": "went for a run"}, format="json")

    assert response.status_code == 200
    body = response.json()
    assert body["task"]["value"] == 10
    assert body["task"]["virtues"]["DISCIPLINE"] == 60
    assert "fragments_awarded" in body
    assert isinstance(body["fragments_awarded"], dict)


def test_post_task_missing_text_is_rejected(client, monkeypatch):
    _use_fake_ai(monkeypatch, [])

    response = client.post(reverse("tasks"), {}, format="json")

    assert response.status_code == 400


def test_post_task_ai_failure_returns_502(client, monkeypatch):
    _use_fake_ai(monkeypatch, [{"bad": 1}, {"bad": 1}, {"bad": 1}])

    response = client.post(reverse("tasks"), {"text": "text"}, format="json")

    assert response.status_code == 502
    assert response.json()["error"]["code"] == "AI_INVALID"


def test_get_tasks_lists_completed_tasks(client, monkeypatch):
    _use_fake_ai(monkeypatch, [_valid_task_response(Value=5)])
    client.post(reverse("tasks"), {"text": "did something"}, format="json")

    response = client.get(reverse("tasks"))

    assert response.status_code == 200
    tasks = response.json()["tasks"]
    assert len(tasks) == 1
    assert tasks[0]["text"] == "did something"
    assert tasks[0]["value"] == 5


def test_get_tasks_empty_when_none_completed(client):
    response = client.get(reverse("tasks"))
    assert response.status_code == 200
    assert response.json()["tasks"] == []
