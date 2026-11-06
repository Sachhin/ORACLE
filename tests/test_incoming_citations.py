"""Tests for bounded incoming-citation discovery."""
import unittest
from oracle.incoming_citations import OpenAlexIncomingCitationClient
from oracle.models import ResearchRun, SourceRecord


class FakeOpenAlex(OpenAlexIncomingCitationClient):
    def __init__(self):
        super().__init__(max_sources=3, max_citing_works=10)
        self.urls = []

    def _get_json(self, url):
        self.urls.append(url)
        if "/works/https://doi.org/" in url:
            return {"id": "https://openalex.org/W123"}
        return {"results": [
            {"id": "https://openalex.org/W456", "doi": "https://doi.org/10.1000/citing",
             "title": "A later paper", "publication_year": 2025,
             "authorships": [{"author": {"display_name": "A Researcher"}}]},
            {"id": "https://openalex.org/W457", "doi": None,
             "title": "A citing preprint", "publication_year": 2024, "authorships": []},
        ]}


class IncomingCitationTests(unittest.TestCase):
    def test_discovers_incoming_links_with_direction_and_provenance(self):
        run = ResearchRun("Citation test")
        source = SourceRecord("Cited paper", doi="10.1000/cited")
        run.sources.append(source)
        client = FakeOpenAlex()
        report = client.discover(run)
        self.assertEqual(report.sources_examined, 1)
        self.assertEqual(report.citing_works_examined, 2)
        self.assertEqual(report.links_created, 2)
        self.assertEqual(report.works_without_doi, 1)
        self.assertTrue(all(item.relation == "cited_by" for item in run.citation_links))
        self.assertTrue(all(item.provider == "OpenAlex" for item in run.citation_links))
        self.assertEqual(run.citation_links[0].target_author, "A Researcher")

    def test_discovery_is_idempotent(self):
        run = ResearchRun("Citation idempotency")
        run.sources.append(SourceRecord("Cited paper", doi="10.1000/cited", source_id="src-cited"))
        client = FakeOpenAlex()
        first = client.discover(run)
        second = client.discover(run)
        self.assertEqual(first.links_created, 2)
        self.assertEqual(second.links_created, 0)
        self.assertEqual(len(run.citation_links), 2)

    def test_limits_are_validated(self):
        with self.assertRaises(ValueError):
            OpenAlexIncomingCitationClient(max_sources=0)


if __name__ == "__main__":
    unittest.main()
