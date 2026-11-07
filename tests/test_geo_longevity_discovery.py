"""Tests for independent, human-specific GEO dataset discovery."""
import unittest

from oracle.literature import LiteratureClient


class _FixtureGEOClient(LiteratureClient):
    def __init__(self):
        super().__init__()
        self.queries = []

    def _search_geo(self, query, limit):
        self.queries.append((query, limit))
        if "longevity" in query:
            return [
                {"dataset": True, "dataset_accession": "GSE123456",
                 "title": "Expression profile of a human cohort", "abstract": "",
                 "provider": "NCBI GEO", "url": "https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE123456"},
            ]
        if "aging" in query and "mitochondria" not in query:
            return [
                {"dataset": True, "dataset_accession": "GSE123456",
                 "title": "Duplicate human cohort", "abstract": "", "provider": "NCBI GEO"},
                {"dataset": True, "dataset_accession": "GSE234567",
                 "title": "Human ageing expression study", "abstract": "",
                 "provider": "NCBI GEO", "url": "https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE234567"},
            ]
        return []


class GEOLongevityDiscoveryTests(unittest.TestCase):
    def test_longevity_search_uses_multiple_human_specific_queries(self):
        client = _FixtureGEOClient()
        report = client.search_geo_datasets(
            "Can we identify previously unknown biological mechanisms involved in human longevity?",
            limit=20,
        )
        self.assertEqual(len(client.queries), 3)
        self.assertTrue(all('"Homo sapiens"[Organism]' in query for query, _ in client.queries))
        self.assertEqual(report.retrieved, 2)
        self.assertEqual(
            {item["dataset_accession"] for item in report.records},
            {"GSE123456", "GSE234567"},
        )

    def test_dataset_is_not_rejected_by_publication_title_gate(self):
        record = {
            "dataset": True,
            "dataset_accession": "GSE123456",
            "title": "Expression profile of a human cohort",
            "abstract": "",
        }
        self.assertTrue(LiteratureClient._passes_topic_gate(
            "human longevity mechanisms", record
        ))

    def test_non_gse_results_are_not_used_for_supplementary_discovery(self):
        class InvalidAccessionClient(_FixtureGEOClient):
            def _search_geo(self, query, limit):
                return [{"dataset": True, "dataset_accession": "GDS123",
                         "title": "Not a GEO Series"}]
        report = InvalidAccessionClient().search_geo_datasets("human longevity")
        self.assertEqual(report.retrieved, 0)
        self.assertTrue(any("valid GSE accession" in warning for warning in report.warnings))


if __name__ == "__main__":
    unittest.main()
