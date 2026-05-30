from __future__ import annotations

import json

from app.profile import UserProfile


SYSTEM_PROMPT = """你是一个微信公众号情报分析 agent。
你的任务不是简单摘要，而是像一个研究与项目助理一样，基于用户兴趣判断哪些内容值得注意、为什么值得注意、下一步应该做什么。
请用中文输出，判断要克制，只能基于给定文章和历史统计，不要编造原文没有的信息。"""


PLACEHOLDER_KEYS = {
    "",
    "your_api_key_here",
    "your_gemini_api_key_here",
    "your_deepseek_api_key_here",
    "你的Gemini_API_Key",
    "你的DeepSeek_API_Key",
}


def analyze_articles(
    scored_articles: list[dict[str, object]],
    profile: UserProfile,
    memory_snapshot: dict[str, object],
    api_key: str,
    model_name: str,
    report_type: str = "daily",
    period_label: str = "",
) -> str:
    if not scored_articles:
        if report_type == "weekly":
            return f"{period_label or '本周'}没有发现新的公众号文章。"
        return "本次没有发现新的文章。"
    if not api_key or api_key.strip() in PLACEHOLDER_KEYS:
        return fallback_analysis(scored_articles, "未配置有效的 GEMINI_API_KEY", report_type)

    try:
        from google import genai
    except ImportError:
        return fallback_analysis(
            scored_articles,
            "未安装 google-genai，已改用基础报告。请运行：pip install -r requirements.txt",
            report_type,
        )

    payload = {
        "report_type": report_type,
        "period_label": period_label,
        "user_profile": {
            "interests": profile.interests,
            "avoid": profile.avoid,
            "focus_questions": profile.focus_questions,
        },
        "memory_snapshot": memory_snapshot,
        "scored_articles": scored_articles,
    }
    prompt = _build_prompt(payload, report_type)

    try:
        client = genai.Client(api_key=api_key.strip())
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
        )
    except Exception as exc:
        return fallback_analysis(scored_articles, f"Gemini 请求失败，已改用基础报告：{exc}", report_type)

    return response.text or fallback_analysis(scored_articles, "Gemini 返回内容为空，已改用基础报告", report_type)


def _build_prompt(payload: dict[str, object], report_type: str) -> str:
    if report_type == "weekly":
        instructions = (
            "请输出一份适合每周定点发送的「学习周报」，格式如下：\n"
            "1. 本周学习总览：本周新增内容是否值得系统学习，核心判断是什么。\n"
            "2. 本周最值得精读的 3-5 篇：每篇给出标题、分数、标签、推荐理由和学习重点。\n"
            "3. 本周主题地图：归纳本周出现的主要方向，例如算法、疾病场景、数据平台、通知类信息。\n"
            "4. 可以跳过的内容：说明哪些是通知、宣传、祝福或低价值重复信息。\n"
            "5. 下周学习计划：给出 3-5 条具体学习动作，尽量可执行。\n"
            "6. 可沉淀资产：说明哪些内容可以整理成论文选题、代码工具、知识卡片或项目想法。\n"
            "7. 邮件标题建议：最后单独输出一行，格式为「邮件标题：...」。\n"
        )
    else:
        instructions = (
            "请输出一份适合直接放进邮件正文的情报简报，格式如下：\n"
            "1. 开场判断：今天是否值得打扰用户，为什么。\n"
            "2. 最值得看的 3 篇：每篇给出标题、分数、标签、推荐理由和建议动作。\n"
            "3. 可以跳过的内容：列出原因，不要冗长。\n"
            "4. 持续趋势：结合 memory_snapshot 判断哪些主题反复出现。\n"
            "5. 今日建议行动：给出 2-4 条具体行动。\n"
            "6. 邮件标题建议：最后单独输出一行，格式为「邮件标题：...」。\n"
        )

    return (
        f"{SYSTEM_PROMPT}\n\n"
        f"{instructions}\n"
        f"输入数据：\n{json.dumps(payload, ensure_ascii=False, indent=2)}"
    )


def fallback_analysis(
    scored_articles: list[dict[str, object]],
    reason: str,
    report_type: str = "daily",
) -> str:
    top_articles = sorted(
        scored_articles,
        key=lambda item: int(item.get("score", 0)),
        reverse=True,
    )
    heading = "## 本周学习判断" if report_type == "weekly" else "## 今日情报判断"
    title = "【WeChat Agent】本周公众号学习周报" if report_type == "weekly" else "【WeChat Agent】本次情报预筛结果"

    lines = [
        reason,
        "",
        heading,
        f"本次共分析 {len(scored_articles)} 篇文章。下面是基于本地兴趣规则的预筛结果。",
        "",
        "## 最值得看的文章",
    ]
    for index, item in enumerate(top_articles[:5], start=1):
        lines.append(
            f"{index}. {item.get('title', '')} "
            f"（{item.get('score', 0)} 分，{item.get('label', '')}）"
        )
        lines.append(f"   原因：{item.get('reason', '')}")
        if item.get("link"):
            lines.append(f"   链接：{item.get('link')}")

    lines.extend(["", f"邮件标题：{title}"])
    return "\n".join(lines)
