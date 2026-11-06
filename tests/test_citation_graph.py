"""Citation graph ranking tests."""
import unittest

from oracle.citation_graph import rank_citation_graph, traverse_citation_graph
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



    def test_bounded_multihop_traversal_follows_citation_direction(self):
        run = ResearchRun("Multi-hop citation graph")
        run.sources.extend([
            SourceRecord("Paper A", doi="10.1000/a", source_id="a"),
            SourceRecord("Paper B", doi="https://doi.org/10.1000/b", source_id="b"),
            SourceRecord("Paper C", doi="10.1000/c", source_id="c"),
            SourceRecord("Paper D", doi="10.1000/d", source_id="d"),
        ])
        run.citation_links.extend([
            CitationLink("a", "10.1000/b", relation="references"),
            CitationLink("b", "10.1000/c", relation="references"),
            CitationLink("d", "10.1000/a", relation="references"),
        ])
        outgoing = traverse_citation_graph(run, "a", direction="outgoing", max_depth=2)
        self.assertEqual([item["source_id"] for item in outgoing["results"]], ["b", "c"])
        self.assertEqual(outgoing["results"][1]["path_source_ids"], ["a", "b", "c"])
        incoming = traverse_citation_graph(run, "a", direction="incoming", max_depth=2)
        self.assertEqual([item["source_id"] for item in incoming["results"]], ["d"])
        self.assertEqual(incoming["results"][0]["depth"], 1)

    def test_multihop_traversal_limits_depth_and_validates_start(self):
        run = ResearchRun("Traversal limits")
        run.sources.extend([
            SourceRecord("A", doi="10.1000/a", source_id="a"),
            SourceRecord("B", doi="10.1000/b", source_id="b"),
            SourceRecord("C", doi="10.1000/c", source_id="c"),
        ])
        run.citation_links.extend([
            CitationLink("a", "10.1000/b"),
            CitationLink("b", "10.1000/c"),
        ])
        report = traverse_citation_graph(run, "a", direction="outgoing", max_depth=1)
        self.assertEqual([item["source_id"] for item in report["results"]], ["b"])
        with self.assertRaisesRegex(ValueError, "Start source not found"):
            traverse_citation_graph(run, "missing")
        with self.assertRaisesRegex(ValueError, "max_depth"):
            traverse_citation_graph(run, "a", max_depth=7)

    def test_ranking_parameters_are_validated(self):
        with self.assertRaises(ValueError):
            rank_citation_graph(ResearchRun("Test"), iterations=0)


if __name__ == "__main__":
    unittest.main()
