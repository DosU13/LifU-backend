from django.urls import reverse
from rest_framework.test import APIClient

from aiclients.fake import FakeAIClient
from services import container


def test_stats_empty_initially():
    client = APIClient()
    response = client.get(reverse("stats"))

    assert response.status_code == 200
    body = response.json()
    assert body["per_day"] == {}
    assert body["streak"] == 0
    assert all(v == 0.0 for v in body["virtue_means"].values())


def test_stats_reflect_a_completed_task(monkeypatch):
    fake = FakeAIClient(
        [
            {
                "Value": 10,
                "Awareness": 20,
                "Curiosity": 30,
                "Willpower": 40,
                "Compassion": 50,
                "Discipline": 60,
            }
        ]
    )
    monkeypatch.setattr(container, "get_ai_client", lambda: fake)
    client = APIClient()
    client.post(reverse("tasks"), {"text": "did something"}, format="json")

    response = client.get(reverse("stats"))

    assert response.status_code == 200
    body = response.json()
    assert sum(body["per_day"].values()) == 1
    assert body["streak"] == 1
    assert body["virtue_means"]["DISCIPLINE"] == 60.0
