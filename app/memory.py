from __future__ import annotations

from collections import Counter

from app.database import Database
from app.profile import UserProfile


def build_memory_snapshot(
    database: Database,
    profile: UserProfile,
    limit: int = 200,
) -> dict[str, object]:
    articles = database.get_latest_articles(limit)
    keyword_counts: Counter[str] = Counter()
    source_counts: Counter[str] = Counter()

    for article in articles:
        text = " ".join(
            [
                article.get("title", ""),
                article.get("author", ""),
                article.get("summary", ""),
            ]
        ).lower()
        for keyword in profile.interests:
            if keyword.lower() in text:
                keyword_counts[keyword] += 1
        author = article.get("author", "").strip()
        if author:
            source_counts[author] += 1

    return {
        "article_count": len(articles),
        "recurring_topics": [
            {"topic": topic, "count": count}
            for topic, count in keyword_counts.most_common(8)
        ],
        "active_sources": [
            {"source": source, "count": count}
            for source, count in source_counts.most_common(5)
        ],
    }

