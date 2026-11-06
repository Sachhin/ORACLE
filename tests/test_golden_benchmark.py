"""Golden-question integrity benchmark for the deterministic offline baseline."""
import json
import tempfile
import unittest
from pathlib import Path

from oracle.models import EvidenceKind, EvidenceStance, ExperimentStatus, HypothesisStatus, RunStatus
from oracle.orchestrator import OracleOrchestrator
from oracle.storage import ResearchStore


class GoldenIntegrityBenchmark(unittest.TestCase):
    def test_golden_questions_preserve_scientific_integrity_invariants(self):
        fixture = Path(__file__).parent.parent / "benchmarks" / "golden_questions.json"
        questions = json.loads(fixture.read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(questions), 8)
        with tempfile.TemporaryDirectory() as directory:
            store = ResearchStore(Path(directory) / "benchmark.sqlite3")
            for item in questions:
                with self.subTest(question_id=item["id"]):
                    run = OracleOrchestrator(store).run(item["question"], max_cycles=1)
                    self.assertEqual(run.status, RunStatus.COMPLETED)
                    self.assertTrue(run.tasks)
                    self.assertGreaterEqual(len(run.hypotheses), 2)
                    self.assertTrue(all(
                        hypothesis.status == HypothesisStatus.PROPOSED
                        for hypothesis in run.hypotheses
                    ))
                    self.assertTrue(all(
                        experiment.status == ExperimentStatus.PROPOSED
                        and experiment.execution_kind == "proposed"
                        for experiment in run.experiments
                    ))
                    self.assertEqual(run.sources, [])
                    self.assertTrue(all(
                        evidence.kind == EvidenceKind.INFERENCE
                        and not evidence.source_id
                        for evidence in run.evidence
                    ))
                    self.assertTrue(all(
                        link.stance == EvidenceStance.CONTEXTUAL and link.strength == 0.0
                        for link in run.evidence_claim_links
                    ))
                    self.assertTrue(any("no external sources" in finding for finding in run.findings))
                    persisted = store.load_run(run.run_id)
                    self.assertEqual(persisted.status, RunStatus.COMPLETED)
                    self.assertEqual(persisted.run_id, run.run_id)


if __name__ == "__main__":
    unittest.main()
