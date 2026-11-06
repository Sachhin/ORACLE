"""Tests for explicit GEO per-sample count matrix construction."""
import gzip
import tempfile
import unittest
from pathlib import Path

from oracle.geo_matrix import merge_sample_count_files


class GEOSampleMatrixTests(unittest.TestCase):
    def test_merges_explicit_samples_and_records_hashes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            a = root / "GSM_A.txt"
            b = root / "GSM_B.txt.gz"
            a.write_text("gene_id\tcount\nAT1G1\t12\nAT1G2\t0\n", encoding="utf-8")
            with gzip.open(b, "wt", encoding="utf-8") as handle:
                handle.write("gene_id\tcount\nAT1G1\t19\nAT1G2\t3\n")
            output = root / "matrix.tsv"
            report = merge_sample_count_files(
                {"GSM_A": a, "GSM_B": b}, output
            )
            self.assertEqual(report["sample_names"], ["GSM_A", "GSM_B"])
            self.assertEqual(report["feature_count"], 2)
            self.assertEqual(len(report["matrix_sha256"]), 64)
            self.assertEqual(len(report["source_sha256"]["GSM_A"]), 64)
            self.assertEqual(
                output.read_text(encoding="utf-8"),
                "feature\tGSM_A\tGSM_B\nAT1G1\t12\t19\nAT1G2\t0\t3\n",
            )

    def test_custom_columns_and_no_header(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            a, b = root / "a.csv", root / "b.csv"
            a.write_text("AT1G1,x,8\nAT1G2,y,4\n", encoding="utf-8")
            b.write_text("AT1G1,x,9\nAT1G2,y,5\n", encoding="utf-8")
            report = merge_sample_count_files(
                {"a": a, "b": b}, root / "matrix.tsv",
                feature_column=0, count_column=2, has_header=False,
                delimiter="comma",
            )
            self.assertEqual(report["feature_count"], 2)

    def test_rejects_mismatched_features_and_duplicates(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            a, b = root / "a.tsv", root / "b.tsv"
            a.write_text("gene\tcount\nA\t1\nB\t2\n", encoding="utf-8")
            b.write_text("gene\tcount\nA\t3\nC\t4\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "feature set differs"):
                merge_sample_count_files({"a": a, "b": b}, root / "out.tsv")
            b.write_text("gene\tcount\nA\t3\nA\t4\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "duplicate"):
                merge_sample_count_files({"a": a, "b": b}, root / "out.tsv")

    def test_rejects_fractional_negative_and_invalid_counts(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            a, b = root / "a.tsv", root / "b.tsv"
            a.write_text("gene\tcount\nA\t1\n", encoding="utf-8")
            for bad in ("1.5", "-1", "NaN", ""):
                b.write_text(f"gene\tcount\nA\t{bad}\n", encoding="utf-8")
                with self.subTest(value=bad):
                    with self.assertRaisesRegex(ValueError, "non-negative integer"):
                        merge_sample_count_files({"a": a, "b": b}, root / "out.tsv")

    def test_requires_two_samples_and_unique_nonempty_names(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "one.tsv"
            path.write_text("gene\tcount\nA\t1\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "At least two"):
                merge_sample_count_files({"one": path}, Path(directory) / "out.tsv")
            with self.assertRaisesRegex(ValueError, "unique"):
                merge_sample_count_files({"same": path, " same ": path}, Path(directory) / "out.tsv")


if __name__ == "__main__":
    unittest.main()
