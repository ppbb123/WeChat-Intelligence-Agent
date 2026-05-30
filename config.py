from dataclasses import dataclass
import os

from dotenv import load_dotenv


load_dotenv()


def _get_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


@dataclass(frozen=True)
class Settings:
    wewe_rss_json_url: str = os.getenv(
        "WEWE_RSS_JSON_URL", "http://127.0.0.1:4000/feeds/all.json"
    )
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", os.getenv("AI_API_KEY", ""))
    gemini_model_name: str = os.getenv(
        "GEMINI_MODEL_NAME", os.getenv("MODEL_NAME", "gemini-3.5-flash")
    )

    email_host: str = os.getenv("EMAIL_HOST", "smtp.qq.com")
    email_port: int = int(os.getenv("EMAIL_PORT", "465"))
    email_user: str = os.getenv("EMAIL_USER", "")
    email_password: str = os.getenv("EMAIL_PASSWORD", "")
    email_to: str = os.getenv("EMAIL_TO", "")

    database_path: str = os.getenv("DATABASE_PATH", "data/wechat_agent.db")
    reports_dir: str = os.getenv("REPORTS_DIR", "reports")
    fetch_interval_minutes: int = int(os.getenv("FETCH_INTERVAL_MINUTES", "60"))
    max_items_per_run: int = int(os.getenv("MAX_ITEMS_PER_RUN", "30"))
    send_email: bool = _get_bool("SEND_EMAIL", True)
    weekly_report_day: int = int(os.getenv("WEEKLY_REPORT_DAY", "6"))
    weekly_report_time: str = os.getenv("WEEKLY_REPORT_TIME", "20:00")
    weekly_loop_poll_seconds: int = int(os.getenv("WEEKLY_LOOP_POLL_SECONDS", "60"))


settings = Settings()
