import csv
import hashlib
import io
import json
import pathlib
import sqlite3
import tempfile
import unittest
from unittest import mock

from app.calc import try_calc
from app.chat import ChatEngine, contextualize, is_followup
from app.db import SCHEMA, connect, init_db
from app.llm import LLMClient, LLMError
from app.prompts import build_system, detect_task, trim_history
from app.retrieval import split_queries
from tests.helpers import make_app

H = {"X-Requested-With": "fetch"}


def engine(**kw):
    return make_app(**kw).extensions["engine"]


class CourseRetrievalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.e = engine()

    def a(self, q, hist=None):
        return self.e.answer(q, hist or [], "auto")

    def test_course_answers(self):
        cases = [("Qu'est-ce que la SARL ?", "50 associés"), ("Quelle est la formule de la variance ?", "σ"),
                 ("période d'essai pour un cadre", "3 mois"), ("comment faire un amortissement dégressif", "coefficient fiscal"),
                 ("formule de la loi binomiale", "np(1"), ("Quels sont les 7 étapes de vente", "SONCAS"),
                 ("what is the PODC process", "Planifier"), ("كيفاش كنحسب الضريبة على القيمة المضافة", "TVA"),
                 ("SQL JOIN example", "JOIN"), ("capital minimum d'une SA", "300 000")]
        for q, expect in cases:
            r = self.a(q)
            self.assertFalse(r.get("not_found"), q)
            self.assertIn(expect, r["answer"], q)
            self.assertEqual(r["kb"], "cours", q)

    def test_admin_still_routed_to_admin_kb(self):
        r = self.a("Où déposer mon certificat médical ?")
        self.assertEqual(r["kb"], "onboarding"); self.assertIn("72", r["answer"])

    def test_mode_filter(self):
        r = self.e.answer("Qu'est-ce que la SARL ?", [], "auto", "admin")
        self.assertTrue(r.get("not_found"))
        r = self.e.answer("certificat médical", [], "auto", "cours")
        self.assertTrue(r.get("not_found"))

    def test_off_topic(self):
        for q in ["capitale de la France", "recette du couscous", "Qui a gagné la coupe du monde ?"]:
            self.assertTrue(self.a(q).get("not_found"), q)

    def test_multi_query(self):
        self.assertEqual(split_queries("Qu'est-ce que la SARL et comment calculer la TVA ?")[:1], ["Qu'est-ce que la SARL"])
        r = self.a("Qu'est-ce que la SARL et comment calculer la TVA ?")
        self.assertTrue(any("Business Law" in s for s in r["sources"])); self.assertTrue(any("Financial Accounting" in s for s in r["sources"]))

    def test_followup_uses_previous_question(self):
        hist = [{"role": "user", "content": "Qu'est-ce que la SARL ?"}, {"role": "assistant", "content": "x"}]
        self.assertTrue(is_followup("Et pour la SA ?"))
        self.assertIn("SARL", contextualize("Et pour la SA ?", hist))
        self.assertEqual(contextualize("Quelle est la formule de la variance ?", hist), "Quelle est la formule de la variance ?")
        r = self.a("Et pour la SA ?", hist)
        self.assertIn("300 000", r["answer"])
        self.assertTrue(self.a("Donne un exemple", hist)["sources"])

    def test_price_rule_beats_course(self):
        r = self.a("Quel est le prix de la formation continue ?")
        self.assertEqual(r["mode"], "regle"); self.assertIn("aucun montant", r["answer"])

    def test_generative_task_needs_ai_in_demo(self):
        r = self.a("Génère un QCM sur la TVA")
        self.assertEqual(r["mode"], "demo"); self.assertEqual(r["task"], "qcm"); self.assertIn("mode IA", r["answer"])


class CalcTests(unittest.TestCase):
    def test_tva(self):
        r = try_calc("Calcule la TVA à 20% sur 1000 DH HT", "fr")
        self.assertIn("200,00", r["answer"]); self.assertIn("1 200,00", r["answer"])
        r = try_calc("Un article coûte 1200 DH TTC, TVA 20%, quel est le HT ?", "fr")
        self.assertIn("1 000,00", r["answer"])
        self.assertIn("1,200.00", try_calc("VAT 20% on 1000 MAD HT", "en")["answer"])

    def test_interest(self):
        self.assertIn("11 576,25", try_calc("intérêts composés capital 10000 DH taux 5% pendant 3 ans", "fr")["answer"])
        r = try_calc("Intérêts simples : 5000 DH à 6% pendant 9 mois", "fr")["answer"]
        self.assertIn("225,00", r); self.assertIn("5 225,00", r)
        r = try_calc("escompte commercial d'un effet de 12000 DH à 8% pendant 45 jours", "fr")["answer"]
        self.assertIn("120,00", r); self.assertIn("11 880,00", r)

    def test_no_guessing(self):
        for q in ["Quelle est la formule de l'intérêt composé ?", "calcule la TVA sur 1000 DH HT",
                  "intérêts composés 10000 DH et 20000 DH à 5% pendant 3 ans", "intérêts composés 10000 DH 5% 6 mois"]:
            self.assertIsNone(try_calc(q, "fr"), q)


class PromptTests(unittest.TestCase):
    def test_tasks(self):
        self.assertEqual(detect_task("Donne-moi un QCM sur le droit"), "qcm")
        self.assertEqual(detect_task("Fais un résumé du module 5"), "resume")
        self.assertEqual(detect_task("différence entre SA et SARL"), "comparaison")
        self.assertEqual(detect_task("Explique la partie double"), "explication")
        self.assertIsNone(detect_task("Où est la bibliothèque ?"))

    def test_course_vs_admin_prompt(self):
        ch = [{"title": "Cours — 11. Business Law", "text": "SARL ...", "location": "Module 11", "verification": "VERIFIED_USER_DATABASE"}]
        course = build_system("course", ch, "qcm", "fr")
        self.assertIn("tuteur", course); self.assertIn("QCM", course); self.assertIn("[1] Cours — 11. Business Law", course)
        self.assertIn("Complément général", course)
        admin = build_system("admin", ch, None, "ar")
        self.assertIn("UNIQUEMENT", admin); self.assertIn("العربية", admin)

    def test_history_trim_keeps_recent_and_summarizes_old(self):
        hist = []
        for i in range(30):
            hist += [{"role": "user", "content": f"question numéro {i} " + "x" * 200}, {"role": "assistant", "content": "r" * 300}]
        kept, summary = trim_history(hist, 2000)
        self.assertLess(len(kept), len(hist)); self.assertEqual(kept[-1], hist[-1])
        self.assertIn("question numéro 26", summary); self.assertNotIn("question numéro 0 ", summary); self.assertNotIn("question numéro 28", summary)
        k2, s2 = trim_history(hist[:2], 2000)
        self.assertEqual((len(k2), s2), (2, ""))

    def test_llm_receives_course_prompt_and_history(self):
        e = engine(LLM_API_KEY="k")
        hist = [{"role": "user", "content": "Qu'est-ce que la SARL ?"}, {"role": "assistant", "content": "Une société..."}]
        with mock.patch.object(LLMClient, "generate", return_value="ok") as gen:
            r = e.answer("Et pour la SA ?", hist)
        system, msgs = gen.call_args[0]
        self.assertIn("tuteur", system); self.assertIn("300 000", system)
        self.assertEqual([m["role"] for m in msgs], ["user", "assistant", "user"])
        self.assertEqual(r["mode"], "ia")


class LLMClientTests(unittest.TestCase):
    def test_usage_model_and_fallback_label(self):
        ok = mock.Mock(status_code=200, json=lambda: {"content": [{"type": "text", "text": "salut"}], "usage": {"input_tokens": 11, "output_tokens": 7}})
        bad = mock.Mock(status_code=400)
        cli = LLMClient("anthropic", "k", "main", backoff=0, fallback_model="backup")
        with mock.patch("app.llm.requests.post", side_effect=[bad, ok]):
            self.assertEqual(cli.generate("s", [{"role": "user", "content": "q"}]), "salut")
        self.assertEqual(cli.last_model, "backup"); self.assertEqual(cli.last_usage, {"in": 11, "out": 7})
        cli2 = LLMClient("anthropic", "k", "main", backoff=0)
        with mock.patch("app.llm.requests.post", side_effect=[bad]):
            with self.assertRaises(LLMError):
                cli2.generate("s", [{"role": "user", "content": "q"}])

    def test_gemini_uses_openai_compatible_endpoint(self):
        resp = mock.Mock(status_code=200, json=lambda: {"choices": [{"message": {"content": "hi"}}], "usage": {"prompt_tokens": 3, "completion_tokens": 2}})
        cli = LLMClient("gemini", "k", "gemini-x", backoff=0)
        with mock.patch("app.llm.requests.post", return_value=resp) as post:
            cli.generate("s", [{"role": "user", "content": "q"}])
        self.assertIn("generativelanguage.googleapis.com", post.call_args[0][0]); self.assertEqual(cli.last_usage["in"], 3)

    def test_connection_test_states(self):
        cli = LLMClient("anthropic", "", "m")
        self.assertFalse(cli.test_connection()["ok"])
        cli = LLMClient("anthropic", "k", "m", backoff=0, retries=1)
        with mock.patch("app.llm.requests.post", return_value=mock.Mock(status_code=401)):
            r = cli.test_connection()
        self.assertFalse(r["ok"]); self.assertIn("clé API refusée", r["error"])
        ok = mock.Mock(status_code=200, json=lambda: {"content": [{"type": "text", "text": "ok"}]})
        with mock.patch("app.llm.requests.post", return_value=ok):
            self.assertTrue(cli.test_connection()["ok"])
        self.assertTrue(cli.verified["ok"])


class WebV2Tests(unittest.TestCase):
    def setUp(self):
        self.app = make_app(); self.c = self.app.test_client()

    def test_pages_and_status(self):
        for u in ("/", "/chat", "/courses", "/modules", "/infos", "/knowledge", "/diagnostics"):
            self.assertEqual(self.c.get(u).status_code, 200, u)
        s = self.c.get("/api/status").get_json()
        self.assertEqual((s["mode"], s["web_research"], s["connection_verified"]), ("demo", False, None))
        self.assertEqual(len(self.c.get("/api/courses").get_json()), 19)
        self.assertEqual({k["name"] for k in self.c.get("/api/kbs").get_json()}, {"onboarding", "cours"})

    def test_security_headers_and_request_id(self):
        r = self.c.get("/")
        self.assertIn("script-src 'self'", r.headers["Content-Security-Policy"]); self.assertTrue(r.headers["X-Request-ID"])

    def test_conversation_isolation_and_management(self):
        self.c.post("/api/chat", json={"message": "Qu'est-ce que la SARL ?"})
        lst = self.c.get("/api/conversations").get_json()
        self.assertEqual(len(lst["conversations"]), 1); cid = lst["conversations"][0]["id"]
        self.assertTrue(lst["conversations"][0]["title"].startswith("Qu'est-ce"))
        other = self.app.test_client()
        self.assertEqual(other.get("/api/conversations").get_json()["conversations"], [])
        self.assertEqual(other.post(f"/api/conversations/{cid}/open").status_code, 404)
        self.assertEqual(other.delete(f"/api/conversations/{cid}").status_code, 404)
        self.c.post("/api/reset")
        self.assertEqual(self.c.get("/api/history").get_json(), [])
        self.assertEqual(self.c.post(f"/api/conversations/{cid}/open").status_code, 200)
        self.assertEqual(len(self.c.get("/api/history").get_json()), 2)
        self.assertEqual(self.c.delete(f"/api/conversations/{cid}").status_code, 200)
        self.assertEqual(self.c.get("/api/history").get_json(), [])

    def test_followup_over_http_keeps_context(self):
        self.c.post("/api/chat", json={"message": "Qu'est-ce que la SARL ?"})
        r = self.c.post("/api/chat", json={"message": "Et pour la SA ?"}).get_json()
        self.assertIn("300 000", r["answer"])

    def test_feedback_and_export(self):
        r = self.c.post("/api/chat", json={"message": "Horaires de l'administration"}).get_json()
        mid = r["message_id"]
        self.assertEqual(self.c.post("/api/feedback", json={"message_id": mid, "value": 1}).status_code, 200)
        self.assertEqual(self.c.get("/api/history").get_json()[-1]["feedback"], 1)
        self.assertEqual(self.c.post("/api/feedback", json={"message_id": mid, "value": 5}).status_code, 400)
        self.assertEqual(self.app.test_client().post("/api/feedback", json={"message_id": mid, "value": 1}).status_code, 404)
        exp = self.c.get("/api/export")
        self.assertIn("8h30", exp.get_data(as_text=True)); self.assertIn("attachment", exp.headers["Content-Disposition"])

    def test_chat_mode_param_and_log_has_no_question_text(self):
        r = self.c.post("/api/chat", json={"message": "phrase secrète unique 12345 tva", "mode": "cours"}).get_json()
        self.assertIn("mode", r)
        log = (self.app.config["NEXA"]["LOG_DIR"] / "nexa.log").read_text(encoding="utf-8")
        self.assertIn("chat mode=", log); self.assertNotIn("secrète", log)

    def test_diagnostics(self):
        d = self.c.get("/api/diagnostics").get_json()
        names = {c["name"]: c for c in d["checks"]}
        self.assertTrue(names["Index de recherche"]["ok"]); self.assertFalse(names["Recherche web"]["ok"])
        self.assertFalse(names["Fournisseur IA"]["ok"]); self.assertNotIn("api_key", json.dumps(d).replace("api_key_set", ""))
        r = self.c.post("/api/diagnostics/llm-test", headers=H).get_json()
        self.assertFalse(r["ok"])


class AdminTests(unittest.TestCase):
    def test_non_local_denied_without_password(self):
        c = make_app().test_client()
        env = {"REMOTE_ADDR": "203.0.113.9"}
        self.assertEqual(c.get("/knowledge", environ_overrides=env).status_code, 403)
        self.assertEqual(c.get("/api/knowledge", environ_overrides=env).status_code, 403)
        self.assertEqual(c.post("/api/knowledge/import", environ_overrides=env, headers=H).status_code, 403)

    def test_password_login_flow_and_csrf_header(self):
        c = make_app(ADMIN_PASSWORD="s3cret").test_client()
        self.assertEqual(c.get("/knowledge").status_code, 302)
        self.assertEqual(c.get("/api/knowledge").status_code, 403)
        self.assertEqual(c.post("/admin/login", data={"password": "nope"}).status_code, 401)
        self.assertEqual(c.post("/admin/login", data={"password": "s3cret"}).status_code, 302)
        self.assertEqual(c.get("/knowledge").status_code, 200)
        self.assertEqual(c.get("/api/knowledge").status_code, 200)
        self.assertEqual(c.post("/api/diagnostics/llm-test").status_code, 403)  # sans en-tête X-Requested-With
        self.assertEqual(c.post("/api/diagnostics/llm-test", headers=H).status_code, 200)

    def test_login_rate_limited(self):
        c = make_app(ADMIN_PASSWORD="s3cret").test_client()
        codes = [c.post("/admin/login", data={"password": "x"}).status_code for _ in range(7)]
        self.assertEqual(codes[-1], 401); self.assertEqual(len(set(codes)), 1)
        r = c.post("/admin/login", data={"password": "s3cret"})
        self.assertEqual(r.status_code, 401)


class IngestTests(unittest.TestCase):
    def setUp(self):
        self.app = make_app(); self.c = self.app.test_client()
        self.up = self.app.config["NEXA"]["UPLOAD_DIR"]

    def imp(self, name, data, kb="documents", label=""):
        return self.c.post("/api/knowledge/import", headers=H, data={"file": (io.BytesIO(data), name), "kb": kb, "label": label},
                           content_type="multipart/form-data")

    def ask(self, q, mode="auto"):
        return self.c.post("/api/chat", json={"message": q, "mode": mode}).get_json()

    def test_csv_import_searchable_with_provenance_and_dedupe(self):
        buf = io.StringIO(); w = csv.writer(buf, delimiter=";")
        w.writerow(["Module", "Enseignant", "Salle"]); w.writerow(["Zymologie appliquée", "Mme Quarkenstein", "B12"])
        w.writerow(["Zymologie appliquée", "Mme Quarkenstein", "B12"]); w.writerow(["Optique", "M. Lumen", ""])
        r = self.imp("planning.csv", buf.getvalue().encode("utf-8"), "planning", "Planning S2")
        self.assertEqual(r.status_code, 200, r.get_data(as_text=True)); rep = r.get_json()["report"]
        self.assertEqual((rep["chunks_indexed"], rep["duplicates_skipped"]), (2, 1)); self.assertEqual(rep["columns"], ["Module", "Enseignant", "Salle"])
        a = self.ask("Qui enseigne la Zymologie appliquée ?")
        self.assertIn("Quarkenstein", a["answer"]); self.assertEqual(a["kb"], "planning")
        conn = connect(self.app.config["NEXA"]["DB_PATH"])
        row = conn.execute("SELECT * FROM chunks WHERE kb='planning' LIMIT 1").fetchone()
        self.assertEqual(row["verification"], "NEEDS_VERIFICATION"); self.assertTrue(row["location"]); self.assertTrue(row["source_id"])
        kb = [k for k in self.c.get("/api/kbs").get_json() if k["name"] == "planning"][0]
        self.assertEqual((kb["label"], kb["chunks"], kb["sources"]), ("Planning S2", 2, 1))
        again = self.imp("planning-copie.csv", buf.getvalue().encode("utf-8"), "planning")
        self.assertEqual(again.status_code, 400); self.assertIn("déjà importé", again.get_json()["error"])

    def test_sqlite_import_readonly_inventory_and_original_untouched(self):
        p = pathlib.Path(tempfile.mkdtemp()) / "ext.sqlite"
        con = sqlite3.connect(p)
        con.executescript("CREATE TABLE prof(id INTEGER PRIMARY KEY, nom TEXT); CREATE TABLE cours(id INTEGER PRIMARY KEY, titre TEXT, prof_id INTEGER REFERENCES prof(id));"
                          "CREATE INDEX ix ON cours(titre); INSERT INTO prof VALUES (1,'Mme Quarkenstein'); INSERT INTO cours VALUES (1,'Zymologie',1);"
                          "CREATE TABLE \"evil\"\"; DROP TABLE prof;--\"(x TEXT); INSERT INTO \"evil\"\"; DROP TABLE prof;--\" VALUES ('piege');")
        con.commit(); con.close()
        data = p.read_bytes(); before = hashlib.sha256(data).hexdigest()
        r = self.imp("ext.sqlite", data, "externe"); self.assertEqual(r.status_code, 200, r.get_data(as_text=True))
        rep = r.get_json()["report"]; tables = {t["table"]: t for t in rep["tables"]}
        self.assertEqual(tables["cours"]["rows"], 1); self.assertEqual(tables["cours"]["foreign_keys"][0]["references"], "prof.id")
        self.assertEqual(tables["prof"]["primary_key"], ["id"]); self.assertIn("ix", tables["cours"]["indexes"])
        self.assertIn("Quarkenstein", self.ask("Quarkenstein", "auto")["answer"])
        stored = next(self.up.iterdir()); self.assertEqual(hashlib.sha256(stored.read_bytes()).hexdigest(), before)
        chk = sqlite3.connect(stored); self.assertEqual(chk.execute("SELECT COUNT(*) FROM prof").fetchone()[0], 1); chk.close()

    def test_json_txt_docx_xlsx_pptx_pdf(self):
        r = self.imp("rows.json", json.dumps([{"sujet": "Quantique", "chef": "Dr Zorg"}, {"sujet": "Optique", "chef": "Dr Lux"}]).encode())
        self.assertEqual(r.get_json()["report"]["chunks_indexed"], 2)
        r = self.imp("cours.txt", ("1. Introduction\nLe gluon est un boson de jauge.\n\n2. Conclusion\nFin du document.\n" + "Texte. " * 5).encode())
        self.assertGreaterEqual(r.get_json()["report"]["chunks_indexed"], 2)
        import docx
        d = docx.Document(); d.add_heading("Chapitre Zeta", 1); d.add_paragraph("Le théorème de Zeta stipule que tout est relatif.")
        t = d.add_table(rows=2, cols=2); t.cell(0, 0).text = "A"; t.cell(0, 1).text = "B"; t.cell(1, 0).text = "valeur1"; t.cell(1, 1).text = "valeur2"
        b = io.BytesIO(); d.save(b); r = self.imp("zeta.docx", b.getvalue()); rep = r.get_json()["report"]
        self.assertEqual((rep["headings"], rep["tables"]), (1, 1)); self.assertIn("Zeta", self.ask("théorème de Zeta")["answer"])
        import openpyxl
        wb = openpyxl.Workbook(); ws = wb.active; ws.title = "Notes"; ws.append(["Etudiant", "Note"]); ws.append(["Alice", 17]); b = io.BytesIO(); wb.save(b)
        r = self.imp("notes.xlsx", b.getvalue()); self.assertEqual(r.get_json()["report"]["sheets"][0]["sheet"], "Notes")
        from pptx import Presentation
        pr = Presentation(); s = pr.slides.add_slide(pr.slide_layouts[1]); s.shapes.title.text = "Diapositive Omega"; s.placeholders[1].text = "contenu omega unique"
        b = io.BytesIO(); pr.save(b); r = self.imp("omega.pptx", b.getvalue()); self.assertEqual(r.get_json()["report"]["slides_with_text"], 1)
        stream = b"BT /F1 14 Tf 20 100 Td (Le theoreme de Bayes pdfunique) Tj ET"
        objs = [b"<</Type/Catalog/Pages 2 0 R>>", b"<</Type/Pages/Kids[3 0 R]/Count 1>>",
                b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 300 200]/Contents 4 0 R/Resources<</Font<</F1 5 0 R>>>>>>",
                b"<</Length %d>>\nstream\n" % len(stream) + stream + b"\nendstream", b"<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>"]
        pdf, offs = b"%PDF-1.4\n", []
        for i, o in enumerate(objs, 1):
            offs.append(len(pdf)); pdf += b"%d 0 obj\n" % i + o + b"\nendobj\n"
        xref = len(pdf); pdf += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1)
        pdf += b"".join(b"%010d 00000 n \n" % o for o in offs) + b"trailer\n<</Root 1 0 R/Size %d>>\nstartxref\n%d\n%%%%EOF" % (len(objs) + 1, xref)
        r = self.imp("bayes.pdf", pdf); self.assertEqual(r.status_code, 200, r.get_data(as_text=True))
        self.assertEqual(r.get_json()["report"]["pages"], 1)

    def test_refusals(self):
        self.assertIn("exécutés", self.imp("dump.sql", b"DROP TABLE x;").get_json()["error"])
        self.assertEqual(self.imp("x.exe", b"MZ").status_code, 400)
        self.assertEqual(self.imp("vide.txt", b"").status_code, 400)
        self.assertIn("SQLite", self.imp("faux.sqlite", b"not a database at all").get_json()["error"])
        self.assertEqual(self.imp("casse.docx", b"PK-corrompu").status_code, 400)
        self.assertEqual(self.imp("mauvais.json", b"{oops").status_code, 400)
        self.assertEqual(self.imp("a.csv", b"a,b\n1,2\n", kb="!!!").status_code, 400)
        conn = connect(self.app.config["NEXA"]["DB_PATH"])
        self.assertGreaterEqual(conn.execute("SELECT COUNT(*) FROM sources WHERE status='failed'").fetchone()[0], 1)

    def test_reindex_delete_rollback_and_schema_change(self):
        p = pathlib.Path(tempfile.mkdtemp()) / "a.sqlite"
        con = sqlite3.connect(p); con.executescript("CREATE TABLE t(a TEXT); INSERT INTO t VALUES ('alphaunique');"); con.commit(); con.close()
        sid = self.imp("a.sqlite", p.read_bytes(), "tmpkb").get_json()["report"]["source_id"]
        self.assertIn("alphaunique", self.ask("alphaunique")["answer"])
        r = self.c.post(f"/api/knowledge/sources/{sid}/reindex", headers=H); self.assertEqual(r.status_code, 200)
        self.assertNotIn("schema_changed", r.get_json()["report"])
        stored = next(self.up.iterdir()); con = sqlite3.connect(stored)  # modification du fichier stocké => schéma différent
        con.executescript("ALTER TABLE t ADD COLUMN b TEXT; UPDATE t SET b='betaunique';"); con.commit(); con.close()
        r = self.c.post(f"/api/knowledge/sources/{sid}/reindex", headers=H); self.assertTrue(r.get_json()["report"]["schema_changed"])
        self.assertIn("betaunique", self.ask("betaunique")["answer"])
        self.assertEqual(self.c.delete(f"/api/knowledge/sources/{sid}", headers=H).status_code, 200)
        gone = self.ask("betaunique"); self.assertEqual(gone["sources"], []); self.assertIn("contact@estc.ma", gone["answer"]); self.assertTrue(stored.exists())
        builtin = [s for s in self.c.get("/api/knowledge").get_json()["sources"] if s["builtin"]][0]["id"]
        self.assertEqual(self.c.delete(f"/api/knowledge/sources/{builtin}", headers=H).status_code, 400)
        self.assertEqual(self.c.post(f"/api/knowledge/sources/{builtin}/reindex", headers=H).status_code, 200)
        self.assertEqual({k["name"] for k in self.c.get("/api/kbs").get_json() if k["builtin"]}, {"onboarding", "cours"})
        self.assertIn("72", self.ask("certificat médical")["answer"])

    def test_report_endpoint(self):
        sid = self.imp("a.csv", b"x,y\n1,2\n").get_json()["report"]["source_id"]
        self.assertEqual(self.c.get(f"/api/knowledge/sources/{sid}/report").get_json()["report"]["status"], "indexed")


class MigrationTests(unittest.TestCase):
    def test_v1_database_is_backed_up_and_migrated(self):
        d = pathlib.Path(tempfile.mkdtemp()); p = d / "old.db"
        con = sqlite3.connect(p)
        con.executescript("""CREATE TABLE chunks (id INTEGER PRIMARY KEY AUTOINCREMENT, section_id TEXT, title TEXT NOT NULL, text TEXT NOT NULL, kind TEXT NOT NULL DEFAULT 'item', semester INTEGER);
        CREATE TABLE conversations (id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE messages (id INTEGER PRIMARY KEY AUTOINCREMENT, conversation_id INTEGER NOT NULL, role TEXT NOT NULL, content TEXT NOT NULL, mode TEXT, language TEXT, sources TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
        INSERT INTO conversations DEFAULT VALUES; INSERT INTO messages (conversation_id, role, content) VALUES (1,'user','ancienne question');""")
        con.commit(); con.close()
        conn = connect(p); backup = init_db(conn, p)
        self.assertTrue(backup and pathlib.Path(backup).exists())
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(messages)")}
        self.assertTrue({"model", "kb_used", "feedback"} <= cols)
        self.assertEqual(conn.execute("SELECT content FROM messages").fetchone()[0], "ancienne question")
        old = sqlite3.connect(backup); self.assertNotIn("model", {r[1] for r in old.execute("PRAGMA table_info(messages)")}); old.close()
        self.assertEqual(init_db(connect(p), p), "")  # idempotent : pas de nouvelle sauvegarde


if __name__ == "__main__":
    unittest.main()
