"""Tests for conservative cross-dataset DE consistency screening."""
import unittest

from oracle.models import DifferentialExpressionAnalysisRecord
from oracle.replication import screen_independent_datasets


def analysis(accession, checksum, feature_rows, analysis_id):
    return DifferentialExpressionAnalysisRecord(
        dataset_accession=accession,
        source_file=f"{accession}.tsv",
        matrix_sha256=checksum,
        method="DESeq2",
        contrast={"group_a": "control", "group_b": "treated"},
        sample_groups={"control": ["C1", "C2"], "treated": ["T1", "T2"]},
        sample_count=4,
        features_input=len(feature_rows),
        software={"r": "4.4", "deseq2": "1.42"},
        results=feature_rows,
        limitations="Simple two-group design",
        analysis_id=analysis_id,
    )


class ReplicationScreenTests(unittest.TestCase):
    def setUp(self):
        self.source = analysis("GSE100", "a" * 64, [
            {"feature": "GENE1", "log2_fold_change": 1.2,
             "p_value": 0.001, "p_value_adjusted_bh": 0.01},
        ], "dea_source")

    def test_independent_dataset_same_direction_is_only_potential_consistency(self):
        other = analysis("GSE200", "b" * 64, [
            {"feature": "GENE1", "log2_fold_change": 0.8,
             "p_value": 0.002, "p_value_adjusted_bh": 0.02},
        ], "dea_other")
        report = screen_independent_datasets([self.source, other], "dea_source", "GENE1")
        self.assertEqual(report["summary"], "potential_directional_consistency")
        self.assertEqual(
            report["independent_dataset_comparisons"][0]["classification"],
            "same_direction_significant",
        )
        self.assertIn("not a meta-analysis", report["interpretation"])

    def test_opposite_direction_significant_is_reported_as_conflict(self):
        other = analysis("GSE200", "b" * 64, [
            {"feature": "GENE1", "log2_fold_change": -0.8,
             "p_value": 0.002, "p_value_adjusted_bh": 0.02},
        ], "dea_other")
        report = screen_independent_datasets([self.source, other], "dea_source", "GENE1")
        self.assertEqual(report["summary"], "potential_directional_conflict")
        self.assertEqual(
            report["independent_dataset_comparisons"][0]["classification"],
            "opposite_direction_significant",
        )

    def test_same_accession_or_same_matrix_is_not_counted_as_independent(self):
        same_accession = analysis("GSE100", "c" * 64, [], "dea_same_accession")
        same_matrix = analysis("GSE300", "a" * 64, [], "dea_same_matrix")
        report = screen_independent_datasets(
            [self.source, same_accession, same_matrix], "dea_source", "GENE1"
        )
        self.assertEqual(report["summary"], "no_eligible_independent_dataset")
        self.assertEqual(report["independent_dataset_comparisons"], [])

    def test_missing_feature_is_visible_not_silently_ignored(self):
        other = analysis("GSE200", "b" * 64, [], "dea_other")
        report = screen_independent_datasets([self.source, other], "dea_source", "GENE1")
        self.assertEqual(
            report["independent_dataset_comparisons"][0]["classification"],
            "feature_not_tested",
        )

    def test_invalid_fdr_and_unknown_feature_are_rejected(self):
        with self.assertRaises(ValueError):
            screen_independent_datasets([self.source], "dea_source", "GENE1", 1.0)
        with self.assertRaisesRegex(ValueError, "not found"):
            screen_independent_datasets([self.source], "dea_source", "UNKNOWN")


if __name__ == "__main__":
    unittest.main()
