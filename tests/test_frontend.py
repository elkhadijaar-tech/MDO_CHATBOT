"""Tests navigateur réels (Chromium via Playwright). Ignorés si Playwright/Chromium est indisponible."""
import threading
import unittest

from werkzeug.serving import make_server

from tests.helpers import make_app

try:
    from playwright.sync_api import sync_playwright
    _p = sync_playwright().start()
    _b = _p.chromium.launch()
    _b.close(); _p.stop()
    HAVE = True
except Exception:  # noqa: BLE001
    HAVE = False


@unittest.skipUnless(HAVE, "Playwright / Chromium indisponible")
class FrontendTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = make_server("127.0.0.1", 0, make_app(), threaded=True)
        cls.url = f"http://127.0.0.1:{cls.srv.server_port}"
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls.pw = sync_playwright().start(); cls.browser = cls.pw.chromium.launch()

    @classmethod
    def tearDownClass(cls):
        cls.browser.close(); cls.pw.stop(); cls.srv.shutdown()

    @staticmethod
    def wait_count(pg, selector, n, timeout=6.0):
        import time
        end = time.time() + timeout
        while time.time() < end:
            if pg.locator(selector).count() >= n:
                return True
            pg.wait_for_timeout(100)
        return False

    def page(self, w=1280, h=800):
        ctx = self.browser.new_context(viewport={"width": w, "height": h})
        pg = ctx.new_page(); self.errs = []
        pg.on("console", lambda m: self.errs.append(m.text) if m.type == "error" else None)
        pg.on("pageerror", lambda e: self.errs.append(str(e)))
        return pg

    def test_markdown_renderer_is_safe_and_complete(self):
        pg = self.page(); pg.goto(self.url + "/chat")
        out = pg.evaluate("""()=>{const d=document.createElement('div');
          d.appendChild(NexaMD.render("# Titre\\n\\n**gras** et _italique_ `code`\\n\\n- a\\n- b\\n\\n| A | B |\\n|---|---|\\n| 1 | 2 |\\n\\n```sql\\nSELECT 1;\\n```\\n\\n<img src=x onerror=window.__xss=1> [lien](javascript:alert(1)) [ok](https://estc.ma) www.estc.ma contact@estc.ma"));
          return {html:d.innerHTML,xss:!!window.__xss,tags:[...d.querySelectorAll('*')].map(e=>e.tagName)}}""")
        self.assertFalse(out["xss"]); self.assertNotIn("IMG", out["tags"])
        for tag in ("H2", "STRONG", "EM", "CODE", "UL", "TABLE", "PRE"):
            self.assertIn(tag, out["tags"], tag)
        self.assertNotIn('href="javascript', out["html"]); self.assertIn('href="https://estc.ma"', out["html"]); self.assertIn("mailto:contact@estc.ma", out["html"])
        self.assertEqual(self.errs, [])

    def test_chat_flow_actions_theme_and_collapse(self):
        pg = self.page(); pg.goto(self.url + "/chat?new=1")
        pg.fill("#input", "Calcule la TVA à 20 % sur 1 000 DH HT"); pg.keyboard.press("Enter")
        pg.wait_for_selector(".msg.bot .md"); self.assertIn("1 200,00", pg.inner_text(".msg.bot .md"))
        self.assertGreaterEqual(pg.locator(".msg.bot .md em").count(), 1)  # _italique_ rendu
        pg.fill("#input", "Et pour la SA ?"); pg.keyboard.press("Enter")
        self.assertTrue(self.wait_count(pg, ".msg.bot .md", 2))
        self.assertGreater(len(pg.locator(".msg.bot .md").last.inner_text()), 10)
        pg.locator(".msg.bot").last.hover(); pg.locator(".msg.bot").last.get_by_label("Réponse utile").click()
        pg.wait_for_selector(".toast"); pg.reload(); pg.wait_for_selector(".msg.bot")
        self.assertEqual(pg.locator(".msg.bot .btn-icon.on").count(), 1)  # feedback persisté
        pg.click("#theme-btn"); self.assertEqual(pg.get_attribute("html", "data-theme"), "dark")
        pg.reload(); self.assertEqual(pg.get_attribute("html", "data-theme"), "dark")
        pg.click("#collapse-btn"); self.assertEqual(pg.get_attribute("html", "data-collapsed"), "1")
        pg.reload(); self.assertEqual(pg.get_attribute("html", "data-collapsed"), "1")
        self.assertTrue(self.wait_count(pg, "#recent .rc", 1))
        self.assertEqual(self.errs, [])

    def test_mobile_no_horizontal_overflow_and_drawer(self):
        pg = self.page(390, 800)
        for path in ("/", "/chat", "/courses", "/modules", "/infos", "/knowledge", "/diagnostics"):
            pg.goto(self.url + path); pg.wait_for_timeout(250)
            self.assertLessEqual(pg.evaluate("document.documentElement.scrollWidth"), 391, path)
        pg.goto(self.url + "/"); pg.click("#burger"); pg.wait_for_timeout(300)
        self.assertGreaterEqual(pg.evaluate("document.getElementById('sidebar').getBoundingClientRect().left"), -1)
        pg.keyboard.press("Escape"); pg.wait_for_timeout(300)
        self.assertLess(pg.evaluate("document.getElementById('sidebar').getBoundingClientRect().right"), 5)
        self.assertEqual(self.errs, [])

    def test_courses_and_knowledge_pages_work(self):
        pg = self.page(); pg.goto(self.url + "/courses"); pg.wait_for_selector("#course-grid .card")
        self.assertEqual(pg.locator("#course-grid .card").count(), 19)
        pg.fill("#c-search", "Droit"); pg.wait_for_timeout(200); self.assertEqual(pg.locator("#course-grid .card").count(), 3)
        pg.goto(self.url + "/knowledge"); pg.wait_for_selector("#src-table tbody tr")
        pg.set_input_files("#f-file", {"name": "t.csv", "mimeType": "text/csv", "buffer": b"nom,ville\nAlice,Rabat\n"})
        pg.fill("#f-kb", "essai"); pg.click("#f-submit"); pg.wait_for_selector("dialog[open]")
        self.assertIn("indexed", pg.inner_text("#dlg-body")); pg.click("#dlg-close")
        self.assertTrue(self.wait_count(pg, "#src-table tbody tr", 3))
        self.assertEqual(self.errs, [])


if __name__ == "__main__":
    unittest.main()
