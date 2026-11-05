"""Tests for ORACLE's offline research and knowledge foundation."""
import tempfile
import unittest
from pathlib import Path

from oracle.decision import choose_next_action
from oracle.knowledge import KnowledgeBase
from oracle.models import (
    Evidence, EvidenceKind, EvidenceStance, ExperimentStatus, Hypothesis,
    ResearchMode, ResearchRun, RunStatus,
)
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
        self.assertGreaterEqual(len(run.hypotheses), 2)
        self.assertEqual(len(run.hypothesis_groups), 1)
        self.assertEqual(len(run.hypothesis_groups[0].hypothesis_ids), 2)
        self.assertGreaterEqual(len(run.experiments), 1)
        self.assertEqual(self.store.load_run(run.run_id).status, RunStatus.COMPLETED)
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
        self.assertEqual(choose_next_action(1, 4, progress=False).action, "stop")

    def test_evidence_links_and_uncertainty_are_auditable(self):
        run = OracleOrchestrator(self.store).run("Test claim", max_cycles=1)
        kb = KnowledgeBase()
        claim = kb.add_claim(run, "Cell fate depends on signaling.")
        ev = Evidence("Signaling observation", "Dataset X", EvidenceKind.DATASET)
        run.evidence.append(ev)
        kb.link_evidence(run, claim.claim_id, ev.evidence_id, EvidenceStance.SUPPORTS, 0.7)
        assessment = kb.assess_claim(run, claim.claim_id)
        self.assertEqual(assessment.evidence_count, 1)
        self.assertAlmostEqual(assessment.confidence_estimate, 1.0)
        self.assertIn("not a calibrated probability", assessment.rationale)

    def test_contradictions_are_detected_and_not_silently_resolved(self):
        run = OracleOrchestrator(self.store).run("Test", max_cycles=1)
        kb = KnowledgeBase()
        a = kb.add_claim(run, "Gene X is required.")
        b = kb.add_claim(run, "Gene X is not required.")
        self.assertIn((a.claim_id, b.claim_id), kb.detect_contradictions(run))
        self.assertEqual(a.status, "unassessed")
        self.assertEqual(b.status, "unassessed")

    def test_competing_hypotheses_share_a_group(self):
        run = ResearchRun("Test")
        kb = KnowledgeBase()
        first = Hypothesis("Model A", "Reason A")
        second = Hypothesis("Model B", "Reason B")
        group = kb.add_hypothesis(run, first)
        same = kb.add_hypothesis(run, second, group.group_id)
        self.assertEqual(group.group_id, same.group_id)
        self.assertEqual(len(group.hypothesis_ids), 2)

    def test_resume_interrupted_run_without_resetting_history(self):
        run = OracleOrchestrator(self.store).run("Resume this", max_cycles=1)
        run.status = RunStatus.PAUSED
        self.store.save_run(run)
        resumed = OracleOrchestrator(self.store).resume(run.run_id, additional_cycles=1)
        self.assertEqual(resumed.status, RunStatus.COMPLETED)
        self.assertEqual(resumed.current_cycle, 2)
        self.assertEqual(len(resumed.evidence), 2)
        self.assertEqual(resumed.run_id, run.run_id)


if __name__ == "__main__":
    unittest.main()
