from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class UserProfile:
    interests: list[str]
    avoid: list[str]
    focus_questions: list[str]


DEFAULT_PROFILE = UserProfile(
    interests=[
        "AI Agent",
        "医疗大数据",
        "生物统计",
        "医学机器学习",
        "疾病风险评估",
        "多标签学习",
        "数据平台",
        "论文选题",
        "自动化工具",
    ],
    avoid=["会议通知", "纯通知", "招生宣传", "节日祝福"],
    focus_questions=[
        "哪些文章值得今天立即阅读？",
        "哪些内容可以转化成项目、论文或自动化工具？",
        "哪些主题正在反复出现，值得长期追踪？",
    ],
)


def load_profile(path: str = "interests.yaml") -> UserProfile:
    profile_path = Path(path)
    if not profile_path.exists():
        return DEFAULT_PROFILE

    sections = _parse_simple_yaml_list(profile_path.read_text(encoding="utf-8"))
    return UserProfile(
        interests=sections.get("interests") or DEFAULT_PROFILE.interests,
        avoid=sections.get("avoid") or DEFAULT_PROFILE.avoid,
        focus_questions=sections.get("focus_questions") or DEFAULT_PROFILE.focus_questions,
    )


def _parse_simple_yaml_list(text: str) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {}
    current_key = ""

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.endswith(":") and not line.startswith("-"):
            current_key = line[:-1].strip()
            sections.setdefault(current_key, [])
            continue
        if line.startswith("-") and current_key:
            value = line[1:].strip().strip("\"'")
            if value:
                sections[current_key].append(value)

    return sections

