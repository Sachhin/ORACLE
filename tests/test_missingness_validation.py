import csv
import tempfile
import unittest
from pathlib import Path

from oracle.missingness_validation import evaluate_orthogonal_missingness


class OrthogonalMissingnessTests(unittest.TestCase):
    def write_tsv(self, path, header, rows):
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle, delimiter="\\t")
            writer.writerow(header)
            writer.writerows(rows)

    def test_scores_real_missing_cells_and_biological_outcome_concordance(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            observed = root / "observed.tsv"
            dia = root / "dia.tsv"
            imputed = root / "imputed.tsv"
            labels = root / "labels.tsv"
            header = ["feature", "S1", "S2", "S3", "S4"]
            self.write_tsv(observed, header, [
                ["P1", 1, "", 3, 4],
                ["P2", 4, 5, "", 7],
                ["P3", 2, 3, 5, 6],
            ])
            self.write_tsv(dia, header, [
                ["P1", 1.1, 2.1, 3.1, 4.1],
                ["P2", 4.1, 5.1, 6.1, 7.1],
                ["P3", 2.1, 3.1, 5.1, 6.1],
            ])
            self.write_tsv(imputed, header, [
                ["P1", 1, 2, 3, 4],
                ["P2", 4, 5, 6, 7],
                ["P3", 2, 3, 5, 6],
            ])
            self.write_tsv(labels, ["sample_id", "phenotype"], [
                ["S1", "control"], ["S2", "control"],
                ["S3", "case"], ["S4", "case"],
            ])
            report = evaluate_orthogonal_missingness(
                observed, dia, imputed, labels, outcome_column="phenotype", top_k=2
            )
            self.assertEqual(report["genuine_missing_cells_scored"], 2)
            self.assertEqual(report["paired_observed_cells_for_assay_alignment"], 10)
            self.assertEqual(report["biological_outcome_concordance"]["features_with_estimable_two_group_effects"], 3)
            self.assertEqual(report["biological_outcome_concordance"]["effect_direction_agreement"], 1.0)
            self.assertEqual(len(report["provenance"]["observed_assay_sha256"]), 64)

    def test_rejects_modified_observed_measurements(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            observed, dia, imputed, labels = [root / name for name in
                ("observed.tsv", "dia.tsv", "imputed.tsv", "labels.tsv")]
            header = ["feature", "S1", "S2", "S3", "S4"]
            rows = [["P1", 1, "", 3, 4], ["P2", 4, 5, 6, 7]]
            self.write_tsv(observed, header, rows)
            self.write_tsv(dia, header, [["P1", 1, 2, 3, 4], ["P2", 4, 5, 6, 7]])
            self.write_tsv(imputed, header, [["P1", 99, 2, 3, 4], ["P2", 4, 5, 6, 7]])
            self.write_tsv(labels, ["sample_id", "phenotype"], [
                ["S1", "control"], ["S2", "control"],
                ["S3", "case"], ["S4", "case"]])
            with self.assertRaisesRegex(ValueError, "modified"):
                evaluate_orthogonal_missingness(observed, dia, imputed, labels, outcome_column="phenotype")

    def test_rejects_missing_orthogonal_reference_for_all_missing_cells(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            observed, dia, imputed, labels = [root / name for name in
                ("observed.tsv", "dia.tsv", "imputed.tsv", "labels.tsv")]
            header = ["feature", "S1", "S2", "S3", "S4"]
            self.write_tsv(observed, header, [["P1", "", 2, 3, 4]])
            self.write_tsv(dia, header, [["P1", "", 2, 3, 4]])
            self.write_tsv(imputed, header, [["P1", 1, 2, 3, 4]])
            self.write_tsv(labels, ["sample_id", "phenotype"], [
                ["S1", "control"], ["S2", "control"],
                ["S3", "case"], ["S4", "case"]])
            with self.assertRaisesRegex(ValueError, "No genuinely missing"):
                evaluate_orthogonal_missingness(observed, dia, imputed, labels, outcome_column="phenotype")

    def test_requires_exact_sample_pairing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            observed, dia, imputed, labels = [root / name for name in
                ("observed.tsv", "dia.tsv", "imputed.tsv", "labels.tsv")]
            self.write_tsv(observed, ["feature", "S1", "S2", "S3", "S4"], [["P1", 1, "", 3, 4]])
            self.write_tsv(dia, ["feature", "S1", "S2", "S3", "OTHER"], [["P1", 1, 2, 3, 4]])
            self.write_tsv(imputed, ["feature", "S1", "S2", "S3", "S4"], [["P1", 1, 2, 3, 4]])
            self.write_tsv(labels, ["sample_id", "phenotype"], [
                ["S1", "control"], ["S2", "control"],
                ["S3", "case"], ["S4", "case"]])
            with self.assertRaisesRegex(ValueError, "sample identifiers"):
                evaluate_orthogonal_missingness(observed, dia, imputed, labels, outcome_column="phenotype")


if __name__ == "__main__":
    unittest.main()
