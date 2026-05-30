from __future__ import annotations

import ast
import sqlite3
from pathlib import Path


SCHEMA = """
CREATE TABLE IF NOT EXISTS articles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    link TEXT NOT NULL UNIQUE,
    author TEXT,
    published_at TEXT,
    summary TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    path TEXT NOT NULL,
    article_count INTEGER NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS job_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_name TEXT NOT NULL,
    run_key TEXT NOT NULL,
    ran_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(job_name, run_key)
);
"""


def _clean_author(value: str | None) -> str:
    if not value:
        return ""
    text = value.strip()
    if text.startswith("{") and text.endswith("}"):
        try:
            parsed = ast.literal_eval(text)
        except (SyntaxError, ValueError):
            return text
        if isinstance(parsed, dict) and parsed.get("name"):
            return str(parsed["name"])
    return text


class Database:
    def __init__(self, path: str) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    def initialize(self) -> None:
        with self.connect() as connection:
            connection.executescript(SCHEMA)

    def save_articles(self, articles: list[dict[str, str]]) -> list[dict[str, str]]:
        new_articles: list[dict[str, str]] = []

        with self.connect() as connection:
            for article in articles:
                cursor = connection.execute(
                    """
                    INSERT OR IGNORE INTO articles
                    (title, link, author, published_at, summary)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        article["title"],
                        article["link"],
                        article.get("author", ""),
                        article.get("published_at", ""),
                        article.get("summary", ""),
                    ),
                )
                if cursor.rowcount:
                    new_articles.append(article)

        return new_articles

    def get_latest_articles(self, limit: int) -> list[dict[str, str]]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT title, link, author, published_at, summary
                FROM articles
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

        return [
            {
                "title": row["title"],
                "link": row["link"],
                "author": _clean_author(row["author"]),
                "published_at": row["published_at"] or "",
                "summary": row["summary"] or "",
            }
            for row in rows
        ]

    def get_all_articles(self) -> list[dict[str, str]]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT id, title, link, author, published_at, summary
                FROM articles
                ORDER BY id DESC
                """
            ).fetchall()

        return [
            {
                "id": str(row["id"]),
                "title": row["title"],
                "link": row["link"],
                "author": _clean_author(row["author"]),
                "published_at": row["published_at"] or "",
                "summary": row["summary"] or "",
            }
            for row in rows
        ]

    def get_articles_created_between(self, start_at: str, end_at: str) -> list[dict[str, str]]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT id, title, link, author, published_at, summary
                FROM articles
                WHERE created_at >= ? AND created_at < ?
                ORDER BY id DESC
                """,
                (start_at, end_at),
            ).fetchall()

        return [
            {
                "id": str(row["id"]),
                "title": row["title"],
                "link": row["link"],
                "author": _clean_author(row["author"]),
                "published_at": row["published_at"] or "",
                "summary": row["summary"] or "",
            }
            for row in rows
        ]

    def has_job_run(self, job_name: str, run_key: str) -> bool:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT 1 FROM job_runs WHERE job_name = ? AND run_key = ?",
                (job_name, run_key),
            ).fetchone()
        return row is not None

    def save_job_run(self, job_name: str, run_key: str) -> None:
        with self.connect() as connection:
            connection.execute(
                "INSERT OR IGNORE INTO job_runs (job_name, run_key) VALUES (?, ?)",
                (job_name, run_key),
            )

    def save_report(self, title: str, path: str, article_count: int) -> None:
        with self.connect() as connection:
            connection.execute(
                "INSERT INTO reports (title, path, article_count) VALUES (?, ?, ?)",
                (title, path, article_count),
            )
