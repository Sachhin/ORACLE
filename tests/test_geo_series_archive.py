"""Tests for bounded GEO Series archive retrieval and extraction."""
import hashlib
import io
import tarfile
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


class _ArchiveClient(GEOSupplementaryClient):
    def _fetch_listing(self, url):
        return '<a href="GSE111062_RAW.tar">archive</a>'


def _tar_bytes(entries):
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode="w") as archive:
        for name, payload in entries:
            info = tarfile.TarInfo(name)
            info.size = len(payload)
            archive.addfile(info, io.BytesIO(payload))
    return stream.getvalue()


class GEOSeriesArchiveTests(unittest.TestCase):
    def test_download_official_raw_archive_with_checksum(self):
        payload = b"small tar fixture"
        with tempfile.TemporaryDirectory() as directory:
            with patch("oracle.geo_data.urlopen", return_value=_Response(payload)):
                report = _ArchiveClient().download_series_raw_archive(
                    "GSE111062", output_dir=directory
                )
            self.assertEqual(report["filename"], "GSE111062_RAW.tar")
            self.assertEqual(report["sha256"], hashlib.sha256(payload).hexdigest())
            self.assertEqual(Path(report["local_path"]).read_bytes(), payload)

    def test_extracts_gsm_files_and_skips_non_sample_files(self):
        payload = _tar_bytes([
            ("GSM3021223_GL48h1.txt.gz", b"counts"),
            ("README.txt", b"not a sample file"),
        ])
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / "input.tar"
            archive.write_bytes(payload)
            report = GEOSupplementaryClient.extract_raw_archive(archive)
            self.assertEqual(report["files_extracted"], 1)
            self.assertEqual(report["files"][0]["filename"], "GSM3021223_GL48h1.txt.gz")
            self.assertEqual(report["files"][0]["sha256"], hashlib.sha256(b"counts").hexdigest())
            self.assertEqual(len(report["skipped"]), 1)

    def test_rejects_path_traversal_member(self):
        payload = _tar_bytes([("../escape.txt", b"bad")])
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / "input.tar"
            archive.write_bytes(payload)
            report = GEOSupplementaryClient.extract_raw_archive(archive)
            self.assertEqual(report["files_extracted"], 0)
            self.assertFalse((Path(directory).parent / "escape.txt").exists())

    def test_rejects_total_uncompressed_size_over_limit(self):
        payload = _tar_bytes([("GSM123456_counts.txt", b"12345")])
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / "input.tar"
            archive.write_bytes(payload)
            with self.assertRaisesRegex(RuntimeError, "total uncompressed"):
                GEOSupplementaryClient.extract_raw_archive(
                    archive, max_total_bytes=4
                )

    def test_requires_unique_official_raw_tar(self):
        client = _ArchiveClient()
        with self.assertRaisesRegex(ValueError, "GSE"):
            client.download_series_raw_archive("GSM123456")


if __name__ == "__main__":
    unittest.main()
