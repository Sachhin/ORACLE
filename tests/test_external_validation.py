import json
import tempfile
import unittest
from pathlib import Path

from oracle.external_validation import compare_de_tables, compare_expression_matrices


class ExternalValidationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.provenance = {
            "dataset_accession": "GSE_TEST",
            "reference_method": "platform-matched trusted reference",
            "software": "R/Bioconductor pinned versions",
            "source_url": "https://example.org/reference",
        }

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, name, value):
        path = self.root / name
        path.write_text(value, encoding="utf-8")
        return path

    def test_expression_reference_metrics_and_provenance(self):
        oracle = self.write("oracle.tsv", "probe\tS1\tS2\np1\t1\t3\np2\t2\t6\np3\t3\t9\n")
        reference = self.write("reference.tsv", "probe\tS1\tS2\np1\t2\t6\np2\t4\t12\np3\t6\t18\n")
        report = compare_expression_matrices(oracle, reference, provenance=self.provenance)
        self.assertEqual(report["matched_features"], 3)
        self.assertEqual(report["samples"], ["S1", "S2"])
        self.assertAlmostEqual(report["per_sample"]["S1"]["pearson_r"], 1.0)
        self.assertAlmostEqual(report["per_sample"]["S1"]["mae"], 2.0)
        self.assertEqual(len(report["oracle_sha256"]), 64)

    def test_expression_rejects_sample_mismatch_and_low_overlap(self):
        oracle = self.write("o.tsv", "probe\tS1\tS2\np1\t1\t3\np2\t2\t6\n")
        wrong_samples = self.write("s.tsv", "probe\tS1\tS3\np1\t1\t3\np2\t2\t6\n")
        with self.assertRaisesRegex(ValueError, "sample identifiers"):
            compare_expression_matrices(oracle, wrong_samples, provenance=self.provenance)
        low_overlap = self.write("low.tsv", "probe\tS1\tS2\nx1\t1\t3\nx2\t2\t6\n")
        with self.assertRaisesRegex(ValueError, "overlap"):
            compare_expression_matrices(oracle, low_overlap, provenance=self.provenance)

    def test_de_concordance(self):
        oracle = self.write("oracle_de.tsv",
            "feature\tlog2fc\tpadj\na\t2\t0.001\nb\t1\t0.2\nc\t-1\t0.01\n")
        reference = self.write("reference_de.tsv",
            "feature\tlogFC\tadj.P.Val\na\t1.8\t0.002\nb\t0.8\t0.3\nc\t-1.2\t0.02\n")
        report = compare_de_tables(oracle, reference, provenance=self.provenance)
        concordance = report["significance_concordance"]
        self.assertEqual(concordance["true_positive"], 2)
        self.assertEqual(concordance["false_positive"], 0)
        self.assertEqual(concordance["false_negative"], 0)
        self.assertAlmostEqual(concordance["f1"], 1.0)
        self.assertAlmostEqual(report["log2fc_metrics"]["spearman_r"], 1.0)

    def test_provenance_is_mandatory_and_reference_p_values_bounded(self):
        oracle = self.write("o.tsv", "feature\tlog2fc\tpadj\na\t1\t0.01\n")
        reference = self.write("r.tsv", "feature\tlogFC\tadj.P.Val\na\t1\t1.2\n")
        with self.assertRaisesRegex(ValueError, "reference_provenance"):
            compare_de_tables(oracle, reference, provenance={})
        with self.assertRaisesRegex(ValueError, "adjusted p-values"):
            compare_de_tables(oracle, reference, provenance=self.provenance)


if __name__ == "__main__":
    unittest.main()
