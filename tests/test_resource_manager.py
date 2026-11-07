"""Tests for the universal scientific resource registry."""
import unittest

from oracle.resource_manager import ResourceManager
from oracle.literature import LiteratureClient


class ResourceManagerTests(unittest.TestCase):
    def test_catalog_covers_all_requested_science_areas(self):
        items = ResourceManager.list_resources()
        domains = {domain for item in items for domain in item["domains"]}
        for expected in ("biology_medicine", "physics_astronomy",
                         "computer_science_ai", "chemistry_materials",
                         "earth_environment", "mathematics_statistics",
                         "social_behavioral"):
            self.assertIn(expected, domains)

    def test_implemented_and_catalog_only_are_distinguished(self):
        items = {item["key"]: item for item in ResourceManager.list_resources()}
        self.assertEqual(items["europepmc"]["status"], "implemented")
        self.assertEqual(items["ncbi_geo"]["status"], "implemented")
        self.assertEqual(items["arxiv"]["status"], "implemented")
        self.assertEqual(items["pubchem"]["status"], "implemented")
        self.assertEqual(items["materials_project"]["authentication"], "api_key")

    def test_domain_filter_includes_universal_resources(self):
        items = ResourceManager.list_resources("biology_medicine")
        keys = {item["key"] for item in items}
        self.assertIn("europepmc", keys)
        self.assertIn("crossref", keys)
        self.assertIn("ncbi_geo", keys)
        self.assertIn("arxiv", keys)
        self.assertNotIn("noaa_ncei", keys)

    def test_arxiv_entry_normalizes_to_common_literature_schema(self):
        record = LiteratureClient._arxiv_record({
            "id": "https://arxiv.org/abs/2601.12345",
            "title": "  A New Method for Discovery  ",
            "summary": "This is an abstract with useful scientific detail.",
            "published": "2026-01-10T00:00:00Z",
            "authors": ["A. Researcher", "B. Scientist"],
            "categories": ["cs.AI"],
        })
        self.assertEqual(record["provider"], "arXiv")
        self.assertEqual(record["title"], "A New Method for Discovery")
        self.assertEqual(record["authors"], "A. Researcher; B. Scientist")
        self.assertEqual(record["year"], "2026-01-10")
        self.assertTrue(record["open_access"])
        self.assertEqual(record["categories"], ["cs.AI"])

    def test_arxiv_resource_dispatches_to_literature_provider(self):
        class StubClient:
            def search(self, query, limit, providers):
                return (query, limit, providers)
        result = ResourceManager(StubClient()).search(
            "black hole", limit=4, resources=("arxiv",))
        self.assertEqual(result, ("black hole", 4, ("arxiv",)))

    def test_pubchem_record_normalizes_structured_compound_properties(self):
        record = LiteratureClient._pubchem_record({
            "CID": 2244, "IUPACName": "acetic acid", "MolecularFormula": "C2H4O2",
            "MolecularWeight": "60.05", "CanonicalSMILES": "CC(=O)O",
        })
        self.assertEqual(record["provider"], "PubChem")
        self.assertEqual(record["compound_cid"], "2244")
        self.assertIn("Molecular formula: C2H4O2.", record["abstract"])
        self.assertEqual(record["molecular_weight"], "60.05")
        self.assertIn("/compound/2244", record["url"])

    def test_pubchem_resource_dispatches_to_literature_provider(self):
        class StubClient:
            def search(self, query, limit, providers):
                return (query, limit, providers)
        result = ResourceManager(StubClient()).search(
            "aspirin", limit=3, resources=("pubchem",))
        self.assertEqual(result, ("aspirin", 3, ("pubchem",)))

    def test_unknown_resource_is_rejected(self):
        with self.assertRaises(KeyError):
            ResourceManager.get_resource("made_up")

    def test_catalog_only_resource_does_not_fake_a_connector(self):
        manager = ResourceManager()
        with self.assertRaisesRegex(NotImplementedError, "catalog metadata only"):
            manager.search("battery cathode", resources=("pubchem",))


if __name__ == "__main__":
    unittest.main()
