"""Tests for bounded Crossref outgoing citation discovery."""
import unittest
from oracle.citation_network import CrossrefCitationClient
from oracle.models import ResearchRun, SourceRecord


class MultiHopCrossrefClient(CrossrefCitationClient):
    def __init__(self):
        super().__init__(max_depth=2, max_nodes=5, max_sources=2, max_references_per_source=5)

    def _get_json(self, doi):
        normalized = doi.lower().replace("https://doi.org/", "")
        if normalized == "10.1000/root":
            return {"message": {"reference": [
                {"DOI": "10.1000/next", "article-title": "Second paper", "year": "2024"}
            ]}}
        if normalized == "10.1000/next":
            return {"message": {"reference": [
                {"DOI": "10.1000/third", "article-title": "Third paper", "year": "2025"}
            ]}}
        return {"message": {"reference": []}}


class CitationNetworkTests(unittest.TestCase):
    def test_bounded_multihop_outgoing_adds_metadata_nodes(self):
        run = ResearchRun("Crossref expansion")
        run.sources.append(SourceRecord("Root", doi="10.1000/root", source_id="root"))
        report = MultiHopCrossrefClient().discover(run)
        self.assertEqual(report.depth_reached, 2)
        self.assertEqual(report.external_nodes_created, 2)
        self.assertEqual(report.links_created, 2)
        self.assertEqual(len(run.sources), 3)
        self.assertTrue(all(x.source_type == "external_citation" for x in run.sources[1:]))
        self.assertTrue(all(x.relation == "references" for x in run.citation_links))

    def test_depth_and_node_limits_are_validated(self):
        with self.assertRaises(ValueError):
            CrossrefCitationClient(max_depth=6)
        with self.assertRaises(ValueError):
            CrossrefCitationClient(max_nodes=251)


if __name__ == "__main__":
    unittest.main()
