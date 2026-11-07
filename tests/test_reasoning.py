"""Tests for API-free scientific reasoning primitives."""
import unittest

from oracle.models import Evidence, EvidenceKind, Hypothesis
from oracle.reasoning import (
    analyze_evidence_gaps,
    generate_competing_hypotheses,
    skeptic_checks,
)


class ReasoningEngineTests(unittest.TestCase):
    def test_gap_analysis_marks_uncovered_terms_and_provenance(self):
        evidence = [
            Evidence(
                claim="Cellular senescence is associated with aging",
                source="Paper A",
                source_id="src-a",
            )
        ]
        report = analyze_evidence_gaps(
            "How do cellular senescence and mitochondrial dynamics affect longevity?",
            evidence,
        )
        self.assertIn("senescence", report.covered_terms)
        self.assertTrue(any(gap.term == "mitochondrial" for gap in report.gaps))
        self.assertEqual(report.source_backed_evidence_count, 1)

    def test_inference_only_evidence_does_not_generate_hypotheses(self):
        evidence = [
            Evidence(
                claim="A planning idea mentions aging and longevity",
                source="ORACLE inference",
                kind=EvidenceKind.INFERENCE,
            ),
            Evidence(
                claim="Another planning idea mentions aging and longevity",
                source="ORACLE inference",
                kind=EvidenceKind.INFERENCE,
            ),
        ]
        self.assertEqual(generate_competing_hypotheses("longevity", evidence), [])

    def test_cross_source_co_mentions_generate_provisional_candidate(self):
        evidence = [
            Evidence(
                claim="Cellular senescence is associated with aging",
                source="Paper A",
                source_id="src-a",
            ),
            Evidence(
                claim="Cellular senescence contributes to tissue dysfunction",
                source="Paper B",
                source_id="src-b",
            ),
        ]
        candidates = generate_competing_hypotheses("human longevity", evidence)
        self.assertTrue(candidates)
        self.assertEqual(candidates[0].confidence, "very low")
        self.assertIn("not by causal inference", candidates[0].rationale)

    def test_skeptic_flags_missing_independent_evidence(self):
        hypothesis = Hypothesis(
            statement="Provisional candidate",
            rationale="Test only",
            predictions=["A testable prediction"],
        )
        warnings = skeptic_checks([hypothesis], [])
        self.assertTrue(any("fewer than two independent" in item for item in warnings))
        self.assertTrue(any("do not demonstrate causality" in item for item in warnings))


if __name__ == "__main__":
    unittest.main()
