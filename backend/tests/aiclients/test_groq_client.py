import json

import pytest

from aiclients.groq_client import GROQ_API_URL, GroqClient


class _FakeResponse:
    def __init__(self, payload: dict, status_code: int = 200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        return self._payload


def test_complete_json_sends_expected_request_and_parses_content(monkeypatch):
    captured = {}

    def fake_post(url, headers=None, json=None, timeout=None):  # noqa: A002
        captured.update(url=url, headers=headers, json=json, timeout=timeout)
        content = '{"Value": 10, "Awareness": 5}'
        return _FakeResponse({"choices": [{"message": {"content": content}}]})

    monkeypatch.setattr("aiclients.groq_client.requests.post", fake_post)

    client = GroqClient(api_key="test-key", model="test-model")
    result = client.complete_json("SYSTEM PROMPT", "USER TEXT")

    assert result == {"Value": 10, "Awareness": 5}
    assert captured["url"] == GROQ_API_URL
    assert captured["headers"]["Authorization"] == "Bearer test-key"
    assert captured["json"]["model"] == "test-model"
    assert captured["json"]["temperature"] == 0.2
    assert captured["json"]["response_format"] == {"type": "json_object"}
    assert captured["json"]["messages"] == [
        {"role": "system", "content": "SYSTEM PROMPT"},
        {"role": "user", "content": "USER TEXT"},
    ]


def test_complete_json_raises_on_malformed_content(monkeypatch):
    def fake_post(url, headers=None, json=None, timeout=None):  # noqa: A002
        return _FakeResponse({"choices": [{"message": {"content": "not json"}}]})

    monkeypatch.setattr("aiclients.groq_client.requests.post", fake_post)
    client = GroqClient(api_key="k", model="m")
    with pytest.raises(json.JSONDecodeError):
        client.complete_json("s", "u")


def test_complete_json_raises_on_http_error(monkeypatch):
    def fake_post(url, headers=None, json=None, timeout=None):  # noqa: A002
        return _FakeResponse({}, status_code=500)

    monkeypatch.setattr("aiclients.groq_client.requests.post", fake_post)
    client = GroqClient(api_key="k", model="m")
    with pytest.raises(RuntimeError):
        client.complete_json("s", "u")
