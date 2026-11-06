"""Tests for explicit GEO matrix normalization methods."""
import csv
import tempfile
import unittest
from pathlib import Path

from oracle.geo_normalization import normalize_geo_matrix


class GEONormalizationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, name, body):
        path = self.root / name
        path.write_text(body, encoding="utf-8")
        return path

    def test_quantile_normalization_equalizes_sample_distributions_and_preserves_raw(self):
        source = self.write(
            "matrix.tsv",
            "ID_REF\tS1\tS2\ng1\t5\t4\ng2\t2\t1\ng3\t3\t6\n",
        )
        output = self.root / "normalized.tsv"
        report = normalize_geo_matrix(source, output, "quantile")
        self.assertEqual(report["features"], 3)
        self.assertEqual(report["samples"], 2)
        self.assertNotEqual(report["input_sha256"], report["output_sha256"])
        self.assertIn("g1", source.read_text(encoding="utf-8"))
        with output.open(encoding="utf-8") as handle:
            rows = list(csv.reader(handle, delimiter="\t"))
        self.assertEqual(rows[0], ["feature", "S1", "S2"])
        col1 = sorted(float(row[1]) for row in rows[1:])
        col2 = sorted(float(row[2]) for row in rows[1:])
        self.assertEqual(col1, col2)
        values = {row[0]: (float(row[1]), float(row[2])) for row in rows[1:]}
        self.assertEqual(values["g1"], (5.5, 3.5))
        self.assertEqual(values["g2"], (1.5, 1.5))

    def test_cpm_and_log2_cpm_require_raw_integer_counts(self):
        source = self.write(
            "counts.tsv",
            "gene\tA\tB\ng1\t10\t20\ng2\t30\t20\n",
        )
        cpm_path = self.root / "cpm.tsv"
        report = normalize_geo_matrix(source, cpm_path, "cpm")
        with cpm_path.open(encoding="utf-8") as handle:
            rows = list(csv.reader(handle, delimiter="\t"))
        self.assertAlmostEqual(float(rows[1][1]), 250000.0)
        self.assertAlmostEqual(float(rows[1][2]), 500000.0)
        self.assertEqual(report["sample_library_sizes"], {"A": 40.0, "B": 40.0})
        log_path = self.root / "log.tsv"
        normalize_geo_matrix(source, log_path, "log2-cpm", prior_count=1.0)
        with log_path.open(encoding="utf-8") as handle:
            log_rows = list(csv.reader(handle, delimiter="\t"))
        self.assertAlmostEqual(float(log_rows[1][1]), 18.0, places=5)

        continuous = self.write("continuous.tsv", "gene\tA\tB\ng1\t1.5\t2\n")
        with self.assertRaisesRegex(ValueError, "non-negative integer raw counts"):
            normalize_geo_matrix(continuous, self.root / "bad.tsv", "cpm")

    def test_rejects_invalid_inputs_and_never_overwrites_raw_file(self):
        source = self.write("raw.tsv", "gene\tA\tB\ng1\t1\t2\n")
        with self.assertRaisesRegex(ValueError, "differ from input"):
            normalize_geo_matrix(source, source, "quantile")
        with self.assertRaisesRegex(ValueError, "positive library size"):
            empty = self.write("empty.tsv", "gene\tA\tB\ng1\t0\t2\n")
            normalize_geo_matrix(empty, self.root / "empty_out.tsv", "cpm")
        with self.assertRaisesRegex(ValueError, "Missing/non-numeric"):
            bad = self.write("missing.tsv", "gene\tA\tB\ng1\tNA\t2\n")
            normalize_geo_matrix(bad, self.root / "missing_out.tsv", "quantile")
        with self.assertRaises(ValueError):
            normalize_geo_matrix(source, self.root / "bad_method.tsv", "auto")


if __name__ == "__main__":
    unittest.main()
