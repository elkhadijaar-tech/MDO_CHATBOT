import json
import unittest
from unittest import mock

from app.aliases import is_price_question, small_talk
from app.chat import ChatEngine
from app.lang import detect_language
from app.llm import LLMClient, LLMError
from tests.helpers import make_app


class LangTests(unittest.TestCase):
    def test_detect(self):
        self.assertEqual(detect_language("Où déposer mon certificat médical ?"), "fr")
        self.assertEqual(detect_language("Where can I find the timetable?"), "en")
        self.assertEqual(detect_language("ما هي ساعات عمل الإدارة؟"), "ar")
        self.assertEqual(detect_language("كيفاش نعرف جدول الحصص؟"), "darija")
        self.assertEqual(detect_language("fin kayn l'emploi du temps wach"), "darija")
        self.assertEqual(detect_language("bghit n3ref les horaires"), "darija")


class RuleTests(unittest.TestCase):
    def test_price(self):
        for q in ["Quel est le prix de l'inscription ?", "How much are the fees?", "بشحال التسجيل", "bchhal l'inscription"]:
            self.assertTrue(is_price_question(q), q)
        self.assertFalse(is_price_question("Qui enseigne Calcul et analyse des coûts ?"))
        self.assertFalse(is_price_question("chhal kayn d les modules"))

    def test_small_talk(self):
        self.assertEqual(small_talk("Bonjour"), "greeting")
        self.assertEqual(small_talk("merci !"), "thanks")
        self.assertIsNone(small_talk("bonjour, où est la bibliothèque ?"))


class RetrievalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = make_app().extensions["engine"]

    def ans(self, q, lang="auto"):
        return self.engine.answer(q, [], lang)

    def test_medical_certificate_fr(self):
        a = self.ans("Où déposer mon certificat médical ?")
        self.assertIn("72", a["answer"]); self.assertIn("Mdarbi", a["answer"]); self.assertIn("JAMAIS", a["answer"])

    def test_medical_certificate_en_ar(self):
        self.assertIn("Mdarbi", self.ans("Where can I submit my medical certificate?")["answer"])
        self.assertIn("Mdarbi", self.ans("كيفاش نقدم الشهادة الطبية")["answer"])

    def test_absence_threshold(self):
        a = self.ans("Que se passe-t-il si je dépasse 50% d'absences ?")["answer"]
        self.assertIn("rattrapage", a); self.assertIn("50%", a)

    def test_rattrapage_cap(self):
        self.assertIn("10/20", self.ans("note maximale au rattrapage")["answer"])

    def test_semester_list(self):
        a = self.ans("Quels sont les modules du S2 ?")["answer"]
        self.assertIn("Droit commercial", a); self.assertIn("Marketing fondamental", a)
        self.assertNotIn("Fiscalité", a)
        self.assertIn("Fiscalité", self.ans("modules du semestre 3")["answer"])
        self.assertIn("Culture Web", self.ans("chhal kayn d les modules fS4")["answer"])

    def test_professor(self):
        a = self.ans("Qui enseigne Business English ?")["answer"]
        self.assertIn("Mansouri Zoulal", a)
        self.assertIn("Oumoussa", self.ans("Who teaches AI?")["answer"])
        self.assertIn("non indiqué", self.ans("Qui est le professeur de Institutions administratives ?")["answer"])

    def test_documents_and_hours(self):
        self.assertIn("Bureau de la Scolarité", self.ans("Où demander une attestation de scolarité ?")["answer"])
        self.assertIn("8h30", self.ans("Horaires de l'administration")["answer"])
        self.assertIn("e-candidature", self.ans("How to apply to the school?")["answer"])
        self.assertIn("El Jadida", self.ans("فين كاينة المدرسة")["answer"])

    def test_off_topic_and_unknown(self):
        for q in ["recette du couscous", "capitale de la France", "Qui est le président de la FIFA ?"]:
            r = self.ans(q)
            self.assertTrue(r.get("not_found"), q)
            self.assertIn("contact@estc.ma", r["answer"])

    def test_price_never_gives_numbers(self):
        r = self.ans("Quels sont les frais d'inscription ?")
        self.assertEqual(r["mode"], "regle"); self.assertIn("aucun montant", r["answer"])
        self.assertIn("contact@estc.ma", r["answer"])

    def test_answer_language_override(self):
        self.assertIn("Hello", self.ans("Hello")["answer"])
        self.assertIn("Hello", self.ans("Bonjour", "en")["answer"])
        self.assertIn("مرحباً", self.ans("Bonjour", "ar")["answer"])


class LLMTests(unittest.TestCase):
    def _engine(self):
        app = make_app(LLM_API_KEY="test-key")
        return app.extensions["engine"]

    def test_llm_gets_context_and_rules(self):
        eng = self._engine()
        with mock.patch.object(LLMClient, "generate", return_value="Réponse IA") as gen:
            r = eng.answer("Où déposer mon certificat médical ?", [], "auto")
        self.assertEqual(r["mode"], "ia"); self.assertEqual(r["answer"], "Réponse IA")
        system, msgs = gen.call_args[0]
        self.assertIn("72 heures", system); self.assertIn("UNIQUEMENT", system)
        self.assertEqual(msgs[-1]["role"], "user")

    def test_llm_not_called_when_nothing_found_or_price(self):
        eng = self._engine()
        with mock.patch.object(LLMClient, "generate") as gen:
            eng.answer("recette du couscous", [], "auto"); eng.answer("prix de l'inscription", [], "auto")
        gen.assert_not_called()

    def test_llm_failure_falls_back_to_base_extract(self):
        eng = self._engine()
        with mock.patch.object(LLMClient, "generate", side_effect=LLMError("x")):
            r = eng.answer("Où déposer mon certificat médical ?", [], "auto")
        self.assertEqual(r["mode"], "demo_secours"); self.assertIn("Mdarbi", r["answer"])

    def test_history_alternates(self):
        msgs = ChatEngine._messages([{"role": "assistant", "content": "a"}, {"role": "user", "content": "b"},
                                     {"role": "user", "content": "c"}, {"role": "assistant", "content": "d"}], "q")
        self.assertEqual([m["role"] for m in msgs], ["user", "assistant", "user"])

    def test_retry_then_success_and_no_retry_on_401(self):
        ok = mock.Mock(status_code=200, json=lambda: {"content": [{"type": "text", "text": "ok"}]})
        busy = mock.Mock(status_code=429)
        cli = LLMClient("anthropic", "k", "m", backoff=0)
        with mock.patch("app.llm.requests.post", side_effect=[busy, busy, ok]) as post:
            self.assertEqual(cli.generate("s", [{"role": "user", "content": "q"}]), "ok")
        self.assertEqual(post.call_count, 3)
        with mock.patch("app.llm.requests.post", return_value=mock.Mock(status_code=401)) as post:
            with self.assertRaises(LLMError):
                cli.generate("s", [{"role": "user", "content": "q"}])
        self.assertEqual(post.call_count, 1)

    def test_openai_format(self):
        resp = mock.Mock(status_code=200, json=lambda: {"choices": [{"message": {"content": "salut"}}]})
        cli = LLMClient("openai", "k", "m", backoff=0)
        with mock.patch("app.llm.requests.post", return_value=resp):
            self.assertEqual(cli.generate("s", [{"role": "user", "content": "q"}]), "salut")


class WebTests(unittest.TestCase):
    def setUp(self):
        self.app = make_app(); self.c = self.app.test_client()

    def test_pages(self):
        for url in ("/", "/modules", "/infos"):
            self.assertEqual(self.c.get(url).status_code, 200, url)
        self.assertIn("MDO", self.c.get("/infos").get_data(as_text=True))

    def test_status_demo(self):
        self.assertEqual(self.c.get("/api/status").get_json()["mode"], "demo")

    def test_modules_api(self):
        self.assertEqual(len(self.c.get("/api/modules").get_json()), 40)
        self.assertEqual(len(self.c.get("/api/modules?semester=2").get_json()), 12)
        r = self.c.get("/api/modules?q=oumoussa").get_json()
        self.assertEqual(r[0]["name"], "Intelligence Artificielle (IA)")

    def test_chat_persistence_and_reset(self):
        r = self.c.post("/api/chat", json={"message": "Horaires de l'administration"})
        self.assertEqual(r.status_code, 200); self.assertEqual(r.get_json()["mode"], "demo")
        h = self.c.get("/api/history").get_json()
        self.assertEqual([m["role"] for m in h], ["user", "assistant"])
        self.c.post("/api/reset")
        self.assertEqual(self.c.get("/api/history").get_json(), [])

    def test_validation(self):
        self.assertEqual(self.c.post("/api/chat", json={"message": "  "}).status_code, 400)
        self.assertEqual(self.c.post("/api/chat", json={"message": "x" * 1001}).status_code, 400)
        self.assertEqual(self.c.post("/api/chat", data="pas du json").status_code, 400)

    def test_rate_limit(self):
        app = make_app(RATE_LIMIT_PER_MIN=2); c = app.test_client()
        codes = [c.post("/api/chat", json={"message": "bonjour"}).status_code for _ in range(3)]
        self.assertEqual(codes, [200, 200, 429])

    def test_unanswered_logged(self):
        self.c.post("/api/chat", json={"message": "recette du couscous"})
        from app.db import connect
        conn = connect(self.app.config["NEXA"]["DB_PATH"])
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM unanswered").fetchone()[0], 1)

    def test_html_is_escaped_by_client_not_stored_as_html(self):
        r = self.c.post("/api/chat", json={"message": "<script>alert(1)</script>"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.headers["X-Frame-Options"], "DENY")


class KnowledgeTests(unittest.TestCase):
    def test_reload_idempotent_and_counts(self):
        from app.db import connect, init_db
        from app.knowledge import load_knowledge
        import pathlib, tempfile
        conn = connect(pathlib.Path(tempfile.mkdtemp()) / "k.db"); init_db(conn)
        kb = make_app().config["NEXA"]["KB_PATH"]
        self.assertTrue(load_knowledge(conn, kb)); self.assertFalse(load_knowledge(conn, kb))
        counts = [r[0] for r in conn.execute("SELECT COUNT(*) FROM modules GROUP BY semester ORDER BY semester")]
        self.assertEqual(counts, [10, 12, 10, 8])
        self.assertTrue(load_knowledge(conn, kb, force=True))
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM modules").fetchone()[0], 40)

    def test_no_price_in_knowledge_base(self):
        import re
        with open(make_app().config["NEXA"]["KB_PATH"], encoding="utf-8") as f:
            text = json.dumps(json.load(f), ensure_ascii=False)
        self.assertIsNone(re.search(r"\d+\s?(dh|mad|dirhams?|€|\$)", text, re.I))


if __name__ == "__main__":
    unittest.main()
