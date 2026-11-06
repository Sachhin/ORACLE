import csv
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from oracle.geo_affymetrix import AffymetrixRMAAnalyzer, AffymetrixUnavailableError

class AffymetrixRMATests(unittest.TestCase):
    def test_requires_explicit_backend_and_two_cel_files(self):
        with self.assertRaises(ValueError):
            AffymetrixRMAAnalyzer().analyze([], "out.tsv", backend="guess")
        with tempfile.TemporaryDirectory() as tmp:
            one = Path(tmp) / "one.CEL"
            one.write_bytes(b"cel")
            with self.assertRaisesRegex(ValueError, "at least two"):
                AffymetrixRMAAnalyzer().analyze([one], Path(tmp) / "out.tsv", backend="affy")

    def test_missing_rscript_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = []
            for name in ("a.CEL", "b.CEL"):
                path = Path(tmp) / name
                path.write_bytes(b"cel data")
                paths.append(path)
            with patch("oracle.geo_affymetrix.shutil.which", return_value=None):
                with self.assertRaises(AffymetrixUnavailableError):
                    AffymetrixRMAAnalyzer().analyze(paths, Path(tmp) / "out.tsv", backend="oligo")

    def test_mocked_rma_output_and_provenance(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = []
            for name in ("a.CEL", "b.CEL"):
                path = Path(tmp) / name
                path.write_bytes(name.encode())
                paths.append(path)
            def fake_run(command, **kwargs):
                manifest = Path(command[4])
                with manifest.open(encoding="utf-8") as handle:
                    cel_paths = [row[0] for row in list(csv.reader(handle, delimiter="\t"))[1:]]
                output = Path(command[5])
                with output.open("w", encoding="utf-8", newline="") as handle:
                    writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
                    writer.writerow(["feature", *[Path(p).stem for p in cel_paths]])
                    writer.writerow(["probe_set_1", "5.2", "5.8"])
                return SimpleNamespace(returncode=0, stdout="4.5.0\t1.70.0", stderr="")
            with patch("oracle.geo_affymetrix.shutil.which", return_value="/usr/bin/Rscript"), \
                 patch("oracle.geo_affymetrix.subprocess.run", side_effect=fake_run):
                report = AffymetrixRMAAnalyzer().analyze(
                    paths, Path(tmp) / "normalized.tsv", backend="affy")
            self.assertEqual(report["features"], 1)
            self.assertEqual(report["software"]["affy"], "1.70.0")
            self.assertEqual(len(report["input_files"]), 2)
            self.assertTrue((Path(tmp) / "normalized.tsv").is_file())
            self.assertIn("No platform detection", report["limitations"])

if __name__ == "__main__":
    unittest.main()
