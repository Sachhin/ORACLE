"""Offline integration and integrity tests."""
import tempfile
import unittest
from pathlib import Path

from oracle.decision import choose_next_action
from oracle.models import ExperimentStatus, ResearchMode, RunStatus
from oracle.orchestrator import OracleOrchestrator
from oracle.storage import ResearchStore


class OracleTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = ResearchStore(Path(self.tmp.name) / "test.sqlite3")

    def tearDown(self):
        self.tmp.cleanup()

    def test_empty_question_rejected(self):
        with self.assertRaises(ValueError):
            OracleOrchestrator(self.store).run("  ")

    def test_cycle_budget_validated(self):
        with self.assertRaises(ValueError):
            OracleOrchestrator(self.store).run("A question?", max_cycles=0)

    def test_integrated_run_completes_and_persists(self):
        run = OracleOrchestrator(self.store).run(
            "How does a fertilized egg develop into an organism?", max_cycles=2
        )
        self.assertEqual(run.status, RunStatus.COMPLETED)
        self.assertEqual(run.current_cycle, 2)
        self.assertGreaterEqual(len(run.evidence), 1)
        self.assertGreaterEqual(len(run.hypotheses), 1)
        self.assertGreaterEqual(len(run.experiments), 1)
        payload = self.store.load_payload(run.run_id)
        self.assertIsNotNone(payload)
        self.assertEqual(payload["status"], "completed")
        self.assertGreater(len(self.store.list_events(run.run_id)), 0)

    def test_experiment_is_proposed_not_performed(self):
        run = OracleOrchestrator(self.store).run("Test question", max_cycles=1)
        self.assertTrue(all(e.status == ExperimentStatus.PROPOSED for e in run.experiments))

    def test_research_only_mode_skips_discovery_directions(self):
        run = OracleOrchestrator(self.store).run(
            "Test question", ResearchMode.DEEP_RESEARCH, max_cycles=1
        )
        self.assertEqual(run.findings.count("Look for overlooked mechanisms"), 0)

    def test_decision_stops_on_no_progress(self):
        decision = choose_next_action(1, 4, progress=False)
        self.assertEqual(decision.action, "stop")


if __name__ == "__main__":
    unittest.main()
