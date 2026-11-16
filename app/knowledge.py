"""Gestion des bases de connaissances : chargement des bases intégrées, enregistrement des sources, passages."""
import hashlib
import json
import re
from pathlib import Path

from .chunking import chunk_markdown, text_hash

BUILTIN = {
    "onboarding": "Intégration MDO / ESTC (base officielle v3)",
    "cours": "Cours — référentiel pédagogique (19 modules)",
}


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ensure_kb(conn, name: str, label: str = "", builtin: int = 0) -> None:
    conn.execute("INSERT OR IGNORE INTO kbs (name, label, builtin) VALUES (?,?,?)", (name, label or name, builtin))


def add_chunk(conn, kb, source_id, title, text, kind="item", location=None, verification="NEEDS_VERIFICATION",
              semester=None, section_id=None, academic_year=None, dedupe=True) -> bool:
    """Insère un passage ; retourne False si un passage identique existe déjà dans la même base."""
    h = text_hash(title + " " + text)
    if dedupe and conn.execute("SELECT 1 FROM chunks WHERE kb=? AND text_hash=? LIMIT 1", (kb, h)).fetchone():
        return False
    conn.execute(
        "INSERT INTO chunks (section_id, title, text, kind, semester, kb, source_id, location, academic_year, verification, text_hash)"
        " VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (section_id, title, text, kind, semester, kb, source_id, location, academic_year, verification, h))
    return True


def _upsert_builtin_source(conn, kb, name, path: Path) -> tuple:
    row = conn.execute("SELECT id, sha256 FROM sources WHERE kb=? AND builtin=1 AND filename=?", (kb, path.name)).fetchone()
    digest = _sha(path)
    if row:
        return row["id"], row["sha256"] != digest, digest
    sid = conn.execute(
        "INSERT INTO sources (kb, name, filename, stored_path, source_type, sha256, builtin) VALUES (?,?,?,?,?,?,1)",
        (kb, name, path.name, str(path), path.suffix.lstrip("."), digest)).lastrowid
    return sid, True, digest


def _finish_source(conn, sid, digest, added, dup, report):
    conn.execute("UPDATE sources SET sha256=?, chunk_count=?, duplicate_count=?, report=?, status='indexed', "
                 "updated_at=CURRENT_TIMESTAMP WHERE id=?",
                 (digest, added, dup, json.dumps(report, ensure_ascii=False), sid))


def load_onboarding(conn, kb_path, force=False) -> bool:
    kb_path = Path(kb_path)
    ensure_kb(conn, "onboarding", BUILTIN["onboarding"], 1)
    sid, changed, digest = _upsert_builtin_source(conn, "onboarding", "Base officielle ESTC / MDO (v3)", kb_path)
    if not (changed or force):
        return False
    kb = json.loads(kb_path.read_text(encoding="utf-8"))
    conn.execute("DELETE FROM chunks WHERE source_id=?", (sid,))
    conn.execute("DELETE FROM modules")
    conn.execute("DELETE FROM sections")
    V = "VERIFIED_USER_DATABASE"
    n = 0
    for pos, sec in enumerate(kb["sections"]):
        conn.execute("INSERT INTO sections (id, title, position) VALUES (?,?,?)", (sec["id"], sec["title"], pos))
        for item in sec["items"]:
            n += add_chunk(conn, "onboarding", sid, sec["title"], item, "item", sec["title"], V, section_id=sec["id"])
    for f in kb.get("faq", []):
        n += add_chunk(conn, "onboarding", sid, "Questions fréquentes", f"{f['q']} {f['a']}", "faq", "FAQ", V, section_id="faq")
    by_name, by_sem = {}, {}
    for sem, name, prof in kb["modules"]:
        conn.execute("INSERT INTO modules (semester, name, professor) VALUES (?,?,?)", (sem, name, prof))
        by_name.setdefault(name, []).append((sem, prof))
        by_sem.setdefault(sem, []).append((name, prof))
    for sem, mods in sorted(by_sem.items()):
        lines = "; ".join(f"{nm} ({p if p else 'professeur non indiqué dans la base'})" for nm, p in mods)
        n += add_chunk(conn, "onboarding", sid, f"Modules et professeurs - Semestre {sem} filière MDO",
                       f"Semestre {sem} - modules et professeurs : {lines}.", "semester", f"Semestre {sem}", V,
                       semester=sem, section_id="modules")
    for name, entries in by_name.items():
        parts = "; ".join(f"Semestre {s} : {p if p else 'professeur non indiqué dans la base'}" for s, p in entries)
        n += add_chunk(conn, "onboarding", sid, "Modules et professeurs - filière MDO",
                       f"Module « {name} » - professeur - {parts}.", "module", name, V, section_id="modules")
    _finish_source(conn, sid, digest, n, 0, {"format": "json", "sections": len(kb["sections"]), "modules": len(kb["modules"])})
    conn.commit()
    return True


def parse_courses(md: str) -> list:
    """Découpe courses.md : un module par '## N. Titre' ; passages avec numéro et titre de module."""
    out = []
    parts = re.split(r"(?m)^##\s+", md)
    for part in parts[1:]:
        head, _, body = part.partition("\n")
        m = re.match(r"(\d+)\.\s*(.*)", head.strip())
        if not m:
            continue
        num, title = int(m.group(1)), m.group(2).strip()
        for c in chunk_markdown(body, default_title=title, max_chars=600, min_chars=100):
            out.append({"module_no": num, "module": title, "text": c["text"]})
    return out


def load_courses(conn, path, force=False) -> bool:
    path = Path(path)
    if not path.exists():
        return False
    ensure_kb(conn, "cours", BUILTIN["cours"], 1)
    sid, changed, digest = _upsert_builtin_source(conn, "cours", "Référentiel des cours ESTC (19 modules)", path)
    if not (changed or force):
        return False
    conn.execute("DELETE FROM chunks WHERE source_id=?", (sid,))
    n = dup = 0
    for c in parse_courses(path.read_text(encoding="utf-8")):
        ok = add_chunk(conn, "cours", sid, f"Cours — {c['module_no']}. {c['module']}", c["text"], "course",
                       f"Module {c['module_no']} — {c['module']}", "VERIFIED_USER_DATABASE")
        n += ok
        dup += (not ok)
    _finish_source(conn, sid, digest, n, dup, {"format": "markdown", "modules": 19})
    conn.commit()
    return True


def load_knowledge(conn, kb_path, courses_path=None, force=False) -> bool:
    a = load_onboarding(conn, kb_path, force)
    b = load_courses(conn, courses_path, force) if courses_path else False
    return a or b


def all_chunks(conn, kbs=None) -> list:
    sql = ("SELECT c.id, c.section_id, c.title, c.text, c.kind, c.semester, c.kb, c.source_id, c.location, c.verification, "
           "c.academic_year, s.name AS source_name FROM chunks c LEFT JOIN sources s ON s.id=c.source_id")
    return [dict(r) for r in conn.execute(sql)]


def course_modules(conn) -> list:
    rows = conn.execute("SELECT DISTINCT location FROM chunks WHERE kb='cours' ORDER BY id").fetchall()
    out, seen = [], set()
    for r in rows:
        m = re.match(r"Module (\d+) — (.*)", r["location"] or "")
        if m and m.group(1) not in seen:
            seen.add(m.group(1))
            out.append({"no": int(m.group(1)), "title": m.group(2)})
    return out
