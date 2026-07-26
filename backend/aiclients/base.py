from typing import Protocol, runtime_checkable


@runtime_checkable
class AIClient(Protocol):
    def complete_json(self, system: str, user: str) -> dict:
        """Call the model with a system+user prompt and return the parsed JSON object.

        Implementations may raise any exception (network failure, non-JSON
        response, ...) — the validation pipeline (aiclients/validation.py)
        treats every exception here as a structural failure and retries.
        """
        ...
