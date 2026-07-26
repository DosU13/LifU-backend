"""Quote and fact sources for generated Pouches. Both are key-free public APIs."""

import requests

from core.entities import GeneratedContent
from core.enums import GeneratedKind
from providers.base import HTTP_TIMEOUT_SECONDS

ZENQUOTES_URL = "https://zenquotes.io/api/random"
USELESS_FACTS_URL = "https://uselessfacts.jsph.pl/api/v2/facts/random"


class ZenQuotesSource:
    """Random inspirational quote. No API key required."""

    def fetch(self) -> GeneratedContent:
        response = requests.get(ZENQUOTES_URL, timeout=HTTP_TIMEOUT_SECONDS)
        response.raise_for_status()
        item = response.json()[0]
        text = (item.get("q") or "").strip()
        if not text:
            raise ValueError("ZenQuotes returned an empty quote")
        return GeneratedContent(
            kind=GeneratedKind.QUOTE,
            title="A thought",
            url="",
            author=(item.get("a") or "Unknown").strip(),
            text=text,
        )


class UselessFactsSource:
    """Random trivia fact. No API key required."""

    def fetch(self) -> GeneratedContent:
        response = requests.get(
            USELESS_FACTS_URL, params={"language": "en"}, timeout=HTTP_TIMEOUT_SECONDS
        )
        response.raise_for_status()
        data = response.json()
        text = (data.get("text") or "").strip()
        if not text:
            raise ValueError("UselessFacts returned an empty fact")
        return GeneratedContent(
            kind=GeneratedKind.FACT,
            title="Did you know?",
            url=data.get("source_url") or "",
            author="",
            text=text,
        )
