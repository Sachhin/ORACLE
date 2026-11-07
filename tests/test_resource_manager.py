"""Tests for the universal scientific resource registry."""
import unittest

from oracle.resource_manager import ResourceManager


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
        self.assertEqual(items["pubchem"]["status"], "catalog_only")
        self.assertEqual(items["materials_project"]["authentication"], "api_key")

    def test_domain_filter_includes_universal_resources(self):
        items = ResourceManager.list_resources("biology_medicine")
        keys = {item["key"] for item in items}
        self.assertIn("europepmc", keys)
        self.assertIn("crossref", keys)
        self.assertIn("ncbi_geo", keys)
        self.assertNotIn("noaa_ncei", keys)

    def test_unknown_resource_is_rejected(self):
        with self.assertRaises(KeyError):
            ResourceManager.get_resource("made_up")

    def test_catalog_only_resource_does_not_fake_a_connector(self):
        manager = ResourceManager()
        with self.assertRaisesRegex(NotImplementedError, "catalog metadata only"):
            manager.search("battery cathode", resources=("pubchem",))


if __name__ == "__main__":
    unittest.main()
