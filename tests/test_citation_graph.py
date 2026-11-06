"""Citation graph ranking tests."""
import unittest

from oracle.citation_graph import rank_citation_graph
from oracle.models import CitationLink, ResearchRun, SourceRecord


class CitationGraphTests(unittest.TestCase):
    def test_resolves_both_outgoing_and_incoming_edges(self):
        run = ResearchRun("Citation graph")
        run.sources.extend([
            SourceRecord("Foundational paper", doi="10.1000/a", source_id="src-a"),
            SourceRecord("Follow-up paper", doi="10.1000/b", source_id="src-b"),
            SourceRecord("Independent paper", doi="10.1000/c", source_id="src-c"),
        ])
        run.citation_links.extend([
            CitationLink("src-b", "10.1000/a", provider="Crossref", relation="references"),
            CitationLink("src-a", "10.1000/b", provider="OpenAlex", relation="cited_by"),
            CitationLink("src-c", "10.1000/missing", provider="Crossref", relation="references"),
        ])
        report = rank_citation_graph(run)
        self.assertEqual(report["nodes"], 3)
        self.assertEqual(report["resolved_edges"], 1)
        self.assertEqual(report["unresolved_citation_records"], 1)
        by_id = {item["source_id"]: item for item in report["ranked_sources"]}
        self.assertEqual(by_id["src-b"]["outgoing_edges"], 1)
        self.assertEqual(by_id["src-a"]["incoming_edges"], 1)
        self.assertAlmostEqual(sum(item["pagerank"] for item in report["ranked_sources"]), 1.0)

    def test_unknown_doi_targets_are_not_fabricated_as_nodes(self):
        run = ResearchRun("Unresolved target")
        run.sources.append(SourceRecord("Only local paper", doi="10.1000/local", source_id="src"))
        run.citation_links.append(CitationLink("src", "10.1000/external", target_title="External work"))
        report = rank_citation_graph(run)
        self.assertEqual(report["nodes"], 1)
        self.assertEqual(report["resolved_edges"], 0)
        self.assertEqual(report["unresolved_citation_records"], 1)

    def test_ranking_parameters_are_validated(self):
        with self.assertRaises(ValueError):
            rank_citation_graph(ResearchRun("Test"), iterations=0)


if __name__ == "__main__":
    unittest.main()
