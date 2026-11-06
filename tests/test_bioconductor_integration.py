"""Live Bioconductor checks; skipped in Python-only environments."""
import shutil
import tempfile
import unittest
from pathlib import Path

from oracle.geo_reference import compare_tmm_to_edger, compare_voom_to_limma_reference
from oracle.geo_voom import GEOVoomAnalyzer

R_AVAILABLE = shutil.which("Rscript") is not None

@unittest.skipUnless(R_AVAILABLE, "Rscript is not installed")
class BioconductorIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.matrix = self.root / "counts.tsv"
        rows = ["gene\tC1\tC2\tC3\tT1\tT2\tT3"]
        for i in range(1, 301):
            base = 20 + (i * 17) % 180
            rows.append(f"gene{i}\t{base}\t{base+2}\t{base+1}\t{base*2}\t{base*2+3}\t{base*2+1}")
        self.matrix.write_text("\n".join(rows) + "\n", encoding="utf-8")
    def tearDown(self):
        self.tmp.cleanup()
    def test_live_edger_reference_comparison_emits_numeric_discrepancy(self):
        try:
            report = compare_tmm_to_edger(self.matrix, tolerance=1e-5)
        except RuntimeError as exc:
            if "not installed" in str(exc) or "there is no package called" in str(exc):
                self.skipTest(str(exc))
            raise
        self.assertEqual(report["comparison"], "ORACLE TMM vs edgeR::calcNormFactors(method='TMM')")
        self.assertGreaterEqual(report["max_absolute_difference"], 0)
        self.assertTrue(report["within_tolerance"], report)
        self.assertEqual(len(report["edgeR_factors"]), 6)
    def test_live_limma_voom_execution(self):
        groups = {"C1":"control","C2":"control","C3":"control",
                  "T1":"treated","T2":"treated","T3":"treated"}
        try:
            result = GEOVoomAnalyzer().analyze(
                self.matrix, groups, "control", "treated", timeout_seconds=300
            )
        except RuntimeError as exc:
            if "not installed" in str(exc) or "there is no package called" in str(exc):
                self.skipTest(str(exc))
            raise
        self.assertEqual(result["sample_count"], 6)
        self.assertEqual(result["features_returned"], 300)
        self.assertTrue(result["software"]["limma"])
        self.assertTrue(result["matrix_sha256"])


    def test_live_limma_voom_reference_output_parity(self):
        groups = {"C1":"control","C2":"control","C3":"control",
                  "T1":"treated","T2":"treated","T3":"treated"}
        try:
            report = compare_voom_to_limma_reference(
                self.matrix, groups, group_a="control", group_b="treated",
                timeout_seconds=300, tolerance=1e-10,
            )
        except RuntimeError as exc:
            if "not installed" in str(exc) or "there is no package called" in str(exc):
                self.skipTest(str(exc))
            raise
        self.assertEqual(report["features_compared"], 300)
        self.assertTrue(report["within_tolerance"], report)
        self.assertEqual(report["overall_maximum_absolute_difference"], 0.0)
        self.assertIn("not an independent algorithm", report["interpretation"])

if __name__ == "__main__":
    unittest.main()
