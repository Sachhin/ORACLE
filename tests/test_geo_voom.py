"""Tests for the optional limma-voom adapter without requiring an R installation."""
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from oracle.geo_voom import GEOVoomAnalyzer, VoomUnavailableError


class GEOVoomTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.matrix = self.root / "counts.tsv"
        self.matrix.write_text(
            "gene\tA1\tA2\tB1\tB2\n"
            "g1\t10\t12\t30\t32\n"
            "g2\t20\t22\t40\t42\n",
            encoding="utf-8",
        )
        self.groups = {"A1": "control", "A2": "control",
                       "B1": "treated", "B2": "treated"}

    def tearDown(self):
        self.temp.cleanup()

    def test_validates_explicit_groups_before_running_r(self):
        with patch("oracle.geo_voom.shutil.which", return_value="/usr/bin/Rscript"):
            with self.assertRaisesRegex(ValueError, "cover all samples"):
                GEOVoomAnalyzer().analyze(
                    self.matrix, {"A1": "control"}, "control", "treated"
                )

    def test_missing_rscript_is_reported(self):
        with patch("oracle.geo_voom.shutil.which", return_value=None):
            with self.assertRaises(VoomUnavailableError):
                GEOVoomAnalyzer().analyze(
                    self.matrix, self.groups, "control", "treated"
                )

    def test_mocked_r_execution_returns_versioned_results_and_hash(self):
        def fake_run(command, **kwargs):
            output = Path(command[5])
            output.write_text(
                "feature\tlogFC\tAveExpr\tt\tP.Value\tadj.P.Val\tB\n"
                "g1\t1.5\t4.2\t3.1\t0.01\t0.02\t-1.0\n"
                "g2\t-0.5\t3.1\t-1.2\t0.3\t0.4\t-2.0\n",
                encoding="utf-8",
            )
            return SimpleNamespace(returncode=0, stdout="4.4.0\t4.0.0\t3.60.0", stderr="")

        with patch("oracle.geo_voom.shutil.which", return_value="/usr/bin/Rscript"), \
             patch("oracle.geo_voom.subprocess.run", side_effect=fake_run):
            result = GEOVoomAnalyzer().analyze(
                self.matrix, self.groups, "control", "treated"
            )
        self.assertEqual(result["contrast"]["direction"], "treated vs control")
        self.assertEqual(result["features_returned"], 2)
        self.assertEqual(result["features_with_adjusted_p_value"], 2)
        self.assertEqual(result["results"][0]["feature"], "g1")
        self.assertEqual(result["software"]["limma"], "3.60.0")
        self.assertEqual(len(result["matrix_sha256"]), 64)

    def test_rejects_fractional_raw_counts(self):
        self.matrix.write_text("gene\tA1\tA2\tB1\tB2\ng1\t1.5\t2\t3\t4\n", encoding="utf-8")
        with patch("oracle.geo_voom.shutil.which", return_value="/usr/bin/Rscript"):
            with self.assertRaisesRegex(ValueError, "integer raw counts"):
                GEOVoomAnalyzer().analyze(
                    self.matrix, self.groups, "control", "treated"
                )


if __name__ == "__main__":
    unittest.main()
