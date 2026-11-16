"""Préparation : crée .env si besoin (avec une clé secrète), initialise la base et charge les données."""
import secrets

from .config import BASE_DIR, get_config
from .db import connect, init_db
from .knowledge import load_knowledge


def ensure_env() -> bool:
    env, example = BASE_DIR / ".env", BASE_DIR / ".env.example"
    created = False
    if not env.exists() and example.exists():
        env.write_text(example.read_text(encoding="utf-8"), encoding="utf-8")
        created = True
    if env.exists():
        lines = env.read_text(encoding="utf-8").splitlines()
        out = []
        for line in lines:
            if line.strip() == "SECRET_KEY=":
                line = "SECRET_KEY=" + secrets.token_hex(32)
            out.append(line)
        env.write_text("\n".join(out) + "\n", encoding="utf-8")
    return created


def main() -> None:
    if ensure_env():
        print("[OK] Fichier .env créé (mode DÉMO tant qu'aucune clé API n'est renseignée).")
    cfg = get_config()
    conn = connect(cfg["DB_PATH"])
    backup = init_db(conn, cfg["DB_PATH"])
    if backup:
        print(f"[OK] Ancienne base migrée ; sauvegarde créée : {backup}")
    reloaded = load_knowledge(conn, cfg["KB_PATH"], cfg["COURSES_PATH"])
    kbs = {r[0]: r[1] for r in conn.execute("SELECT kb, COUNT(*) FROM chunks GROUP BY kb")}
    m = conn.execute("SELECT COUNT(*) FROM modules").fetchone()[0]
    print(f"[OK] Base de données prête : {kbs} passages, {m} modules MDO{' - bases rechargées' if reloaded else ''}.")
    conn.close()


if __name__ == "__main__":
    main()
