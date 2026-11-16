"""Import dynamique de sources (adaptateurs par format) : inspection -> rapport -> passages indexables.

Principes de sécurité : le fichier original est copié (jamais modifié ni supprimé) ; les bases SQLite sont ouvertes en
lecture seule ; aucun SQL provenant du fichier n'est exécuté ; tout le contenu importé est traité comme non fiable
(statut NEEDS_VERIFICATION).
"""
import csv
import hashlib
import io
import json
import re
import shutil
import sqlite3
import zipfile
from pathlib import Path

from .chunking import chunk_markdown
from .knowledge import add_chunk, ensure_kb

ALLOWED = {".txt", ".md", ".csv", ".json", ".sqlite", ".sqlite3", ".db", ".docx", ".xlsx", ".pptx", ".pdf"}
MAX_BYTES = 25 * 1024 * 1024
MAX_ROWS = 5000
UNSUPPORTED_HINT = {".sql": "Les dumps SQL ne sont pas exécutés pour des raisons de sécurité : importez la base .sqlite correspondante ou un export CSV.",
                    ".doc": "Format .doc ancien non pris en charge : enregistrez le fichier en .docx.",
                    ".xls": "Format .xls ancien non pris en charge : enregistrez le fichier en .xlsx.",
                    ".ppt": "Format .ppt ancien non pris en charge : enregistrez le fichier en .pptx."}


class IngestError(Exception):
    pass


def _q(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def _read_text(path: Path) -> str:
    raw = path.read_bytes()
    for enc in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def _row_text(cols, vals) -> str:
    parts = []
    for c, v in zip(cols, vals):
        if v is None or (isinstance(v, str) and not v.strip()):
            continue
        if isinstance(v, (bytes, bytearray)):
            v = "[données binaires]"
        parts.append(f"{c}: {str(v).strip()}")
    return "; ".join(parts)


def _check_zip(path: Path):
    if not zipfile.is_zipfile(path):
        raise IngestError("Fichier corrompu ou format incorrect (archive Office invalide).")
    with zipfile.ZipFile(path) as z:
        if sum(i.file_size for i in z.infolist()) > 150 * 1024 * 1024:
            raise IngestError("Fichier refusé : contenu décompressé trop volumineux.")


# ---------- adaptateurs : chacun retourne (report, records) ----------
def _a_text(path):
    text = _read_text(path)
    if path.suffix.lower() == ".txt":
        lines = []
        for ln in text.splitlines():
            s = ln.strip()
            if s and len(s) < 90 and re.match(r"^(\d+[.)]\s|partie\b|chapitre\b|module\b|section\b)", s, re.I) and not s.endswith("."):
                ln = "## " + s
            lines.append(ln)
        text = "\n".join(lines)
    chunks = chunk_markdown(text)
    heads = len({c["heading"] for c in chunks if c["heading"]})
    return ({"format": "texte", "characters": len(text), "headings": heads},
            [{"heading": c["heading"], "text": c["text"], "location": c["heading"] or "début"} for c in chunks])


def _rows_to_records(rows, cols, label):
    recs, seen, dup, empty = [], set(), 0, 0
    for i, vals in enumerate(rows, start=1):
        t = _row_text(cols, vals)
        if not t:
            empty += 1
            continue
        if t in seen:
            dup += 1
        seen.add(t)
        recs.append({"heading": label, "text": t, "location": f"{label}, ligne {i}"})
    return recs, {"rows_read": len(recs) + empty, "empty_rows": empty, "duplicate_rows_in_file": dup}


def _a_csv(path):
    text = _read_text(path)
    try:
        dialect = csv.Sniffer().sniff(text[:4096], delimiters=",;\t|")
    except csv.Error:
        dialect = csv.excel
    rows = list(csv.reader(io.StringIO(text), dialect))
    if not rows:
        raise IngestError("Fichier CSV vide.")
    cols = [c.strip() or f"colonne_{i+1}" for i, c in enumerate(rows[0])]
    body = rows[1:MAX_ROWS + 1]
    recs, stats = _rows_to_records(body, cols, path.stem)
    rep = {"format": "csv", "delimiter": dialect.delimiter, "columns": cols, "truncated": len(rows) - 1 > MAX_ROWS}
    rep.update(stats)
    return rep, recs


def _a_json(path):
    try:
        data = json.loads(_read_text(path))
    except json.JSONDecodeError as exc:
        raise IngestError(f"JSON invalide : {exc.msg} (ligne {exc.lineno}).")
    if isinstance(data, dict) and len(data) == 1 and isinstance(next(iter(data.values())), list):
        data = next(iter(data.values()))
    if isinstance(data, list) and data and all(isinstance(x, dict) for x in data):
        cols = sorted({k for x in data for k in x})
        rows = [[x.get(c) if not isinstance(x.get(c), (dict, list)) else json.dumps(x.get(c), ensure_ascii=False)
                 for c in cols] for x in data[:MAX_ROWS]]
        recs, stats = _rows_to_records(rows, cols, path.stem)
        rep = {"format": "json (liste d'objets)", "columns": cols, "records": len(data), "truncated": len(data) > MAX_ROWS}
        rep.update(stats)
        return rep, recs
    lines = []

    def walk(o, p=""):
        if isinstance(o, dict):
            for k, v in o.items():
                walk(v, f"{p}{k} > " if isinstance(v, (dict, list)) else f"{p}{k}")
                if not isinstance(v, (dict, list)):
                    lines.append(f"{p}{k}: {v}")
        elif isinstance(o, list):
            for i, v in enumerate(o):
                if isinstance(v, (dict, list)):
                    walk(v, f"{p}[{i}] > ")
                else:
                    lines.append(f"{p.rstrip(' >')}: {v}")
    walk(data)
    chunks = chunk_markdown("\n".join(lines), default_title=path.stem)
    return ({"format": "json (structure libre)", "lines": len(lines)},
            [{"heading": path.stem, "text": c["text"], "location": path.stem} for c in chunks])


def _a_xlsx(path):
    _check_zip(path)
    try:
        import openpyxl
    except ImportError:
        raise IngestError("Le paquet openpyxl est requis pour .xlsx : pip install openpyxl")
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    recs, sheets = [], []
    for ws in wb.worksheets:
        rows = [list(r) for r in ws.iter_rows(values_only=True)]
        rows = [r for r in rows if any(v not in (None, "") for v in r)]
        if not rows:
            sheets.append({"sheet": ws.title, "rows": 0})
            continue
        cols = [str(c).strip() if c not in (None, "") else f"colonne_{i+1}" for i, c in enumerate(rows[0])]
        r, stats = _rows_to_records(rows[1:MAX_ROWS + 1], cols, ws.title)
        recs += r
        sheets.append({"sheet": ws.title, "columns": cols, "rows": len(rows) - 1, **stats})
    wb.close()
    return {"format": "xlsx", "sheets": sheets}, recs


def _a_docx(path):
    _check_zip(path)
    try:
        import docx
        from docx.table import Table
        from docx.text.paragraph import Paragraph
    except ImportError:
        raise IngestError("Le paquet python-docx est requis pour .docx : pip install python-docx")
    d = docx.Document(str(path))
    md, heads, tables = [], 0, 0
    for el in d.element.body.iterchildren():
        tag = el.tag.rsplit("}", 1)[-1]
        if tag == "p":
            p = Paragraph(el, d)
            t = p.text.strip()
            if not t:
                continue
            style = (p.style.name if p.style is not None else "") or ""
            if style.lower().startswith(("heading", "titre", "title")):
                md.append("## " + t)
                heads += 1
            else:
                md.append(t)
        elif tag == "tbl":
            tables += 1
            for row in Table(el, d).rows:
                md.append("| " + " | ".join(c.text.strip().replace("\n", " ") for c in row.cells) + " |")
            md.append("")
    chunks = chunk_markdown("\n".join(md))
    return ({"format": "docx", "headings": heads, "tables": tables},
            [{"heading": c["heading"], "text": c["text"], "location": c["heading"] or "début"} for c in chunks])


def _a_pptx(path):
    _check_zip(path)
    try:
        from pptx import Presentation
    except ImportError:
        raise IngestError("Le paquet python-pptx est requis pour .pptx : pip install python-pptx")
    prs, recs = Presentation(str(path)), []
    for n, slide in enumerate(prs.slides, start=1):
        texts = []
        for sh in slide.shapes:
            if sh.has_text_frame:
                texts += [p.text.strip() for p in sh.text_frame.paragraphs if p.text.strip()]
            if getattr(sh, "has_table", False) and sh.has_table:
                for row in sh.table.rows:
                    texts.append("| " + " | ".join(c.text.strip() for c in row.cells) + " |")
        if texts:
            recs.append({"heading": texts[0][:80], "text": "\n".join(texts), "location": f"diapositive {n}"})
    return {"format": "pptx", "slides": len(prs.slides), "slides_with_text": len(recs)}, recs


def _a_pdf(path):
    try:
        import pypdf
    except ImportError:
        raise IngestError("Le paquet pypdf est requis pour .pdf : pip install pypdf")
    try:
        reader = pypdf.PdfReader(str(path))
        if reader.is_encrypted:
            raise IngestError("PDF protégé par mot de passe : non pris en charge.")
        recs, empty = [], 0
        for n, page in enumerate(reader.pages, start=1):
            txt = (page.extract_text() or "").strip()
            if not txt:
                empty += 1
                continue
            for c in chunk_markdown(txt):
                recs.append({"heading": f"page {n}", "text": c["text"], "location": f"page {n}"})
    except IngestError:
        raise
    except Exception as exc:
        raise IngestError(f"PDF illisible ({exc.__class__.__name__}).")
    rep = {"format": "pdf", "pages": len(reader.pages), "pages_without_text": empty}
    if empty:
        rep["warning"] = "Pages sans texte (scan ?) : l'OCR n'est pas disponible."
    return rep, recs


def _a_sqlite(path):
    if path.read_bytes()[:16] != b"SQLite format 3\x00":
        raise IngestError("Ce fichier n'est pas une base SQLite valide.")
    uri = f"file:{path.as_posix()}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.execute("PRAGMA query_only = ON")
    recs, tables = [], []
    try:
        names = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
        for t in names:
            info = conn.execute(f"PRAGMA table_info({_q(t)})").fetchall()
            cols = [r[1] for r in info]
            pk = [r[1] for r in info if r[5]]
            fks = [{"column": r[3], "references": f"{r[2]}.{r[4]}"} for r in conn.execute(f"PRAGMA foreign_key_list({_q(t)})")]
            idx = [r[1] for r in conn.execute(f"PRAGMA index_list({_q(t)})")]
            count = conn.execute(f"SELECT COUNT(*) FROM {_q(t)}").fetchone()[0]
            tables.append({"table": t, "columns": [{"name": r[1], "type": r[2]} for r in info], "primary_key": pk,
                           "foreign_keys": fks, "indexes": idx, "rows": count})
            cur = conn.execute(f"SELECT * FROM {_q(t)} LIMIT {MAX_ROWS}")
            for i, vals in enumerate(cur, start=1):
                txt = _row_text(cols, vals)
                if txt:
                    recs.append({"heading": t, "text": f"Table {t} — {txt}", "location": f"table {t}, enregistrement {i}"})
    except sqlite3.DatabaseError as exc:
        raise IngestError(f"Base SQLite illisible ({exc}).")
    finally:
        conn.close()
    return {"format": "sqlite", "tables": tables, "schema_signature": json.dumps(
        [(t["table"], [c["name"] for c in t["columns"]]) for t in tables])}, recs


ADAPTERS = {".txt": _a_text, ".md": _a_text, ".csv": _a_csv, ".json": _a_json, ".xlsx": _a_xlsx, ".docx": _a_docx,
            ".pptx": _a_pptx, ".pdf": _a_pdf, ".sqlite": _a_sqlite, ".sqlite3": _a_sqlite, ".db": _a_sqlite}


def safe_name(name: str) -> str:
    base = re.sub(r"[^\w.\-]+", "_", Path(name).name, flags=re.UNICODE).strip("._") or "fichier"
    return base[:120]


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _populate(conn, sid, kb, display, records):
    added = dup = skipped = 0
    for r in records:
        text = (r["text"] or "").strip()
        if len(text) < 3:
            skipped += 1
            continue
        title = f"{display} — {r['heading']}" if r.get("heading") else display
        if add_chunk(conn, kb, sid, title, text, "import", r.get("location"), "NEEDS_VERIFICATION"):
            added += 1
        else:
            dup += 1
    return added, dup, skipped


def import_file(conn, data: bytes, original_name: str, kb: str, upload_dir, label: str = "") -> dict:
    """Importe un fichier téléversé. Lève IngestError pour les refus ; retourne le rapport d'ingestion."""
    ext = Path(original_name).suffix.lower()
    if ext in UNSUPPORTED_HINT:
        raise IngestError(UNSUPPORTED_HINT[ext])
    if ext not in ALLOWED:
        raise IngestError(f"Format « {ext or 'inconnu'} » non pris en charge. Formats acceptés : {', '.join(sorted(ALLOWED))}.")
    if not data:
        raise IngestError("Fichier vide.")
    if len(data) > MAX_BYTES:
        raise IngestError("Fichier trop volumineux (25 Mo maximum).")
    kb = re.sub(r"[^a-z0-9_-]+", "-", kb.strip().lower()).strip("-")[:40]
    if not kb:
        raise IngestError("Nom de base de connaissances invalide.")
    digest = sha256_bytes(data)
    if conn.execute("SELECT id FROM sources WHERE kb=? AND sha256=? AND status='indexed'", (kb, digest)).fetchone():
        raise IngestError("Ce fichier (contenu identique) est déjà importé dans cette base.")
    upload_dir = Path(upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    stored = upload_dir / f"{digest[:12]}_{safe_name(original_name)}"
    if not stored.exists():
        stored.write_bytes(data)  # original conservé tel quel
    ensure_kb(conn, kb, label or kb, 0)
    sid = conn.execute("INSERT INTO sources (kb, name, filename, stored_path, source_type, sha256, status) VALUES (?,?,?,?,?,?, 'failed')",
                       (kb, Path(original_name).stem, Path(original_name).name, str(stored), ext.lstrip("."), digest)).lastrowid
    conn.commit()
    return _index_source(conn, sid, stored, kb, Path(original_name).stem, ext, digest, len(data))


def _index_source(conn, sid, stored: Path, kb, display, ext, digest, size, previous_report=None) -> dict:
    try:
        report, records = ADAPTERS[ext](stored)
    except IngestError as exc:
        rep = {"status": "failed", "error": str(exc), "size_bytes": size, "sha256": digest}
        conn.execute("UPDATE sources SET status='failed', report=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
                     (json.dumps(rep, ensure_ascii=False), sid))
        conn.commit()
        raise
    except Exception as exc:  # fichier inattendu : échec propre, jamais de plantage
        rep = {"status": "failed", "error": f"Lecture impossible ({exc.__class__.__name__}).", "size_bytes": size, "sha256": digest}
        conn.execute("UPDATE sources SET status='failed', report=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
                     (json.dumps(rep, ensure_ascii=False), sid))
        conn.commit()
        raise IngestError(rep["error"])
    added, dup, skipped = _populate(conn, sid, kb, display, records)
    report.update({"status": "indexed", "size_bytes": size, "sha256": digest, "records_extracted": len(records),
                   "chunks_indexed": added, "duplicates_skipped": dup, "empty_skipped": skipped, "kb": kb})
    if previous_report and previous_report.get("schema_signature") and previous_report["schema_signature"] != report.get("schema_signature"):
        report["schema_changed"] = True
    if added == 0:
        report["warning"] = report.get("warning") or "Aucun contenu exploitable n'a été indexé."
    conn.execute("UPDATE sources SET status='indexed', chunk_count=?, duplicate_count=?, report=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
                 (added, dup, json.dumps(report, ensure_ascii=False), sid))
    conn.commit()
    report["source_id"] = sid
    return report


def reindex_source(conn, sid: int) -> dict:
    row = conn.execute("SELECT * FROM sources WHERE id=?", (sid,)).fetchone()
    if not row or row["builtin"]:
        raise IngestError("Source introuvable ou intégrée (utilisez le rechargement de la base intégrée).")
    stored = Path(row["stored_path"])
    if not stored.exists():
        raise IngestError("Le fichier original est introuvable sur le disque.")
    prev = json.loads(row["report"] or "{}")
    conn.execute("DELETE FROM chunks WHERE source_id=?", (sid,))
    return _index_source(conn, sid, stored, row["kb"], row["name"], "." + (row["source_type"] or ""), row["sha256"],
                         stored.stat().st_size, prev)


def delete_source(conn, sid: int) -> None:
    """Retire une source de l'index (retour en arrière). Le fichier original n'est jamais supprimé."""
    row = conn.execute("SELECT builtin FROM sources WHERE id=?", (sid,)).fetchone()
    if not row:
        raise IngestError("Source introuvable.")
    if row["builtin"]:
        raise IngestError("Les sources intégrées ne peuvent pas être supprimées.")
    conn.execute("DELETE FROM chunks WHERE source_id=?", (sid,))
    conn.execute("DELETE FROM sources WHERE id=?", (sid,))
    conn.commit()
