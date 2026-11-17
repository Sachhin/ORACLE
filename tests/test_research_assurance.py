import unittest

from oracle.research_assurance import (
    cross_dataset_validation, discover_mechanism_candidates,
    evidence_integrity_audit, novelty_screen, prioritize_experiments,
    run_research_assurance, skeptic_review,
)


class ResearchAssuranceTests(unittest.TestCase):
    def test_integrity_detects_dangling_source_and_link(self):
        report = evidence_integrity_audit({
            "sources": [{"source_id": "s1", "title": "Paper"}],
            "evidence": [{"evidence_id": "e1", "source_id": "missing", "kind": "source", "claim": "x"}],
            "claims": [{"claim_id": "c1", "statement": "x"}],
            "evidence_claim_links": [{"claim_id": "c1", "evidence_id": "e404", "strength": 2}],
        })
        self.assertEqual(report["status"], "BLOCKED")
        codes = {item["code"] for item in report["issues"]}
        self.assertIn("EVIDENCE_SOURCE_UNRESOLVED", codes)
        self.assertIn("DANGLING_EVIDENCE_CLAIM_LINK", codes)
        self.assertIn("INVALID_LINK_STRENGTH", codes)

    def test_integrity_passes_source_backed_evidence(self):
        report = evidence_integrity_audit({
            "sources": [{"source_id": "s1", "doi": "10.1/example"}],
            "evidence": [{"evidence_id": "e1", "source_id": "s1", "kind": "source", "claim": "finding"}],
        })
        self.assertEqual(report["status"], "PASS")

    def test_cross_dataset_requires_distinct_accessions_and_flags_conflict(self):
        report = cross_dataset_validation([
            {"dataset_accession": "GSE1", "results": [{"feature": "GENE1", "log2_fold_change": 1.2, "p_value_adjusted_bh": .01}]},
            {"dataset_accession": "GSE1", "results": [{"feature": "GENE1", "log2_fold_change": 1.4, "p_value_adjusted_bh": .01}]},
            {"dataset_accession": "GSE2", "results": [{"feature": "GENE1", "log2_fold_change": -1.0, "p_value_adjusted_bh": .02}]},
        ])
        feature = report["features"][0]
        self.assertEqual(feature["dataset_count"], 2)
        self.assertEqual(feature["classification"], "replicated_directional_conflict")

    def test_cross_dataset_concordant_signal(self):
        report = cross_dataset_validation([
            {"dataset_accession": "GSE1", "results": [{"feature": "X", "log2_fold_change": 1, "p_value_adjusted_bh": .01}]},
            {"dataset_accession": "GSE2", "results": [{"feature": "X", "log2_fold_change": 2, "p_value_adjusted_bh": .02}]},
        ])
        self.assertEqual(report["features"][0]["classification"], "replicated_directionally_concordant_screen")

    def test_mechanism_candidates_never_claim_mechanism_or_novelty(self):
        cross = cross_dataset_validation([
            {"dataset_accession": "GSE1", "results": [{"feature": "GENE", "log2_fold_change": 1, "p_value_adjusted_bh": .01}]},
            {"dataset_accession": "GSE2", "results": [{"feature": "GENE", "log2_fold_change": 2, "p_value_adjusted_bh": .02}]},
        ])
        report = discover_mechanism_candidates(cross, [{"feature": "GENE", "pathway": "test", "source_url": "https://example.org"}])
        self.assertEqual(report["candidate_count"], 1)
        self.assertEqual(report["candidates"][0]["mechanism_status"], "NOT_ESTABLISHED")
        self.assertEqual(report["candidates"][0]["novelty_status"], "NOT_ESTABLISHED")

    def test_novelty_screen_marks_overlap_but_never_certifies_novelty(self):
        report = novelty_screen(
            [{"hypothesis_id": "h1", "statement": "mitochondrial protein expression supports human longevity"}],
            [{"title": "Mitochondrial protein expression and human longevity", "doi": "10.1/test"}],
            similarity_threshold=.2,
        )
        item = report["comparisons"][0]
        self.assertEqual(item["screen_status"], "possible_prior_art_overlap")
        self.assertEqual(item["novelty_conclusion"], "NOT_ESTABLISHED")

    def test_skeptic_flags_causal_language_and_missing_counterevidence(self):
        report = skeptic_review({"hypotheses": [{
            "hypothesis_id": "h1", "statement": "Gene A causes human longevity",
            "supporting_evidence_ids": [], "predictions": []
        }]})
        flags = report["reviews"][0]["flags"]
        self.assertTrue(any("Causal wording" in item for item in flags))
        self.assertTrue(any("No opposing evidence" in item for item in flags))

    def test_experiment_prioritization_is_deterministic_and_bounded(self):
        report = prioritize_experiments([
            {"name": "B", "feasibility": 5, "information_gain": 5, "falsifiability": 5, "data_readiness": 5},
            {"name": "A", "feasibility": 1, "information_gain": 1, "falsifiability": 1, "data_readiness": 1},
        ])
        self.assertEqual(report["experiments"][0]["name"], "B")
        self.assertEqual(report["experiments"][0]["priority_score"], 5.0)
        with self.assertRaises(ValueError):
            prioritize_experiments([{"name": "bad", "feasibility": 6}])

    def test_end_to_end_assurance_keeps_external_blockers_explicit(self):
        report = run_research_assurance({
            "run": {"hypotheses": [{"hypothesis_id": "h1", "statement": "testable longevity mechanism"}]},
            "prior_art": [], "experiment_candidates": [{"name": "replication"}]
        })
        self.assertEqual(report["status"], "SCREEN_COMPLETE")
        self.assertIn("source-authenticated CRA000515", report["release_caution"])
        self.assertEqual(report["modules"]["novelty_screen"]["status"], "PRIOR_ART_NOT_SUPPLIED")


if __name__ == "__main__":
    unittest.main()
