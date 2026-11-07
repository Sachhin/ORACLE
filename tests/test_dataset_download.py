import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from oracle.dataset_download import _host_allowed, download_dataset_file, pdb_structure_download_url


class DatasetDownloadTests(unittest.TestCase):
    def test_allows_documented_openml_and_sra_data_hosts(self):
        self.assertTrue(_host_allowed("api.openml.org"))
        self.assertTrue(_host_allowed("sra-pub-run-odp.s3.amazonaws.com"))
        self.assertTrue(_host_allowed("ftp.ncbi.nlm.nih.gov"))
        self.assertTrue(_host_allowed("www.ncbi.nlm.nih.gov"))
        self.assertFalse(_host_allowed("evil-example.com"))

    def test_download_returns_sha256_and_byte_count(self):
        payload = b"research-data"
        response = MagicMock()
        response.__enter__.return_value = response
        response.__exit__.return_value = False
        response.geturl.return_value = "https://zenodo.org/records/1/files/data.csv"
        response.headers = {"Content-Length": str(len(payload))}
        response.read.side_effect = [payload, b""]
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "data.csv"
            with patch("oracle.dataset_download.urlopen", return_value=response):
                result = download_dataset_file(
                    "https://zenodo.org/records/1/files/data.csv", target
                )
            self.assertEqual(target.read_bytes(), payload)
            self.assertEqual(result["bytes"], len(payload))
            self.assertEqual(result["sha256"], hashlib.sha256(payload).hexdigest())

    def test_rejects_unapproved_or_non_https_urls(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(ValueError):
                download_dataset_file("http://zenodo.org/data.csv", Path(folder) / "x")
            with self.assertRaises(ValueError):
                download_dataset_file("https://example.com/data.csv", Path(folder) / "x")

    def test_rejects_oversized_content_length(self):
        response = MagicMock()
        response.__enter__.return_value = response
        response.__exit__.return_value = False
        response.geturl.return_value = "https://zenodo.org/data.bin"
        response.headers = {"Content-Length": "100"}
        with tempfile.TemporaryDirectory() as folder:
            with patch("oracle.dataset_download.urlopen", return_value=response):
                with self.assertRaises(ValueError):
                    download_dataset_file(
                        "https://zenodo.org/data.bin", Path(folder) / "x", max_bytes=10
                    )

    def test_pdb_download_url_validates_accession_and_format(self):
        self.assertEqual(
            pdb_structure_download_url("1abc"),
            "https://files.rcsb.org/download/1ABC.cif",
        )
        with self.assertRaises(ValueError):
            pdb_structure_download_url("../etc/passwd")
        with self.assertRaises(ValueError):
            pdb_structure_download_url("1ABC", "exe")


if __name__ == "__main__":
    unittest.main()
