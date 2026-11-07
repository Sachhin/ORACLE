"""Tests for hybrid domain routing and specialist task planning."""
import tempfile
import unittest
from pathlib import Path

from oracle.domain_router import list_domains, resolve_domain
from oracle.models import ResearchMode, RunStatus
from oracle.orchestrator import OracleOrchestrator
from oracle.storage import ResearchStore


class DomainRouterTests(unittest.TestCase):
    def test_registry_covers_multiple_scientific_fields(self):
        keys = {item["key"] for item in list_domains()}
        self.assertGreaterEqual(len(keys), 8)
        self.assertIn("biology_medicine", keys)
        self.assertIn("physics_astronomy", keys)
        self.assertIn("computer_science_ai", keys)

    def test_auto_routes_biology_question(self):
        profile, diagnostics = resolve_domain(
            "Can we identify biological mechanisms involved in human longevity?"
        )
        self.assertEqual(profile.key, "biology_medicine")
        self.assertEqual(diagnostics["method"], "keyword_router")
        self.assertIn("PubMed/Europe PMC", profile.preferred_sources)

    def test_auto_routes_physics_question(self):
        profile, _ = resolve_domain("Can we derive a quantum gravity model?")
        self.assertEqual(profile.key, "physics_astronomy")

    def test_explicit_domain_overrides_auto(self):
        profile, diagnostics = resolve_domain(
            "How does aging work?", "computer_science_ai"
        )
        self.assertEqual(profile.key, "computer_science_ai")
        self.assertEqual(diagnostics["method"], "user_selected")

    def test_general_fallback_for_unclassified_question(self):
        profile, diagnostics = resolve_domain("What is the nature of this phenomenon?")
        self.assertEqual(profile.key, "general_science")
        self.assertEqual(diagnostics["confidence"], 0.0)

    def test_hybrid_profile_reaches_plan_and_is_persisted_as_event(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = ResearchStore(Path(tmp) / "oracle.sqlite3")
            run = OracleOrchestrator(store, research_domain="auto").run(
                "Can we identify biological mechanisms in human longevity?",
                ResearchMode.DEEP_RESEARCH, max_cycles=1,
            )
            self.assertEqual(run.status, RunStatus.COMPLETED)
            self.assertTrue(any(task.name.startswith("Biology & Medicine specialist:")
                                for task in run.tasks))
            events = store.list_events(run.run_id)
            self.assertTrue(any(event["kind"] == "domain_routed" for event in events))
            self.assertTrue(any("Domain routing: Biology & Medicine" in item
                                for item in run.findings))


if __name__ == "__main__":
    unittest.main()
