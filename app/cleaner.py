from __future__ import annotations

import re
from html import unescape

from bs4 import BeautifulSoup


WHITESPACE_RE = re.compile(r"\s+")


def clean_text(value: str) -> str:
    text = BeautifulSoup(value or "", "html.parser").get_text(" ")
    text = unescape(text)
    return WHITESPACE_RE.sub(" ", text).strip()


def clean_item(item: dict[str, str]) -> dict[str, str]:
    return {
        "title": clean_text(item.get("title", "")),
        "link": item.get("link", "").strip(),
        "author": clean_text(item.get("author", "")),
        "published_at": item.get("published_at", "").strip(),
        "summary": clean_text(item.get("summary", "")),
    }


def keep_useful_items(items: list[dict[str, str]]) -> list[dict[str, str]]:
    seen: set[str] = set()
    results: list[dict[str, str]] = []

    for item in items:
        cleaned = clean_item(item)
        identity = cleaned["link"] or cleaned["title"]
        if not cleaned["title"] or not identity or identity in seen:
            continue
        seen.add(identity)
        results.append(cleaned)

    return results

