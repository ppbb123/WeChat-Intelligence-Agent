from __future__ import annotations

from datetime import datetime
from pathlib import Path


def generate_markdown_report(
    reports_dir: str,
    analysis: str,
    articles: list[dict[str, str]],
    title: str | None = None,
) -> tuple[str, str]:
    output_dir = Path(reports_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    now = datetime.now()
    report_title = title or f"WeChat Intelligence Report {now:%Y-%m-%d %H:%M}"
    file_path = output_dir / f"wechat-report-{now:%Y%m%d-%H%M%S}.md"

    article_lines = []
    for article in articles:
        line = f"- [{article['title']}]({article['link']})"
        if article.get("author"):
            line += f" - {article['author']}"
        article_lines.append(line)

    content = "\n".join(
        [
            f"# {report_title}",
            "",
            f"生成时间：{now:%Y-%m-%d %H:%M:%S}",
            f"分析文章数：{len(articles)}",
            "",
            "## Agent 分析",
            "",
            analysis.strip(),
            "",
            "## 原始文章",
            "",
            "\n".join(article_lines) if article_lines else "本次没有文章。",
            "",
        ]
    )

    file_path.write_text(content, encoding="utf-8")
    return report_title, str(file_path)

