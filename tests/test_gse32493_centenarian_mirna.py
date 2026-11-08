import csv
import gzip
import tempfile
import unittest
from pathlib import Path

from scripts.analyze_gse32493_centenarian_mirna import analyze


class GSE32493CentenarianMiRNATests(unittest.TestCase):
    def _write(self, path, header, rows):
        with gzip.open(path, "wt", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle, delimiter="\t")
            writer.writerow(header)
            writer.writerows(rows)

    def test_replicate_level_exact_permutation_and_fdr(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cent = root / "cent.txt.gz"
            control = root / "control.txt.gz"
            features = [f"hsa-miR-{i}" for i in range(12)]
            self._write(cent, ["miRNA", "cent1", "cent2", "cent3"],
                        [[name, 30+i, 31+i, 32+i] for i, name in enumerate(features)])
            self._write(control, ["miRNA", "ctrl1", "ctrl2", "ctrl3"],
                        [[name, 5+i, 6+i, 7+i] for i, name in enumerate(features)])
            report = analyze(cent, control)
            self.assertEqual(report["status"], "EXPLORATORY_REPLICATE_LEVEL_COMPARISON")
            self.assertTrue(report["per_sample_values_retained"])
            self.assertEqual(report["features_shared"], 12)
            self.assertIn("exact_permutation_p", report["top_effects"][0])
            self.assertIn("fdr_bh", report["top_effects"][0])
            self.assertEqual(len(report["source_files"]["centenarian"]["sha256"]), 64)

    def test_group_means_are_never_treated_as_replicates(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cent = root / "cent.txt.gz"
            control = root / "control.txt.gz"
            features = [f"hsa-miR-{i}" for i in range(12)]
            self._write(cent, ["miRNA", "mean_count"],
                        [[name, 30+i] for i, name in enumerate(features)])
            self._write(control, ["miRNA", "mean_count"],
                        [[name, 5+i] for i, name in enumerate(features)])
            report = analyze(cent, control)
            self.assertEqual(report["status"], "EXPLORATORY_GROUP_LEVEL_COMPARISON")
            self.assertFalse(report["per_sample_values_retained"])
            self.assertNotIn("exact_permutation_p", report["top_effects"][0])
            self.assertIn("Not computed", report["inferential_statistics"])


if __name__ == "__main__":
    unittest.main()
