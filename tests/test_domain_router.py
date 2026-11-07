"""Tests for hybrid domain routing and specialist task planning."""
import tempfile
import unittest
from pathlib import Path

from oracle.domain_router import classify_research_intent, list_domains, resolve_domain
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
            self.assertEqual(len(run.tasks), 4)
            self.assertTrue(any("Domain-specialist lens: Identify organism" in task.description
                                for task in run.tasks))
            events = store.list_events(run.run_id)
            self.assertTrue(any(event["event_type"] == "domain_routed" for event in events))
            self.assertTrue(any("Domain routing: Biology & Medicine" in item
                                for item in run.findings))


    def test_registry_includes_humanities_and_applied_fields(self):
        keys = {item["key"] for item in list_domains()}
        expected = {
            "history_archaeology", "law_policy", "economics_business", "finance",
            "philosophy_ethics", "linguistics_literature", "education",
            "geography_urban", "politics_governance", "arts_culture",
            "religion_theology",
        }
        self.assertTrue(expected.issubset(keys))

    def test_auto_routes_non_scientific_and_applied_questions(self):
        cases = [
            ("How did the Roman Empire collapse?", "history_archaeology"),
            ("What does Indian constitutional law say about privacy?", "law_policy"),
            ("How does inflation affect small businesses?", "economics_business"),
            ("How should a portfolio measure downside risk?", "finance"),
            ("Is free will compatible with determinism?", "philosophy_ethics"),
            ("How do dialects change across generations?", "linguistics_literature"),
            ("Which teaching methods improve reading comprehension?", "education"),
            ("How does urban density affect commuting?", "geography_urban"),
            ("How do electoral systems shape representation?", "politics_governance"),
            ("How did cinema influence popular culture?", "arts_culture"),
            ("How have interpretations of Buddhist texts changed?", "religion_theology"),
        ]
        for question, expected in cases:
            with self.subTest(question=question):
                profile, _ = resolve_domain(question)
                self.assertEqual(profile.key, expected)

    def test_cross_domain_question_reports_secondary_domains(self):
        profile, diagnostics = resolve_domain(
            "How can machine learning improve medical diagnosis?"
        )
        self.assertIn(profile.key, {"computer_science_ai", "biology_medicine"})
        keys = {item["key"] for item in diagnostics["secondary_domains"]}
        self.assertTrue({"computer_science_ai", "biology_medicine"} & (keys | {profile.key}))
        self.assertIn("research_intent", diagnostics)

    def test_research_intent_is_separate_from_domain(self):
        self.assertEqual(
            classify_research_intent("Compare two datasets and test the causal mechanism")["primary"],
            "comparison",
        )
        self.assertIn(
            "data_analysis",
            classify_research_intent("Compare two datasets and test the causal mechanism")["all_detected"],
        )
        self.assertEqual(
            classify_research_intent("Prove the theorem")["primary"], "proof_or_derivation"
        )

    def test_unknown_topic_uses_general_profile_without_fake_confidence(self):
        profile, diagnostics = resolve_domain("What is the meaning of this unusual concept?")
        self.assertEqual(profile.key, "general_science")
        self.assertEqual(diagnostics["confidence"], 0.0)
        self.assertEqual(diagnostics["method"], "keyword_fallback")


if __name__ == "__main__":
    unittest.main()
