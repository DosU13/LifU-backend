import pytest

from aiclients.base import AIClient
from aiclients.fake import FakeAIClient


def test_returns_queued_dicts_in_order():
    client = FakeAIClient([{"a": 1}, {"a": 2}])
    assert client.complete_json("s", "u1") == {"a": 1}
    assert client.complete_json("s", "u2") == {"a": 2}


def test_logs_every_call():
    client = FakeAIClient([{"a": 1}, {"a": 2}])
    client.complete_json("system-1", "user-1")
    client.complete_json("system-2", "user-2")
    assert client.calls == [("system-1", "user-1"), ("system-2", "user-2")]


def test_raises_queued_exception_instance():
    client = FakeAIClient([ValueError("boom")])
    with pytest.raises(ValueError, match="boom"):
        client.complete_json("s", "u")


def test_raises_queued_exception_class():
    client = FakeAIClient([ValueError])
    with pytest.raises(ValueError):
        client.complete_json("s", "u")


def test_raises_assertion_error_when_exhausted():
    client = FakeAIClient([{"a": 1}])
    client.complete_json("s", "u")
    with pytest.raises(AssertionError):
        client.complete_json("s", "u")


def test_satisfies_ai_client_protocol():
    assert isinstance(FakeAIClient([{"a": 1}]), AIClient)
