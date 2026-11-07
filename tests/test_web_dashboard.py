"""Contract tests for the local browser dashboard."""
import unittest

from oracle.web import PAGE, OracleDashboardHandler


class DashboardTests(unittest.TestCase):
    def test_page_exposes_research_controls_and_history(self):
        for expected in (
            "Start a research mission", "Research question", "Deep research",
            "Autonomous discovery", "Research history", "No model API key or paid AI API is used", "Discover GEO supplementary files", "Download and analyze supported GEO matrices", "/api/run", "/api/runs",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, PAGE)

    def test_browser_uses_deterministic_agents_without_model_provider_flags(self):
        import inspect
        import oracle.web as web
        source = inspect.getsource(web.OracleDashboardHandler.do_POST)
        self.assertNotIn("GEMINI_API_KEY", source)
        self.assertIn('literature_provider = "auto"', source)
        self.assertIn('"--provider", literature_provider', source)
        self.assertIn("No model API key or paid AI API is used", PAGE)
        self.assertIn('command.append("--discover-geo-files")', source)
        self.assertIn('command.append("--analyze-geo-files")', source)

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
