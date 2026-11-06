"""Tests for known-positive recovery benchmark semantics."""
import json
import tempfile
import unittest
from pathlib import Path

from oracle.benchmark import evaluate_known_positive_recovery, run_benchmark


class KnownPositiveBenchmarkTests(unittest.TestCase):
    def setUp(self):
        self.manifest = {
            "dataset_accession": "GSE12345",
            "reference": "https://example.org/curated-study",
            "truth_set_version": "v1",
            "contrast": {"group_a": "control", "group_b": "treated"},
            "known_positive_features": ["GENE_A", "GENE_B", "GENE_NOT_TESTED"],
        }
        self.results = [
            {"feature": "GENE_A", "log2_fold_change": 1.1, "p_value_adjusted_bh": 0.01},
            {"feature": "GENE_B", "log2_fold_change": -0.7, "p_value_adjusted_bh": 0.2},
            {"feature": "GENE_C", "log2_fold_change": 2.0, "p_value_adjusted_bh": 0.001},
        ]

    def test_recovery_separates_missed_untested_and_unmatched_hits(self):
        report = evaluate_known_positive_recovery(self.results, self.manifest)
        self.assertEqual(report["recovered_known_positives"], ["GENE_A"])
        self.assertEqual(report["missed_tested_known_positives"], ["GENE_B"])
        self.assertEqual(report["known_positives_not_tested"], ["GENE_NOT_TESTED"])
        self.assertEqual(report["significant_hits_not_in_reference_set"], ["GENE_C"])
        self.assertAlmostEqual(report["known_positive_recall"], 1 / 3)
        self.assertAlmostEqual(report["curated_set_overlap_precision"], 1 / 2)
        self.assertIn("not proven biological false positives", report["interpretation"])

    def test_log2fc_threshold_is_applied_and_thresholds_are_recorded(self):
        report = evaluate_known_positive_recovery(
            self.results, self.manifest, absolute_log2fc_threshold=1.0
        )
        self.assertEqual(report["significant_hits"], ["GENE_A", "GENE_C"])
        self.assertEqual(report["thresholds"]["absolute_log2_fold_change_min"], 1.0)

    def test_invalid_or_duplicate_truth_set_is_rejected(self):
        bad = {**self.manifest, "known_positive_features": ["GENE_A", "GENE_A"]}
        with self.assertRaisesRegex(ValueError, "unique"):
            evaluate_known_positive_recovery(self.results, bad)
        bad = {**self.manifest, "reference": "http://example.org"}
        with self.assertRaisesRegex(ValueError, "HTTPS"):
            evaluate_known_positive_recovery(self.results, bad)

    def test_duplicate_result_features_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "unique"):
            evaluate_known_positive_recovery(
                self.results + [self.results[0]], self.manifest
            )

    def test_file_runner_records_input_checksums(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            results_path = root / "results.json"
            manifest_path = root / "truth.json"
            results_path.write_text(json.dumps({"results": self.results}), encoding="utf-8")
            manifest_path.write_text(json.dumps(self.manifest), encoding="utf-8")
            report = run_benchmark(results_path, manifest_path)
            self.assertEqual(len(report["provenance"]["results_sha256"]), 64)
            self.assertEqual(len(report["provenance"]["manifest_sha256"]), 64)


if __name__ == "__main__":
    unittest.main()
