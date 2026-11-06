import csv
import json
import tempfile
import unittest
from pathlib import Path

from scripts.benchmark_pxd000279_mixture import benchmark_pxd000279


class PXD000279MixtureBenchmarkTests(unittest.TestCase):
    def test_scores_known_species_ratios_and_real_missingness(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "proteinGroups.txt"
            columns = [
                "LFQ intensity run_Hela60_Ecoli10_rep1",
                "LFQ intensity run_Hela60_Ecoli10_rep2",
                "LFQ intensity run_Hela60_Ecoli10_rep3",
                "LFQ intensity run_Hela60_Ecoli30_rep1",
                "LFQ intensity run_Hela60_Ecoli30_rep2",
                "LFQ intensity run_Hela60_Ecoli30_rep3",
            ]
            with path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle, delimiter="\t")
                writer.writerow(["Fasta headers", "Reverse", "Potential contaminant",
                                 "Only identified by site", *columns])
                writer.writerow(["sp|P1|HUMAN OS=Homo sapiens", "", "", "",
                                 100, 100, 100, 100, 100, 100])
                writer.writerow(["sp|P2|ECOLI OS=Escherichia coli", "", "", "",
                                 100, 100, 100, 300, 300, 300])
                writer.writerow(["sp|P3|HUMAN OS=Homo sapiens", "", "", "",
                                 100, 100, 0, 100, 100, 100])
                writer.writerow(["sp|P4|ECOLI OS=Escherichia coli", "", "", "",
                                 100, 100, 100, 300, 0, 300])
                writer.writerow(["REV__DECOY OS=Homo sapiens", "+", "", "",
                                 100, 100, 100, 100, 100, 100])
                writer.writerow(["sp|P5|MIXED OS=Homo sapiens OS=Escherichia coli", "", "", "",
                                 100, 100, 100, 300, 300, 300])
            report = benchmark_pxd000279(path)
            self.assertEqual(report["status"], "SCORED_KNOWN_MIXTURE_RATIO")
            self.assertEqual(report["protein_universe"], 4)
            self.assertGreater(report["missing_fraction"], 0)
            self.assertEqual(report["species_results"]["human"]["observed_only"]["median_log2_fold_change"], 0)
            self.assertAlmostEqual(
                report["species_results"]["ecoli"]["observed_only"]["median_log2_fold_change"],
                1.5849625007, places=6)
            self.assertEqual(report["skipped_rows"]["decoy_or_contaminant_or_site_only"], 1)
            self.assertEqual(report["skipped_rows"]["ambiguous_species"], 1)
            self.assertEqual(len(report["input_sha256"]), 64)

    def test_rejects_unrecognized_sample_design(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "proteinGroups.txt"
            with path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle, delimiter="\t")
                writer.writerow(["Fasta headers", *[f"LFQ intensity sample{i}" for i in range(6)]])
            with self.assertRaisesRegex(ValueError, "Could not identify three Ecoli10 and three Ecoli30"):
                benchmark_pxd000279(path)


if __name__ == "__main__":
    unittest.main()
