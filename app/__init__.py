"""MDO CHATBOT v2 - assistant d'intégration et tuteur MDO / ESTC Casablanca."""
import hmac
import importlib.util
import json
import logging
import sys
import time
import uuid
from collections import defaultdict, deque
from functools import wraps
from logging.handlers import RotatingFileHandler

from flask import Flask, Response, g, jsonify, redirect, render_template, request, session, url_for

from .chat import ChatEngine
from .config import get_config
from .db import connect, init_db
from .ingest import IngestError, delete_source, import_file, reindex_source
from .knowledge import all_chunks, course_modules, load_knowledge
from .lang import detect_language
from .llm import LLMClient
from .messages import t
from .retrieval import Index

__version__ = "2.0.0"
CSP = ("default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self'; "
       "frame-ancestors 'none'; base-uri 'self'; form-action 'self'")


def create_app(overrides: dict = None) -> Flask:
    cfg = get_config()
    cfg.update(overrides or {})
    app = Flask(__name__)
    app.config.update(SECRET_KEY=cfg["SECRET_KEY"], SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax",
                      MAX_CONTENT_LENGTH=26 * 1024 * 1024, NEXA=cfg)

    log = logging.getLogger(f"nexa.{id(app)}")
    log.setLevel(logging.INFO)
    log.propagate = False
    try:
        cfg["LOG_DIR"].mkdir(parents=True, exist_ok=True)
        h = RotatingFileHandler(cfg["LOG_DIR"] / "nexa.log", maxBytes=1_000_000, backupCount=3, encoding="utf-8")
        h.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
        log.addHandler(h)
    except OSError:
        pass
    app.extensions["log"] = log

    conn = connect(cfg["DB_PATH"])
    backup = init_db(conn, cfg["DB_PATH"])
    load_knowledge(conn, cfg["KB_PATH"], cfg["COURSES_PATH"])
    chunks = all_chunks(conn)
    conn.close()
    if backup:
        log.info("migration base : sauvegarde créée %s", backup)
    llm = LLMClient(cfg["LLM_PROVIDER"], cfg["LLM_API_KEY"], cfg["LLM_MODEL"], cfg["LLM_BASE_URL"],
                    backoff=cfg.get("LLM_BACKOFF", 1.5), fallback_model=cfg["LLM_FALLBACK_MODEL"])
    engine = ChatEngine(Index(chunks), llm)
    app.extensions["engine"] = engine
    app.extensions["migration_backup"] = backup
    hits = defaultdict(deque)

    def db():
        return connect(cfg["DB_PATH"])

    def rebuild_index():
        c = db()
        engine.set_index(Index(all_chunks(c)))
        c.close()

    def limited(key: str, limit: int) -> bool:
        now, q = time.time(), hits[key]
        while q and now - q[0] > 60:
            q.popleft()
        if len(q) >= limit:
            return True
        q.append(now)
        return False

    def client_id() -> str:
        if "client" not in session:
            session["client"] = uuid.uuid4().hex
        return session["client"]

    def conversation_id(conn, create=True):
        cid = session.get("cid")
        if cid and conn.execute("SELECT 1 FROM conversations WHERE id=? AND client_id=?", (cid, client_id())).fetchone():
            return cid
        if not create:
            return None
        cid = conn.execute("INSERT INTO conversations (client_id) VALUES (?)", (client_id(),)).lastrowid
        conn.commit()
        session["cid"] = cid
        return cid

    def is_admin() -> bool:
        if cfg["ADMIN_PASSWORD"]:
            return session.get("admin") is True
        return request.remote_addr in ("127.0.0.1", "::1")

    def admin_required(api: bool):
        def deco(fn):
            @wraps(fn)
            def wrapper(*a, **kw):
                if not is_admin():
                    if api:
                        return jsonify(error="Accès administrateur requis."), 403
                    return redirect(url_for("login")) if cfg["ADMIN_PASSWORD"] else (render_template("forbidden.html", page=""), 403)
                if api and request.method in ("POST", "DELETE") and request.headers.get("X-Requested-With") != "fetch":
                    return jsonify(error="Requête refusée (en-tête de sécurité manquant)."), 403
                return fn(*a, **kw)
            return wrapper
        return deco

    @app.context_processor
    def inject():
        return {"is_admin": is_admin(), "version": __version__, "has_password": bool(cfg["ADMIN_PASSWORD"])}

    @app.before_request
    def start():
        g.rid, g.t0 = uuid.uuid4().hex[:8], time.time()

    @app.after_request
    def after(resp):
        resp.headers["X-Content-Type-Options"] = "nosniff"
        resp.headers["X-Frame-Options"] = "DENY"
        resp.headers["Referrer-Policy"] = "same-origin"
        resp.headers["Content-Security-Policy"] = CSP
        resp.headers["X-Request-ID"] = getattr(g, "rid", "-")
        if request.path.startswith("/api/") or resp.status_code >= 400:
            log.info("rid=%s %s %s status=%s ms=%d", getattr(g, "rid", "-"), request.method, request.path,
                     resp.status_code, int((time.time() - getattr(g, "t0", time.time())) * 1000))
        return resp

    @app.errorhandler(413)
    def too_big(_e):
        return jsonify(error="Fichier trop volumineux (25 Mo maximum)."), 413

    @app.errorhandler(500)
    def server_error(_e):
        log.exception("rid=%s erreur interne", getattr(g, "rid", "-"))
        if request.path.startswith("/api/"):
            return jsonify(error="Erreur interne.", request_id=g.rid), 500
        return "Erreur interne. Référence : " + g.rid, 500

    # ---------------- pages ----------------
    @app.get("/")
    def dashboard():
        return render_template("dashboard.html", page="dashboard")

    @app.get("/chat")
    def chat_page():
        return render_template("chat.html", page="chat")

    @app.get("/courses")
    def courses_page():
        return render_template("courses.html", page="courses")

    @app.get("/modules")
    def modules_page():
        return render_template("modules.html", page="modules")

    @app.get("/infos")
    def infos_page():
        conn = db()
        secs = []
        for s in conn.execute("SELECT id, title FROM sections WHERE id NOT IN ('modules') ORDER BY position"):
            items = [r["text"] for r in conn.execute("SELECT text FROM chunks WHERE section_id=? AND kind='item'", (s["id"],))]
            secs.append({"id": s["id"], "title": s["title"], "items": items})
        conn.close()
        return render_template("infos.html", page="infos", sections=secs)

    @app.get("/knowledge")
    @admin_required(api=False)
    def knowledge_page():
        return render_template("knowledge.html", page="knowledge")

    @app.get("/diagnostics")
    @admin_required(api=False)
    def diagnostics_page():
        return render_template("diagnostics.html", page="diagnostics")

    @app.route("/admin/login", methods=["GET", "POST"])
    def login():
        if not cfg["ADMIN_PASSWORD"]:
            return redirect(url_for("knowledge_page"))
        error = ""
        if request.method == "POST":
            if limited("login:" + (request.remote_addr or ""), 5):
                error = "Trop de tentatives. Patientez une minute."
            elif hmac.compare_digest(request.form.get("password", ""), cfg["ADMIN_PASSWORD"]):
                session["admin"] = True
                return redirect(url_for("knowledge_page"))
            else:
                error = "Mot de passe incorrect."
        return render_template("login.html", page="", error=error), (401 if error else 200)

    @app.post("/admin/logout")
    def logout():
        session.pop("admin", None)
        return redirect(url_for("dashboard"))

    # ---------------- API publique ----------------
    @app.get("/api/status")
    def status():
        v = llm.verified
        return jsonify(mode=engine.mode, provider=cfg["LLM_PROVIDER"] if llm.configured else None,
                       model=cfg["LLM_MODEL"] if llm.configured else None,
                       fallback_model=cfg["LLM_FALLBACK_MODEL"] or None,
                       connection_verified=(v["ok"] if v else None), web_research=False, version=__version__)

    @app.get("/api/kbs")
    def kbs():
        conn = db()
        rows = [dict(r) for r in conn.execute(
            "SELECT k.name, k.label, k.builtin, (SELECT COUNT(*) FROM chunks c WHERE c.kb=k.name) AS chunks, "
            "(SELECT COUNT(*) FROM sources s WHERE s.kb=k.name AND s.status='indexed') AS sources FROM kbs k ORDER BY k.builtin DESC, k.name")]
        conn.close()
        return jsonify(rows)

    @app.get("/api/modules")
    def modules_api():
        sem = request.args.get("semester", type=int)
        q = (request.args.get("q") or "").strip().lower()
        conn = db()
        rows = [dict(r) for r in conn.execute("SELECT semester, name, professor FROM modules ORDER BY semester, id")]
        conn.close()
        if sem:
            rows = [r for r in rows if r["semester"] == sem]
        if q:
            rows = [r for r in rows if q in r["name"].lower() or q in (r["professor"] or "").lower()]
        return jsonify(rows)

    @app.get("/api/courses")
    def courses_api():
        conn = db()
        rows = course_modules(conn)
        conn.close()
        return jsonify(rows)

    @app.get("/api/conversations")
    def conversations():
        conn = db()
        rows = [dict(r) for r in conn.execute(
            "SELECT c.id, COALESCE(c.title,'Nouvelle conversation') AS title, c.created_at, "
            "(SELECT COUNT(*) FROM messages m WHERE m.conversation_id=c.id) AS messages "
            "FROM conversations c WHERE c.client_id=? AND EXISTS (SELECT 1 FROM messages m WHERE m.conversation_id=c.id) "
            "ORDER BY c.id DESC LIMIT 30", (client_id(),))]
        conn.close()
        return jsonify(conversations=rows, current=session.get("cid"))

    @app.post("/api/conversations/<int:cid>/open")
    def open_conversation(cid):
        conn = db()
        ok = conn.execute("SELECT 1 FROM conversations WHERE id=? AND client_id=?", (cid, client_id())).fetchone()
        conn.close()
        if not ok:
            return jsonify(error="Conversation introuvable."), 404
        session["cid"] = cid
        return jsonify(ok=True)

    @app.delete("/api/conversations/<int:cid>")
    def delete_conversation(cid):
        conn = db()
        if not conn.execute("SELECT 1 FROM conversations WHERE id=? AND client_id=?", (cid, client_id())).fetchone():
            conn.close()
            return jsonify(error="Conversation introuvable."), 404
        conn.execute("DELETE FROM messages WHERE conversation_id=?", (cid,))
        conn.execute("DELETE FROM conversations WHERE id=?", (cid,))
        conn.commit()
        conn.close()
        if session.get("cid") == cid:
            session.pop("cid", None)
        return jsonify(ok=True)

    @app.get("/api/history")
    def history():
        conn = db()
        cid = conversation_id(conn, create=False)
        rows = []
        if cid:
            rows = [{"id": r["id"], "role": r["role"], "content": r["content"], "mode": r["mode"], "model": r["model"],
                     "kb": r["kb_used"], "feedback": r["feedback"], "sources": json.loads(r["sources"] or "[]")}
                    for r in conn.execute("SELECT * FROM messages WHERE conversation_id=? ORDER BY id", (cid,))]
        conn.close()
        return jsonify(rows)

    @app.post("/api/reset")
    def reset():
        session.pop("cid", None)
        return jsonify(ok=True)

    @app.get("/api/export")
    def export():
        conn = db()
        cid = conversation_id(conn, create=False)
        lines = ["# Conversation MDO CHATBOT", ""]
        if cid:
            for r in conn.execute("SELECT role, content, sources FROM messages WHERE conversation_id=? ORDER BY id", (cid,)):
                lines += [f"**{'Étudiant' if r['role'] == 'user' else 'MDO CHATBOT'}**", "", r["content"], ""]
                src = json.loads(r["sources"] or "[]")
                if src:
                    lines += ["_Sources : " + " · ".join(src) + "_", ""]
        conn.close()
        return Response("\n".join(lines), mimetype="text/markdown",
                        headers={"Content-Disposition": "attachment; filename=conversation-mdo-chatbot.md"})

    @app.post("/api/feedback")
    def feedback():
        data = request.get_json(silent=True) or {}
        mid, val = data.get("message_id"), data.get("value")
        if not isinstance(mid, int) or val not in (-1, 0, 1):
            return jsonify(error="Paramètres invalides."), 400
        conn = db()
        ok = conn.execute("SELECT 1 FROM messages m JOIN conversations c ON c.id=m.conversation_id WHERE m.id=? AND c.client_id=? AND m.role='assistant'",
                          (mid, client_id())).fetchone()
        if not ok:
            conn.close()
            return jsonify(error="Message introuvable."), 404
        conn.execute("UPDATE messages SET feedback=? WHERE id=?", (val or None, mid))
        conn.commit()
        conn.close()
        return jsonify(ok=True)

    @app.post("/api/chat")
    def chat():
        data = request.get_json(silent=True) or {}
        question = str(data.get("message", "")).strip()
        lang_pref = data.get("lang", "auto")
        if lang_pref not in ("auto", "fr", "en", "ar", "darija"):
            lang_pref = "auto"
        mode_pref = data.get("mode", "auto")
        if mode_pref not in ("auto", "cours", "admin"):
            mode_pref = "auto"
        if not question:
            return jsonify(error="Message vide."), 400
        if len(question) > cfg["MAX_MESSAGE_LEN"]:
            return jsonify(error=f"Message trop long (max {cfg['MAX_MESSAGE_LEN']} caractères)."), 400
        if limited("chat:" + (request.remote_addr or "local"), cfg["RATE_LIMIT_PER_MIN"]):
            lang = detect_language(question) if lang_pref == "auto" else lang_pref
            return jsonify(error=t("rate_limit", lang)), 429
        conn = db()
        cid = conversation_id(conn)
        hist = [dict(r) for r in conn.execute(
            "SELECT role, content FROM messages WHERE conversation_id=? ORDER BY id DESC LIMIT 40", (cid,))][::-1]
        res = engine.answer(question, hist, lang_pref, mode_pref)
        usage = res.get("usage") or {}
        conn.execute("INSERT INTO messages (conversation_id, role, content, language, request_id) VALUES (?,?,?,?,?)",
                     (cid, "user", question, res["language"], g.rid))
        mid = conn.execute(
            "INSERT INTO messages (conversation_id, role, content, mode, language, sources, model, kb_used, tokens_in, tokens_out, request_id)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (cid, "assistant", res["answer"], res["mode"], res["language"], json.dumps(res["sources"], ensure_ascii=False),
             res.get("model"), res.get("kb"), usage.get("in"), usage.get("out"), g.rid)).lastrowid
        conn.execute("UPDATE conversations SET title=COALESCE(title, ?) WHERE id=?", (question[:60], cid))
        if res.get("not_found"):
            conn.execute("INSERT INTO unanswered (question, language) VALUES (?,?)", (question, res["language"]))
        conn.commit()
        conn.close()
        log.info("rid=%s chat mode=%s kb=%s task=%s lang=%s chunks=%s retrieval_ms=%s llm_ms=%s model=%s tokens_in=%s tokens_out=%s",
                 g.rid, res["mode"], res.get("kb"), res.get("task"), res["language"], res.get("chunks"),
                 res.get("retrieval_ms"), res.get("llm_ms"), res.get("model"), usage.get("in"), usage.get("out"))
        return jsonify(answer=res["answer"], mode=res["mode"], language=res["language"], sources=res["sources"],
                       source_details=res.get("source_details", []), kb=res.get("kb"), model=res.get("model"),
                       task=res.get("task"), message_id=mid, request_id=g.rid)

    # ---------------- API administration ----------------
    def sources_payload():
        conn = db()
        rows = [dict(r) for r in conn.execute(
            "SELECT id, kb, name, filename, source_type, status, chunk_count, duplicate_count, builtin, imported_at, updated_at "
            "FROM sources ORDER BY builtin DESC, id DESC")]
        kb_rows = [dict(r) for r in conn.execute(
            "SELECT k.name, k.label, k.builtin, (SELECT COUNT(*) FROM chunks c WHERE c.kb=k.name) AS chunks FROM kbs k ORDER BY k.builtin DESC, k.name")]
        conn.close()
        return {"kbs": kb_rows, "sources": rows}

    @app.get("/api/knowledge")
    @admin_required(api=True)
    def knowledge_list():
        return jsonify(sources_payload())

    @app.post("/api/knowledge/import")
    @admin_required(api=True)
    def knowledge_import():
        f = request.files.get("file")
        if not f or not f.filename:
            return jsonify(error="Aucun fichier reçu."), 400
        kb = request.form.get("kb", "").strip() or "documents"
        conn = db()
        try:
            rep = import_file(conn, f.read(), f.filename, kb, cfg["UPLOAD_DIR"], request.form.get("label", "").strip())
        except IngestError as exc:
            conn.close()
            log.info("rid=%s import refusé : %s", g.rid, exc)
            return jsonify(error=str(exc)), 400
        conn.close()
        rebuild_index()
        log.info("rid=%s import ok kb=%s chunks=%s doublons=%s", g.rid, rep["kb"], rep["chunks_indexed"], rep["duplicates_skipped"])
        return jsonify(report=rep)

    @app.post("/api/knowledge/sources/<int:sid>/reindex")
    @admin_required(api=True)
    def knowledge_reindex(sid):
        conn = db()
        row = conn.execute("SELECT builtin FROM sources WHERE id=?", (sid,)).fetchone()
        try:
            if row and row["builtin"]:
                load_knowledge(conn, cfg["KB_PATH"], cfg["COURSES_PATH"], force=True)
                rep = {"status": "indexed", "note": "Base intégrée rechargée depuis son fichier."}
            else:
                rep = reindex_source(conn, sid)
        except IngestError as exc:
            conn.close()
            return jsonify(error=str(exc)), 400
        conn.close()
        rebuild_index()
        return jsonify(report=rep)

    @app.delete("/api/knowledge/sources/<int:sid>")
    @admin_required(api=True)
    def knowledge_delete(sid):
        conn = db()
        try:
            delete_source(conn, sid)
        except IngestError as exc:
            conn.close()
            return jsonify(error=str(exc)), 400
        conn.close()
        rebuild_index()
        return jsonify(ok=True)

    @app.get("/api/knowledge/sources/<int:sid>/report")
    @admin_required(api=True)
    def knowledge_report(sid):
        conn = db()
        row = conn.execute("SELECT report FROM sources WHERE id=?", (sid,)).fetchone()
        conn.close()
        if not row:
            return jsonify(error="Source introuvable."), 404
        return jsonify(report=json.loads(row["report"] or "{}"))

    @app.get("/api/diagnostics")
    @admin_required(api=True)
    def diagnostics():
        checks = []

        def add(name, ok, detail):
            checks.append({"name": name, "ok": ok, "detail": detail})

        add("Python", sys.version_info >= (3, 10), sys.version.split()[0])
        for mod, label, required in (("flask", "Flask", True), ("requests", "requests", True), ("dotenv", "python-dotenv", True),
                                      ("openpyxl", "openpyxl (.xlsx)", False), ("docx", "python-docx (.docx)", False),
                                      ("pptx", "python-pptx (.pptx)", False), ("pypdf", "pypdf (.pdf)", False)):
            found = importlib.util.find_spec(mod) is not None
            add(label, found or not required, "installé" if found else ("MANQUANT" if required else "absent : import de ce format indisponible"))
        try:
            conn = db()
            n = conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
            failed = conn.execute("SELECT COUNT(*) FROM sources WHERE status='failed'").fetchone()[0]
            unans = conn.execute("SELECT COUNT(*) FROM unanswered").fetchone()[0]
            conn.close()
            add("Base de données SQLite", True, f"{n} passages indexés")
            add("Imports en échec", failed == 0, f"{failed} source(s) en échec")
            add("Questions sans réponse enregistrées", True, str(unans))
        except Exception as exc:  # noqa: BLE001
            add("Base de données SQLite", False, exc.__class__.__name__)
        add("Index de recherche", engine.index.size > 0, f"{engine.index.size} passages, bases : {engine.index.kb_counts()}")
        add("Embeddings / recherche vectorielle", True, "non utilisés : recherche lexicale BM25 + bigrammes (aucun modèle d'embedding requis)")
        add("Recherche web", False, "non configurée (fonction non implémentée dans cette version)")
        add("Fournisseur IA", llm.configured, f"{cfg['LLM_PROVIDER']} / {cfg['LLM_MODEL']}" if llm.configured else "aucune clé API : MODE DÉMO")
        v = llm.verified
        add("Connexion IA vérifiée", bool(v and v["ok"]), "jamais testée (utilisez le bouton de test)" if not v else
            (f"OK en {v['ms']} ms ({v['at']})" if v["ok"] else f"ÉCHEC : {v['error']}"))
        add("Sauvegarde de migration", True, app.extensions["migration_backup"] or "aucune migration nécessaire")
        return jsonify(checks=checks, config={"provider": cfg["LLM_PROVIDER"], "model": cfg["LLM_MODEL"],
                                              "api_key_set": llm.configured, "fallback_model": cfg["LLM_FALLBACK_MODEL"] or None,
                                              "admin_password_set": bool(cfg["ADMIN_PASSWORD"]), "log_file": str(cfg["LOG_DIR"] / "nexa.log")})

    @app.post("/api/diagnostics/llm-test")
    @admin_required(api=True)
    def llm_test():
        return jsonify(llm.test_connection())

    return app
