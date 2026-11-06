"""Tests for GEO GSM supplementary retrieval."""
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from oracle.geo_data import GEOSupplementaryClient


class _Response:
    def __init__(self, payload):
        self.payload = payload
        self.headers = {"Content-Length": str(len(payload))}
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False
    def read(self, size=-1):
        if not self.payload:
            return b""
        chunk, self.payload = self.payload[:size], self.payload[size:]
        return chunk


class _FixtureClient(GEOSupplementaryClient):
    def _fetch_listing(self, url):
        return '<a href="GSM3021223_GL48h1.txt.gz">file</a><a href="../">up</a>'


class GEOSampleDownloadTests(unittest.TestCase):
    def test_sample_directory_uses_gsm_range(self):
        self.assertEqual(
            GEOSupplementaryClient.sample_directory("GSM3021223"),
            "https://ftp.ncbi.nlm.nih.gov/geo/samples/GSM3021nnn/GSM3021223/suppl/",
        )
        with self.assertRaisesRegex(ValueError, "GSM"):
            GEOSupplementaryClient.sample_directory("GSE111062")

    def test_download_records_checksum_and_path(self):
        payload = b"gene_id\tcount\nAT1G01010\t42\n"
        with tempfile.TemporaryDirectory() as directory:
            with patch("oracle.geo_data.urlopen", return_value=_Response(payload)):
                report = _FixtureClient().download_sample_files(
                    ["GSM3021223"], output_dir=directory
                )
            self.assertEqual(report["files_downloaded"], 1)
            item = report["files"][0]
            self.assertEqual(item["status"], "downloaded")
            self.assertEqual(len(item["sha256"]), 64)
            self.assertEqual(Path(item["local_path"]).read_bytes(), payload)

    def test_duplicate_accessions_rejected(self):
        with self.assertRaisesRegex(ValueError, "unique"):
            _FixtureClient().download_sample_files(["GSM123456", "gsm123456"])

    def test_missing_accessions_rejected(self):
        with self.assertRaisesRegex(ValueError, "explicit GSM"):
            _FixtureClient().download_sample_files([])


if __name__ == "__main__":
    unittest.main()
