from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import requests


def _stringify(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, dict):
        for key in ("name", "title", "author"):
            if value.get(key):
                return str(value[key])
        return ""
    return str(value)


def fetch_wewe_rss_items(url: str, timeout: int = 20) -> list[dict[str, Any]]:
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()
    payload = response.json()

    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("items", "data", "feeds", "entries"):
            value = payload.get(key)
            if isinstance(value, list):
                return value

    raise ValueError("Unsupported WeWe RSS JSON format. Expected a list or an items/data list.")


def normalize_item(raw: dict[str, Any]) -> dict[str, str]:
    title = _stringify(raw.get("title") or raw.get("name")).strip()
    link = _stringify(raw.get("link") or raw.get("url") or raw.get("id")).strip()
    author = _stringify(raw.get("author") or raw.get("source") or raw.get("account")).strip()
    published_at = _stringify(
        raw.get("published") or raw.get("pubDate") or raw.get("date") or raw.get("created_at") or ""
    ).strip()
    summary = _stringify(
        raw.get("summary") or raw.get("description") or raw.get("contentSnippet") or raw.get("content") or ""
    ).strip()

    return {
        "title": title,
        "link": link,
        "author": author,
        "published_at": published_at or datetime.now(timezone.utc).isoformat(),
        "summary": summary,
    }
