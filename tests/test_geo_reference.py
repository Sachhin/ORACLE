import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from oracle.geo_reference import compare_tmm_to_edger, evaluate_row_median_imputation

class GEOReferenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "counts.tsv"
        self.path.write_text("gene\tA\tB\tC\n" + "".join(
            f"g{i}\t{i*10+2}\t{i*8+3}\t{i*12+1}\n" for i in range(1, 61)
        ), encoding="utf-8")
    def tearDown(self):
        self.tmp.cleanup()
    def test_mcar_imputation_diagnostic_is_reproducible(self):
        a = evaluate_row_median_imputation(self.path, missing_fraction=.2, replicates=5, seed=7)
        b = evaluate_row_median_imputation(self.path, missing_fraction=.2, replicates=5, seed=7)
        self.assertEqual(a, b)
        self.assertGreater(a["masked_values"], 0)
        self.assertIn("MCAR", a["limitations"])
    def test_mar_and_mnar_diagnostics_are_reproducible_and_distinct(self):
        mar = evaluate_row_median_imputation(self.path, missing_fraction=.2, replicates=5, seed=7, mechanism="MAR")
        mnar = evaluate_row_median_imputation(self.path, missing_fraction=.2, replicates=5, seed=7, mechanism="MNAR")
        self.assertEqual(mar["missingness_mechanism"], "MAR")
        self.assertEqual(mnar["missingness_mechanism"], "MNAR")
        self.assertNotEqual(mar["benchmark_type"], mnar["benchmark_type"])
        self.assertGreater(mar["masked_values"], 0)
        self.assertGreater(mnar["masked_values"], 0)
    def test_invalid_mechanism_rejected(self):
        with self.assertRaisesRegex(ValueError, "mechanism"):
            evaluate_row_median_imputation(self.path, mechanism="UNKNOWN")
    def test_invalid_mcar_fraction_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_row_median_imputation(self.path, missing_fraction=1)
    def test_edgeR_missing_runtime_is_explicit(self):
        with patch("oracle.geo_reference.shutil.which", return_value=None):
            with self.assertRaisesRegex(RuntimeError, "Cannot find"):
                compare_tmm_to_edger(self.path)
    def test_edgeR_factor_comparison_mocked_contract(self):
        def fake_run(command, **kwargs):
            out = Path(command[4])
            out.write_text("sample\tfactor\nA\t1.0\nB\t1.0\nC\t1.0\n", encoding="utf-8")
            return SimpleNamespace(returncode=0, stdout="4.5.0", stderr="")
        with patch("oracle.geo_reference.shutil.which", return_value="/usr/bin/Rscript"), \
             patch("oracle.geo_reference.subprocess.run", side_effect=fake_run):
            result = compare_tmm_to_edger(self.path)
        self.assertEqual(result["edgeR_version"], "4.5.0")
        self.assertEqual(set(result["edgeR_factors"]), {"A", "B", "C"})
        self.assertEqual(result["input_sha256"].__len__(), 64)

if __name__ == "__main__":
    unittest.main()
