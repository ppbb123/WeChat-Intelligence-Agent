from __future__ import annotations

import argparse
from datetime import datetime, timedelta
import re
import time

from app.ai_analyzer import analyze_articles
from app.cleaner import keep_useful_items
from app.database import Database
from app.email_sender import send_email
from app.memory import build_memory_snapshot
from app.profile import load_profile
from app.rag_qa import answer_question
from app.report_generator import generate_markdown_report
from app.retriever import retrieve_articles
from app.rss_fetcher import fetch_wewe_rss_items, normalize_item
from app.scorer import score_articles, serialize_scored_articles
from config import settings


EMAIL_TITLE_RE = re.compile(r"^邮件标题[:：]\s*(.+)$", re.MULTILINE)


def build_email_title(
    analysis: str,
    scored_articles: list[dict[str, object]],
    report_type: str = "daily",
) -> str:
    match = EMAIL_TITLE_RE.search(analysis)
    if match:
        return match.group(1).strip()

    top_titles = [
        str(item.get("title", "")).strip()
        for item in scored_articles[:3]
        if item.get("title")
    ]
    if top_titles:
        short_titles = "、".join(title[:14] for title in top_titles)
        if report_type == "weekly":
            return f"【WeChat Agent】本周学习周报：{short_titles}"
        return f"【WeChat Agent】今日高价值情报：{short_titles}"
    if report_type == "weekly":
        return "【WeChat Agent】本周公众号学习周报"
    return "【WeChat Agent】本次情报分析"


def remove_email_title_line(analysis: str) -> str:
    return EMAIL_TITLE_RE.sub("", analysis).strip()


def send_report_email(title: str, analysis: str) -> None:
    if not settings.send_email:
        return

    try:
        send_email(
            host=settings.email_host,
            port=settings.email_port,
            user=settings.email_user,
            password=settings.email_password,
            to_address=settings.email_to,
            subject=title,
            body=analysis,
        )
        print("Email sent.")
    except Exception as exc:
        print(f"Email sending failed: {exc}")


def fetch_and_store_latest(database: Database) -> list[dict[str, str]]:
    print("Fetching WeWe RSS JSON...")
    raw_items = fetch_wewe_rss_items(settings.wewe_rss_json_url)
    normalized_items = [normalize_item(item) for item in raw_items]
    useful_items = keep_useful_items(normalized_items)[: settings.max_items_per_run]
    new_articles = database.save_articles(useful_items)
    print(f"Fetched {len(raw_items)} items, saved {len(new_articles)} new articles.")
    return new_articles


def analyze_and_report(
    database: Database,
    articles: list[dict[str, str]],
    report_type: str = "daily",
    period_label: str = "",
) -> None:
    profile = load_profile()
    scored = score_articles(articles, profile)
    scored_payload = serialize_scored_articles(scored)
    memory_snapshot = build_memory_snapshot(database, profile)

    analysis = analyze_articles(
        scored_payload,
        profile=profile,
        memory_snapshot=memory_snapshot,
        api_key=settings.gemini_api_key,
        model_name=settings.gemini_model_name,
        report_type=report_type,
        period_label=period_label,
    )
    title = build_email_title(analysis, scored_payload, report_type=report_type)
    analysis = remove_email_title_line(analysis)
    title, report_path = generate_markdown_report(
        settings.reports_dir,
        analysis,
        articles,
        title=title,
    )
    database.save_report(title, report_path, len(articles))
    print(f"Report generated: {report_path}")
    send_report_email(title, analysis)


def ask_history(question: str, top_k: int) -> None:
    database = Database(settings.database_path)
    database.initialize()
    articles = database.get_all_articles()
    results = retrieve_articles(question, articles, top_k=top_k)
    answer = answer_question(
        question,
        results,
        api_key=settings.gemini_api_key,
        model_name=settings.gemini_model_name,
    )
    print(answer)


def week_bounds(now: datetime | None = None) -> tuple[datetime, datetime]:
    current = now or datetime.now()
    start = current - timedelta(days=current.weekday())
    start = start.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=7)
    return start, end


def current_week_key(now: datetime | None = None) -> str:
    current = now or datetime.now()
    iso_year, iso_week, _ = current.isocalendar()
    return f"{iso_year}-W{iso_week:02d}"


def run_weekly_report(force: bool = False) -> None:
    database = Database(settings.database_path)
    database.initialize()

    week_key = current_week_key()
    if not force and database.has_job_run("weekly_report", week_key):
        print(f"Weekly report already generated for {week_key}.")
        return

    fetch_and_store_latest(database)
    start, end = week_bounds()
    articles = database.get_articles_created_between(
        start.strftime("%Y-%m-%d %H:%M:%S"),
        end.strftime("%Y-%m-%d %H:%M:%S"),
    )
    period_label = f"{start:%Y-%m-%d} 至 {(end - timedelta(days=1)):%Y-%m-%d}"
    print(f"Loaded {len(articles)} articles created this week: {period_label}.")

    analyze_and_report(
        database,
        articles,
        report_type="weekly",
        period_label=period_label,
    )
    database.save_job_run("weekly_report", week_key)


def should_run_weekly(now: datetime | None = None) -> bool:
    current = now or datetime.now()
    try:
        hour_text, minute_text = settings.weekly_report_time.split(":", maxsplit=1)
        scheduled_hour = int(hour_text)
        scheduled_minute = int(minute_text)
    except ValueError:
        scheduled_hour = 20
        scheduled_minute = 0

    return (
        current.weekday() == settings.weekly_report_day
        and current.hour == scheduled_hour
        and current.minute == scheduled_minute
    )


def run_weekly_loop() -> None:
    print(
        "Weekly loop started. "
        f"day={settings.weekly_report_day}, time={settings.weekly_report_time}."
    )
    while True:
        try:
            if should_run_weekly():
                run_weekly_report(force=False)
        except Exception as exc:
            print(f"Weekly report failed: {exc}")
        time.sleep(settings.weekly_loop_poll_seconds)


def run_once(analyze_existing: bool = False) -> None:
    database = Database(settings.database_path)
    database.initialize()

    if analyze_existing:
        articles = database.get_latest_articles(settings.max_items_per_run)
        print(f"Loaded {len(articles)} existing articles from database.")
        analyze_and_report(database, articles)
        return

    new_articles = fetch_and_store_latest(database)
    analyze_and_report(database, new_articles)


def run_forever() -> None:
    while True:
        try:
            run_once()
        except Exception as exc:
            print(f"Agent run failed: {exc}")
        time.sleep(settings.fetch_interval_minutes * 60)


def main() -> None:
    parser = argparse.ArgumentParser(description="WeChat Intelligence Agent")
    parser.add_argument("--loop", action="store_true", help="Run continuously.")
    parser.add_argument(
        "--weekly",
        action="store_true",
        help="Generate this week's learning report immediately.",
    )
    parser.add_argument(
        "--weekly-loop",
        action="store_true",
        help="Run forever and generate a weekly report at the configured day/time.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force weekly report generation even if this week already ran.",
    )
    parser.add_argument(
        "--analyze-existing",
        action="store_true",
        help="Analyze the latest existing articles already saved in the database.",
    )
    parser.add_argument(
        "--ask",
        type=str,
        default="",
        help="Ask a question over historical articles with local retrieval + Gemini RAG.",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Number of retrieved articles used as RAG context.",
    )
    args = parser.parse_args()

    if args.ask:
        ask_history(args.ask, top_k=args.top_k)
    elif args.weekly:
        run_weekly_report(force=args.force)
    elif args.weekly_loop:
        run_weekly_loop()
    elif args.loop:
        run_forever()
    else:
        run_once(analyze_existing=args.analyze_existing)


if __name__ == "__main__":
    main()
