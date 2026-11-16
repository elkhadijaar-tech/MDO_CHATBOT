"""Vercel serverless entrypoint for the MDO chatbot."""
import os
import shutil
from pathlib import Path

from app import create_app

ROOT = Path(__file__).resolve().parent.parent
RUNTIME = Path("/tmp/mdo-chatbot")
RUNTIME.mkdir(parents=True, exist_ok=True)

# SQLite on Vercel must live in writable /tmp, not in the read-only deployment bundle.
source_db = ROOT / "data" / "nexa.db"
runtime_db = RUNTIME / "nexa.db"
if source_db.exists() and not runtime_db.exists():
    shutil.copy2(source_db, runtime_db)

app = create_app({
    "DB_PATH": runtime_db,
    "UPLOAD_DIR": RUNTIME / "uploads",
    "LOG_DIR": RUNTIME / "logs",
})
