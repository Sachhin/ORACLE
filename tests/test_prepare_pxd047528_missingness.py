import csv
import json
import tempfile
import unittest
from pathlib import Path

from scripts.prepare_pxd047528_missingness import prepare_pxd047528


class PXD047528PreparationTests(unittest.TestCase):
    def _write(self, path, rows):
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
            writer.writerows(rows)

    def test_prepares_paired_matrices_and_never_invents_clinical_labels(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dda, dia, out = root / "dda.tsv", root / "dia.tsv", root / "prepared"
            samples = ["S1", "S2", "S3"]
            self._write(dda, [
                ["Sequence", *samples],
                ["PEPTIDE_A", "10", "0", "30"],
                ["PEPTIDE_A", "10", "20", ""],
                ["PEPTIDE_B", "0", "40", "60"],
                ["PEPTIDE_C", "0", "0", "0"],
            ])
            self._write(dia, [
                ["Sequence", *samples],
                ["PEPTIDE_A", "20", "40", "60"],
                ["PEPTIDE_B", "20", "80", "120"],
                ["PEPTIDE_C", "10", "10", "10"],
            ])
            report = prepare_pxd047528(dda, dia, out, sample_ids=samples)
            self.assertEqual(report["sample_count"], 3)
            self.assertEqual(report["shared_peptides_with_at_least_one_dda_measurement"], 2)
            self.assertEqual(report["genuine_dda_missing_cells"], 1)
            self.assertEqual(report["genuine_dda_missing_cells_with_dia_measurement"], 1)
            self.assertEqual(report["preparation_status"], "MATRICES_PREPARED_CLINICAL_SAMPLE_MAPPING_REQUIRED")

            with (out / "observed_dda_log.tsv").open(encoding="utf-8") as handle:
                observed = list(csv.DictReader(handle, delimiter="\t"))
            with (out / "orthogonal_dia_log.tsv").open(encoding="utf-8") as handle:
                orthogonal = list(csv.DictReader(handle, delimiter="\t"))
            with (out / "row_median_imputed_dda_log.tsv").open(encoding="utf-8") as handle:
                imputed = list(csv.DictReader(handle, delimiter="\t"))
            by_feature = {row["Sequence"]: row for row in observed}
            imp_by_feature = {row["Sequence"]: row for row in imputed}
            dia_by_feature = {row["Sequence"]: row for row in orthogonal}
            self.assertEqual(by_feature["PEPTIDE_B"]["S1"], "")
            self.assertEqual(dia_by_feature["PEPTIDE_B"]["S1"] != "", True)
            self.assertAlmostEqual(float(imp_by_feature["PEPTIDE_B"]["S1"]),
                                   (float(by_feature["PEPTIDE_B"]["S2"]) +
                                    float(by_feature["PEPTIDE_B"]["S3"])) / 2)
            self.assertEqual(imp_by_feature["PEPTIDE_A"]["S1"], by_feature["PEPTIDE_A"]["S1"])

            with (out / "sample_map_template.tsv").open(encoding="utf-8") as handle:
                labels = list(csv.DictReader(handle, delimiter="\t"))
            self.assertEqual([row["sample_id"] for row in labels], samples)
            self.assertTrue(all(row["phenotype"] == "" for row in labels))
            manifest = json.loads((out / "preparation_manifest.json").read_text())
            self.assertIn("15-to-13 sample discrepancy", manifest["clinical_mapping_warning"])

    def test_rejects_sample_column_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dda, dia = root / "dda.tsv", root / "dia.tsv"
            self._write(dda, [["Sequence", "S1", "S2"], ["PEPTIDE", "1", "2"]])
            self._write(dia, [["Sequence", "S1", "OTHER"], ["PEPTIDE", "1", "2"]])
            with self.assertRaisesRegex(ValueError, "missing expected sample columns"):
                prepare_pxd047528(dda, dia, root / "out", sample_ids=["S1", "S2"])


if __name__ == "__main__":
    unittest.main()
