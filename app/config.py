import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def get_config() -> dict:
    return {
        "BASE_DIR": BASE_DIR,
        "DB_PATH": Path(os.getenv("DB_PATH", BASE_DIR / "data" / "nexa.db")),
        "KB_PATH": Path(os.getenv("KB_PATH", BASE_DIR / "data" / "knowledge_base.json")),
        "COURSES_PATH": Path(os.getenv("COURSES_PATH", BASE_DIR / "data" / "courses.md")),
        "UPLOAD_DIR": Path(os.getenv("UPLOAD_DIR", BASE_DIR / "data" / "uploads")),
        "LOG_DIR": Path(os.getenv("LOG_DIR", BASE_DIR / "data" / "logs")),
        "ADMIN_PASSWORD": os.getenv("ADMIN_PASSWORD", ""),
        "LLM_FALLBACK_MODEL": os.getenv("LLM_FALLBACK_MODEL", "").strip(),
        "SECRET_KEY": os.getenv("SECRET_KEY") or "dev-only-change-me",
        "LLM_PROVIDER": os.getenv("LLM_PROVIDER", "anthropic").strip().lower(),
        "LLM_API_KEY": os.getenv("LLM_API_KEY", "").strip(),
        "LLM_MODEL": os.getenv("LLM_MODEL", "claude-sonnet-5-5").strip(),
        "LLM_BASE_URL": os.getenv("LLM_BASE_URL", "").strip(),
        "RATE_LIMIT_PER_MIN": int(os.getenv("RATE_LIMIT_PER_MIN", "20")),
        "MAX_MESSAGE_LEN": int(os.getenv("MAX_MESSAGE_LEN", "1000")),
        "HOST": os.getenv("HOST", "127.0.0.1"),
        "PORT": int(os.getenv("PORT", "5000")),
    }
