"""Unit tests for reproducible CRA metadata acquisition and conservative joins."""
import csv
import io
import json
import tempfile
import unittest
from pathlib import Path
try:
    from openpyxl import Workbook
except ImportError:
    raise unittest.SkipTest("openpyxl is installed by the dedicated CRA metadata workflow")

from scripts.acquire_cra000515_metadata import acquire_metadata


class FakeResponse:
    def __init__(self, content):
        self.content = content
    def raise_for_status(self):
        return None


class FakeSession:
    def __init__(self, run_csv, workbook):
        self.run_csv = run_csv
        self.workbook = workbook
        self.calls = []
    def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        return FakeResponse(self.run_csv if url.endswith("getRunInfoByCra") else self.workbook)


def workbook_bytes():
    wb = Workbook()
    ws = wb.active
    ws.title = "Sample"
    ws.append(["BioSample accession", "Sample name", "Group", "Age"])
    ws.append(["SAMC000001", "CHHA67", "Centenarian", "101"])
    ws.append(["SAMC000002", "CHHA68", "Centenarian offspring", "72"])
    exp = wb.create_sheet("Experiment")
    exp.append(["Experiment accession", "Library strategy"])
    exp.append(["CRX000001", "RNA-Seq"])
    run = wb.create_sheet("Run")
    run.append(["Run accession", "BioSample accession", "Experiment accession"])
    run.append(["CRR000001", "SAMC000001", "CRX000001"])
    run.append(["CRR000002", "SAMC000002", "CRX000001"])
    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


class CRAAcquisitionTests(unittest.TestCase):
    def test_acquires_raw_metadata_and_joins_only_by_biosample_accession(self):
        run_csv = (
            "Run accession,BioSample accession,Experiment accession,File size\n"
            "CRR000001,SAMC000001,CRX000001,100\n"
            "CRR000002,SAMC000002,CRX000001,200\n"
        ).encode()
        session = FakeSession(run_csv, workbook_bytes())
        with tempfile.TemporaryDirectory() as tmp:
            report = acquire_metadata(output_dir=tmp, session=session)
            self.assertEqual(report["run_count"], 2)
            self.assertEqual(report["unique_biosample_count"], 2)
            self.assertEqual(report["biosample_join"]["matched_runs"], 2)
            self.assertFalse(report["raw_bam_downloaded"])
            self.assertFalse(report["scientific_analysis_performed"])
            manifest = list(csv.DictReader(open(Path(tmp) / "CRA000515.run_biosample_manifest.csv")))
            self.assertEqual(manifest[0]["sample_alias"], "CHHA67")
            self.assertEqual(manifest[0]["raw_group_label"], "Centenarian")
            self.assertEqual(len(session.calls), 2)
            audit = json.loads((Path(tmp) / "CRA000515.metadata_audit.json").read_text())
            self.assertIn("SHA256SUMS.txt", {p.name for p in Path(tmp).iterdir()})

    def test_rejects_invalid_run_accessions(self):
        run_csv = b"Run accession,BioSample accession\nBAD,SAMC000001\n"
        session = FakeSession(run_csv, workbook_bytes())
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(RuntimeError, "invalid/missing CRR"):
                acquire_metadata(output_dir=tmp, session=session)

    def test_rejects_html_browser_challenge(self):
        session = FakeSession(b"<html>browser check</html>", workbook_bytes())
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(RuntimeError, "HTML challenge"):
                acquire_metadata(output_dir=tmp, session=session)

    def test_does_not_guess_group_when_sample_sheet_has_no_labels(self):
        wb = Workbook()
        ws = wb.active
        ws.title = "Sample"
        ws.append(["BioSample accession", "Sample name"])
        ws.append(["SAMC000001", "CHHA67"])
        exp = wb.create_sheet("Experiment")
        exp.append(["Experiment accession"])
        exp.append(["CRX000001"])
        run = wb.create_sheet("Run")
        run.append(["Run accession", "BioSample accession"])
        run.append(["CRR000001", "SAMC000001"])
        b = io.BytesIO()
        wb.save(b)
        session = FakeSession(b"Run accession,BioSample accession\nCRR000001,SAMC000001\n", b.getvalue())
        with tempfile.TemporaryDirectory() as tmp:
            report = acquire_metadata(output_dir=tmp, session=session)
            self.assertFalse(report["cohort_design_check"]["all_expected_group_labels_explicitly_present"])
            self.assertIsNone(report["cohort_design_check"]["metadata_age_column"])


if __name__ == "__main__":
    unittest.main()
