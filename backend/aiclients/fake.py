class FakeAIClient:
    """Test double for AIClient — no network.

    Returns a pre-programmed queue of responses. Each queued item is either a
    dict (returned as-is) or an exception instance/class (raised) — simulating
    a malformed/unparseable or failed response. Every call is logged in
    `.calls` for assertions on what the retry loop actually sent.
    """

    def __init__(self, responses: list) -> None:
        self._responses = list(responses)
        self.calls: list[tuple[str, str]] = []

    def complete_json(self, system: str, user: str) -> dict:
        self.calls.append((system, user))
        if not self._responses:
            raise AssertionError("FakeAIClient ran out of programmed responses")
        item = self._responses.pop(0)
        if isinstance(item, BaseException):
            raise item
        if isinstance(item, type) and issubclass(item, BaseException):
            raise item("simulated AI client failure")
        return item
