import pathlib
import tempfile

from app import create_app


def make_app(**over):
    d = pathlib.Path(tempfile.mkdtemp())
    cfg = {"DB_PATH": d / "test.db", "LOG_DIR": d / "logs", "UPLOAD_DIR": d / "uploads", "LLM_API_KEY": "",
           "RATE_LIMIT_PER_MIN": 1000, "LLM_BACKOFF": 0, "ADMIN_PASSWORD": "", "LLM_FALLBACK_MODEL": ""}
    cfg.update(over)
    return create_app(cfg)
