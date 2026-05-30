from __future__ import annotations

import json

from app.ai_analyzer import PLACEHOLDER_KEYS
from app.retriever import SearchResult


def answer_question(
    question: str,
    results: list[SearchResult],
    api_key: str,
    model_name: str,
) -> str:
    if not results:
        return "没有在历史文章中检索到足够相关的内容。"

    context = [
        {
            "rank": index,
            "title": result.article.get("title", ""),
            "author": result.article.get("author", ""),
            "published_at": result.article.get("published_at", ""),
            "summary": result.article.get("summary", ""),
            "link": result.article.get("link", ""),
            "retrieval_score": round(result.score, 4),
            "matched_terms": result.matched_terms,
        }
        for index, result in enumerate(results, start=1)
    ]

    if not api_key or api_key.strip() in PLACEHOLDER_KEYS:
        return _fallback_answer(question, context, "未配置有效的 GEMINI_API_KEY")

    try:
        from google import genai
    except ImportError:
        return _fallback_answer(
            question,
            context,
            "未安装 google-genai，请运行：pip install -r requirements.txt",
        )

    prompt = (
        "你是一个基于历史微信公众号文章的 RAG 问答助手。\n"
        "请只基于给定 context 回答用户问题，不要编造未出现的信息。\n"
        "回答结构：先给结论，再给证据文章，最后给可行动建议。\n"
        "如果证据不足，请明确说明不足。\n\n"
        f"用户问题：{question}\n\n"
        f"context：\n{json.dumps(context, ensure_ascii=False, indent=2)}"
    )

    try:
        client = genai.Client(api_key=api_key.strip())
        response = client.models.generate_content(model=model_name, contents=prompt)
    except Exception as exc:
        return _fallback_answer(question, context, f"Gemini 请求失败：{exc}")

    answer = response.text or ""
    if not answer.strip():
        return _fallback_answer(question, context, "Gemini 返回内容为空")
    return answer.strip() + "\n\n" + format_sources(results)


def format_sources(results: list[SearchResult]) -> str:
    lines = ["## 检索来源"]
    for index, result in enumerate(results, start=1):
        article = result.article
        lines.append(
            f"{index}. {article.get('title', '')} "
            f"(score={result.score:.4f})"
        )
        if article.get("link"):
            lines.append(f"   {article.get('link')}")
    return "\n".join(lines)


def _fallback_answer(question: str, context: list[dict[str, object]], reason: str) -> str:
    lines = [
        reason,
        "",
        f"问题：{question}",
        "",
        "下面是本地检索到的相关历史文章：",
    ]
    for item in context:
        lines.append(
            f"{item['rank']}. {item['title']} "
            f"(score={item['retrieval_score']})"
        )
        if item.get("summary"):
            lines.append(f"   摘要：{str(item['summary'])[:180]}")
        if item.get("link"):
            lines.append(f"   链接：{item['link']}")
    return "\n".join(lines)
