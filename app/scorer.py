from __future__ import annotations

from dataclasses import dataclass

from app.profile import UserProfile


@dataclass(frozen=True)
class ScoredArticle:
    article: dict[str, str]
    score: int
    label: str
    matched_interests: list[str]
    avoid_hits: list[str]
    reason: str


def score_articles(
    articles: list[dict[str, str]],
    profile: UserProfile,
) -> list[ScoredArticle]:
    scored = [_score_article(article, profile) for article in articles]
    return sorted(scored, key=lambda item: item.score, reverse=True)


def _score_article(article: dict[str, str], profile: UserProfile) -> ScoredArticle:
    text = " ".join(
        [
            article.get("title", ""),
            article.get("author", ""),
            article.get("summary", ""),
        ]
    ).lower()
    matched = [keyword for keyword in profile.interests if keyword.lower() in text]
    avoid_hits = [keyword for keyword in profile.avoid if keyword.lower() in text]

    score = 20 + len(matched) * 18 - len(avoid_hits) * 20
    if article.get("summary"):
        score += 8
    if any(word in text for word in ["研究", "模型", "平台", "数据", "预测", "风险", "agent", "ai"]):
        score += 12
    if any(word in text for word in ["通知", "祝福", "会议", "论坛"]):
        score -= 8

    score = max(0, min(score, 100))
    label = _label_for_score(score, avoid_hits)
    reason = _build_reason(matched, avoid_hits, bool(article.get("summary")))

    return ScoredArticle(
        article=article,
        score=score,
        label=label,
        matched_interests=matched,
        avoid_hits=avoid_hits,
        reason=reason,
    )


def _label_for_score(score: int, avoid_hits: list[str]) -> str:
    if avoid_hits and score < 50:
        return "可以忽略"
    if score >= 75:
        return "立即阅读"
    if score >= 55:
        return "值得收藏"
    if score >= 35:
        return "后续跟踪"
    return "可以忽略"


def _build_reason(matched: list[str], avoid_hits: list[str], has_summary: bool) -> str:
    parts: list[str] = []
    if matched:
        parts.append("命中关注方向：" + "、".join(matched))
    if avoid_hits:
        parts.append("包含低优先级信号：" + "、".join(avoid_hits))
    if has_summary:
        parts.append("有可分析摘要")
    if not parts:
        parts.append("未明显命中偏好，保留为普通信息")
    return "；".join(parts)


def serialize_scored_articles(scored_articles: list[ScoredArticle]) -> list[dict[str, object]]:
    return [
        {
            "title": item.article.get("title", ""),
            "link": item.article.get("link", ""),
            "author": item.article.get("author", ""),
            "published_at": item.article.get("published_at", ""),
            "summary": item.article.get("summary", ""),
            "score": item.score,
            "label": item.label,
            "matched_interests": item.matched_interests,
            "avoid_hits": item.avoid_hits,
            "reason": item.reason,
        }
        for item in scored_articles
    ]

