import gzip
import importlib.util
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "audit_gse262619_source_bundle.py"
SPEC = importlib.util.spec_from_file_location("audit_gse262619_source_bundle", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class GSE262619SourceBundleAuditTests(unittest.TestCase):
    def test_authenticates_sample_ids_and_explicit_characteristics(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            soft = root / "family.soft.gz"
            counts = root / "counts.txt.gz"
            output = root / "audit.json"
            manifest = root / "manifest.tsv"
            with gzip.open(soft, "wt", encoding="utf-8") as handle:
                handle.write(
                    "^SAMPLE = GSM100001\n"
                    "!Sample_title = 30y_F1\n"
                    "!Sample_geo_accession = GSM100001\n"
                    "!Sample_characteristics_ch1 = age: 30\n"
                    "!Sample_characteristics_ch1 = sex: female\n"
                    "^SAMPLE = GSM100002\n"
                    "!Sample_title = 75y_M1\n"
                    "!Sample_geo_accession = GSM100002\n"
                    "!Sample_characteristics_ch1 = age: 75\n"
                    "!Sample_characteristics_ch1 = sex: male\n"
                )
            with gzip.open(counts, "wt", encoding="utf-8") as handle:
                handle.write(
                    "gene\tcount.G30y_F1\tcount.G75y_M1\n"
                    "ENSG000001\t12\t19\n"
                    "ENSG000002\t4\t8\n"
                )
            report = MODULE.audit(counts, soft, output, manifest, expected_samples=2)
            self.assertEqual(report["status"], "PASS_SOURCE_BUNDLE")
            self.assertEqual(report["matched_sample_count"], 2)
            self.assertEqual(report["explicit_age_metadata_count"], 2)
            self.assertEqual(report["explicit_sex_metadata_count"], 0)
            self.assertEqual(report["title_coded_sex_count"], 2)
            self.assertTrue(output.exists())
            self.assertTrue(manifest.exists())

    def test_fails_closed_when_count_table_does_not_link_all_samples(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            soft = root / "family.soft.gz"
            counts = root / "counts.txt.gz"
            with gzip.open(soft, "wt", encoding="utf-8") as handle:
                handle.write(
                    "^SAMPLE = GSM100001\n"
                    "!Sample_title = sample one\n"
                    "!Sample_geo_accession = GSM100001\n"
                    "^SAMPLE = GSM100002\n"
                    "!Sample_title = sample two\n"
                    "!Sample_geo_accession = GSM100002\n"
                )
            with gzip.open(counts, "wt", encoding="utf-8") as handle:
                handle.write("gene\tGSM100001\nENSG000001\t12\n")
            report = MODULE.audit(
                counts, soft, root / "audit.json", root / "manifest.tsv",
                expected_samples=2,
            )
            self.assertEqual(report["status"], "BLOCKED_SOURCE_BUNDLE")
            self.assertEqual(report["matched_sample_count"], 1)
            self.assertTrue(report["issues"])


if __name__ == "__main__":
    unittest.main()
