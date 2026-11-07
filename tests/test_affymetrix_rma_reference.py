import csv, tempfile, unittest
from pathlib import Path
from scripts.compare_affymetrix_rma_reference import compare


class AffymetrixRMAReferenceTests(unittest.TestCase):
    def _write(self, path, samples, rows):
        with path.open("w", newline="", encoding="utf-8") as f:
            w=csv.writer(f, delimiter="\t")
            w.writerow(["feature", *samples])
            w.writerows(rows)

    def test_identical_platform_matched_matrix_passes(self):
        with tempfile.TemporaryDirectory() as d:
            o=Path(d)/"oracle.tsv"; r=Path(d)/"reference.tsv"
            rows=[["p1",1,2],["p2",3,4],["p3",5,7]]
            self._write(o,["GSM1","GSM2"],rows)
            self._write(r,["GSM1","GSM2"],rows)
            report=compare(o,r)
            self.assertEqual(report["status"],"PASS")
            self.assertEqual(report["metrics"]["rmse"],0)

    def test_rejects_sample_identity_mismatch(self):
        with tempfile.TemporaryDirectory() as d:
            o=Path(d)/"oracle.tsv"; r=Path(d)/"reference.tsv"
            rows=[["p1",1,2],["p2",3,4],["p3",5,7]]
            self._write(o,["GSM1","GSM2"],rows)
            self._write(r,["GSM1","GSM3"],rows)
            with self.assertRaisesRegex(ValueError,"sample identifiers"):
                compare(o,r)

    def test_numerical_threshold_failure_is_not_relabelled_pass(self):
        with tempfile.TemporaryDirectory() as d:
            o=Path(d)/"oracle.tsv"; r=Path(d)/"reference.tsv"
            self._write(o,["GSM1","GSM2"],[["p1",1,2],["p2",3,4],["p3",5,7]])
            self._write(r,["GSM1","GSM2"],[["p1",10,20],["p2",30,40],["p3",50,70]])
            report=compare(o,r)
            self.assertEqual(report["status"],"FAIL_NUMERICAL_TOLERANCE")


if __name__=="__main__":
    unittest.main()
