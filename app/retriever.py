from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass


WORD_RE = re.compile(r"[a-zA-Z0-9_+\-.]+")
CJK_RE = re.compile(r"[\u4e00-\u9fff]")


@dataclass(frozen=True)
class SearchResult:
    article: dict[str, str]
    score: float
    matched_terms: list[str]


def retrieve_articles(
    query: str,
    articles: list[dict[str, str]],
    top_k: int = 5,
) -> list[SearchResult]:
    if not query.strip() or not articles:
        return []

    documents = [_article_text(article) for article in articles]
    query_terms = _tokenize(query)
    document_terms = [_tokenize(document) for document in documents]
    idf = _build_idf(document_terms)
    query_vector = _tfidf(query_terms, idf)

    results: list[SearchResult] = []
    for article, terms in zip(articles, document_terms):
        vector = _tfidf(terms, idf)
        score = _cosine(query_vector, vector)
        matched_terms = sorted(set(query_terms) & set(terms))
        if score > 0:
            results.append(SearchResult(article=article, score=score, matched_terms=matched_terms[:8]))

    return sorted(results, key=lambda item: item.score, reverse=True)[:top_k]


def _article_text(article: dict[str, str]) -> str:
    title = article.get("title", "")
    author = article.get("author", "")
    summary = article.get("summary", "")
    return f"{title} {title} {author} {summary}"


def _tokenize(text: str) -> list[str]:
    normalized = text.lower()
    tokens = WORD_RE.findall(normalized)
    cjk_chars = CJK_RE.findall(normalized)

    tokens.extend(cjk_chars)
    tokens.extend(
        "".join(cjk_chars[index : index + 2])
        for index in range(max(0, len(cjk_chars) - 1))
    )
    tokens.extend(
        "".join(cjk_chars[index : index + 3])
        for index in range(max(0, len(cjk_chars) - 2))
    )
    return [token for token in tokens if token.strip()]


def _build_idf(documents: list[list[str]]) -> dict[str, float]:
    document_count = len(documents)
    document_frequency: Counter[str] = Counter()
    for terms in documents:
        document_frequency.update(set(terms))

    return {
        term: math.log((1 + document_count) / (1 + count)) + 1
        for term, count in document_frequency.items()
    }


def _tfidf(terms: list[str], idf: dict[str, float]) -> dict[str, float]:
    counts = Counter(terms)
    if not counts:
        return {}
    max_count = max(counts.values())
    return {
        term: (count / max_count) * idf.get(term, 1.0)
        for term, count in counts.items()
    }


def _cosine(left: dict[str, float], right: dict[str, float]) -> float:
    if not left or not right:
        return 0.0

    common_terms = set(left) & set(right)
    dot = sum(left[term] * right[term] for term in common_terms)
    left_norm = math.sqrt(sum(value * value for value in left.values()))
    right_norm = math.sqrt(sum(value * value for value in right.values()))
    if not left_norm or not right_norm:
        return 0.0
    return dot / (left_norm * right_norm)

