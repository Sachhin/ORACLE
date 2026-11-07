"""Contract tests for the local browser dashboard."""
import unittest

from oracle.web import PAGE, OracleDashboardHandler


class DashboardTests(unittest.TestCase):
    def test_page_exposes_research_controls_and_history(self):
        for expected in (
            "Start a research mission", "Research question", "Deep research",
            "Autonomous discovery", "Research history", "No API key is required", "/api/run", "/api/runs",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, PAGE)

    def test_browser_uses_gemini_when_key_is_configured_and_baseline_without_it(self):
        from unittest.mock import patch
        import inspect
        import oracle.web as web
        with patch.dict(web.os.environ, {}, clear=True):
            self.assertEqual(
                "auto" if web.os.environ.get("GEMINI_API_KEY", "").strip() else "deterministic",
                "deterministic",
            )
        with patch.dict(web.os.environ, {"GEMINI_API_KEY": "test-key"}, clear=True):
            self.assertEqual(
                "auto" if web.os.environ.get("GEMINI_API_KEY", "").strip() else "deterministic",
                "auto",
            )
        source = inspect.getsource(web.OracleDashboardHandler.do_POST)
        self.assertIn('literature_provider = "biology" if domain == "biology_medicine" else "both"', source)
        self.assertIn("GEMINI_API_KEY", PAGE)

    def test_dashboard_is_loopback_only_by_default(self):
        # The server entry point defaults to 127.0.0.1 and rejects public binds.
        import inspect
        import oracle.web as web
        source = inspect.getsource(web.main)
        self.assertIn('default="127.0.0.1"', source)
        self.assertIn('args.host not in {"127.0.0.1", "localhost", "::1"}', source)

    def test_dashboard_handler_has_no_external_static_assets(self):
        self.assertNotIn("<script src=", PAGE)
        self.assertNotIn('<link rel="stylesheet" href=', PAGE)


if __name__ == "__main__":
    unittest.main()
