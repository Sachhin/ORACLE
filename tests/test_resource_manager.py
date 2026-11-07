"""Tests for the universal scientific resource registry."""
import unittest
from unittest.mock import patch

from oracle.resource_manager import ResourceManager, resolve_literature_providers
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
        self.assertEqual(items["materials_project"]["status"], "catalog_only")
        self.assertEqual(items["materials_project"]["authentication"], "api_key")

    def test_domain_filter_includes_universal_resources(self):
        items = ResourceManager.list_resources("biology_medicine")
        keys = {item["key"] for item in items}
        self.assertIn("europepmc", keys)
        self.assertIn("crossref", keys)
        self.assertIn("ncbi_geo", keys)
        self.assertNotIn("arxiv", keys)
        self.assertIn("pubchem", keys)
        self.assertNotIn("noaa_ncei", keys)

    def test_cross_domain_resources_are_catalogued_with_truthful_status(self):
        items = {item["key"]: item for item in ResourceManager.list_resources()}
        for key in ("openalex", "gbif", "world_bank", "pdb", "pride", "openml", "huggingface_datasets"):
            self.assertEqual(items[key]["status"], "implemented")
        for key in ("materials_project", "nomad", "nasa_ads", "pdb",
                    "nasa_earthdata", "usgs", "pangaea",
                    "eric", "philpapers", "icpsr",
                    "internet_archive", "europeana", "smithsonian_open_access"):
            self.assertEqual(items[key]["status"], "catalog_only")

    def test_domain_alias_resource_filtering(self):
        keys = {item["key"] for item in ResourceManager.list_resources("history")}
        self.assertIn("openalex", keys)
        self.assertIn("internet_archive", keys)

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

    def test_pubchem_search_uses_pug_rest_and_normalizes_results(self):
        client = LiteratureClient()
        payload = {"PropertyTable": {"Properties": [{
            "CID": 2244, "IUPACName": "acetic acid", "MolecularFormula": "C2H4O2",
            "MolecularWeight": "60.05", "CanonicalSMILES": "CC(=O)O",
        }]}}
        with patch.object(client, "_get_json", return_value=payload) as get_json:
            records = client._search_pubchem("acetic acid", 5)
        requested_url = get_json.call_args.args[0]
        self.assertIn("/compound/name/acetic%20acid/property/", requested_url)
        self.assertIn("MaxRecords=5", requested_url)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["compound_cid"], "2244")

    def test_pubchem_resource_dispatches_to_literature_provider(self):
        class StubClient:
            def search(self, query, limit, providers):
                return (query, limit, providers)
        result = ResourceManager(StubClient()).search(
            "aspirin", limit=3, resources=("pubchem",))
        self.assertEqual(result, ("aspirin", 3, ("pubchem",)))

    def test_geo_provider_alias_dispatches_to_ncbi_geo_connector(self):
        class StubClient:
            def search(self, query, limit, providers):
                return (query, limit, providers)
        result = ResourceManager(StubClient()).search(
            "human longevity", limit=5, resources=("geo",))
        self.assertEqual(result, ("human longevity", 5, ("geo",)))

    def test_openalex_gbif_and_world_bank_dispatch_through_resource_manager(self):
        class StubClient:
            def search(self, query, limit, providers):
                return (query, limit, providers)
        manager = ResourceManager(StubClient())
        for key in ("openalex", "gbif", "world_bank"):
            result = manager.search("test query", limit=2, resources=(key,))
            self.assertEqual(result, ("test query", 2, (key,)))

    def test_unknown_resource_is_rejected(self):
        with self.assertRaises(KeyError):
            ResourceManager.get_resource("made_up")

    def test_catalog_only_resource_does_not_fake_a_connector(self):
        manager = ResourceManager()
        with self.assertRaisesRegex(NotImplementedError, "catalog metadata only"):
            manager.search("battery cathode", resources=("materials_project",))


    def test_auto_source_selection_uses_domain_adapters(self):
        self.assertEqual(
            resolve_literature_providers("Can we identify aging mechanisms?", "auto"),
            ("openalex", "europepmc", "crossref", "geo", "pubchem", "clinical_trials", "sra", "zenodo", "harvard_dataverse", "pdb", "pride"),
        )
        self.assertEqual(
            resolve_literature_providers("Can quantum gravity be tested?", "auto"),
            ("openalex", "arxiv", "crossref"),
        )
        self.assertEqual(
            resolve_literature_providers("How does a polymer catalyst work?", "auto"),
            ("openalex", "pubchem", "crossref"),
        )

    def test_auto_source_selection_uses_openalex_for_humanities_and_social_sciences(self):
        self.assertEqual(
            resolve_literature_providers("How did the Roman Empire collapse?", "auto"),
            ("openalex", "crossref"),
        )
        self.assertEqual(
            resolve_literature_providers("How does GDP growth influence unemployment rates?", "auto"),
            ("openalex", "crossref", "world_bank"),
        )
        self.assertEqual(
            resolve_literature_providers("How is climate change affecting biodiversity?", "auto"),
            ("openalex", "crossref", "gbif", "noaa_ncei", "zenodo"),
        )

    def test_openalex_inverted_abstract_is_reconstructed(self):
        client = LiteratureClient()
        payload = {"results": [{
            "id": "https://openalex.org/W1", "doi": "https://doi.org/10.1/example",
            "title": "A test paper", "publication_year": 2024,
            "authorships": [{"author": {"display_name": "A Scientist"}}],
            "primary_location": {"source": {"display_name": "Test Journal"}},
            "open_access": {"is_oa": True, "oa_status": "gold"},
            "cited_by_count": 12, "type": "article",
            "abstract_inverted_index": {"World": [1], "Hello": [0], "again.": [2]},
        }]}
        with patch.object(client, "_get_json", return_value=payload):
            records = client._search_openalex("test", 2)
        self.assertEqual(records[0]["abstract"], "Hello World again.")
        self.assertEqual(records[0]["provider"], "OpenAlex")
        self.assertTrue(records[0]["open_access"])

    def test_gbif_search_normalizes_occurrence_records(self):
        client = LiteratureClient()
        with patch.object(client, "_get_json", return_value={"results": [{
            "key": 123, "scientificName": "Homo sapiens", "country": "India",
            "year": 2025, "license": "CC_BY_4_0", "basisOfRecord": "HUMAN_OBSERVATION",
        }]}):
            records = client._search_gbif("human", 3)
        self.assertEqual(records[0]["provider"], "GBIF")
        self.assertIn("Homo sapiens", records[0]["abstract"])
        self.assertEqual(records[0]["url"], "https://www.gbif.org/occurrence/123")

    def test_world_bank_search_ranks_indicator_metadata(self):
        client = LiteratureClient()
        payload = [ {"page": 1}, [
            {"id": "SP.DYN.LE00.IN", "name": "Life expectancy at birth",
             "sourceNote": "Average number of years."},
            {"id": "NY.GDP.MKTP.CD", "name": "GDP current US dollars",
             "sourceNote": "Gross domestic product."},
        ]]
        with patch.object(client, "_get_json", return_value=payload):
            records = client._search_world_bank("life expectancy", 1)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["provider"], "World Bank")
        self.assertEqual(records[0]["provider_id"], "SP.DYN.LE00.IN")


    def test_clinical_trials_search_normalizes_study_records(self):
        client = LiteratureClient()
        payload = {"studies": [{"protocolSection": {
            "identificationModule": {"nctId": "NCT01234567", "briefTitle": "Longevity study"},
            "descriptionModule": {"briefSummary": "A human clinical study."},
            "designModule": {"studyType": "OBSERVATIONAL"},
            "statusModule": {"overallStatus": "COMPLETED", "studyFirstPostDateStruct": {"date": "2024-01-01"}},
            "sponsorCollaboratorsModule": {"leadSponsor": {"name": "University"}},
        }}]}
        with patch.object(client, "_get_json", return_value=payload):
            records = client._search_clinical_trials("longevity", 3)
        self.assertEqual(records[0]["provider_id"], "NCT01234567")
        self.assertIn("clinicaltrials.gov/study/NCT01234567", records[0]["url"])

    def test_zenodo_search_preserves_doi_license_and_file_metadata(self):
        client = LiteratureClient()
        payload = {"hits": {"hits": [{
            "id": 42, "doi": "10.5281/zenodo.42",
            "metadata": {"title": "A dataset", "description": "Dataset summary",
                         "publication_date": "2025-01-01",
                         "creators": [{"name": "Researcher"}],
                         "license": {"id": "cc-by-4.0"},
                         "resource_type": {"type": "dataset"}},
            "links": {"self_html": "https://zenodo.org/records/42"}, "files": [{"key": "data.csv"}],
        }]}}
        with patch.object(client, "_get_json", return_value=payload):
            records = client._search_zenodo("dataset", 2)
        self.assertEqual(records[0]["doi"], "10.5281/zenodo.42")
        self.assertEqual(records[0]["license"], "cc-by-4.0")
        self.assertEqual(records[0]["files"][0]["key"], "data.csv")

    def test_dataverse_search_normalizes_dataset_records(self):
        client = LiteratureClient()
        payload = {"data": {"items": [{
            "global_id": "doi:10.1234/ABC", "name": "Study dataset",
            "description": "Dataset description", "url": "https://dataverse.harvard.edu/dataset.xhtml?id=1",
        }]}}
        with patch.object(client, "_get_json", return_value=payload):
            records = client._search_dataverse("study", 2)
        self.assertEqual(records[0]["provider_id"], "doi:10.1234/ABC")
        self.assertEqual(records[0]["provider"], "Harvard Dataverse")

    def test_sra_search_resolves_accession_and_source_url(self):
        client = LiteratureClient()
        payloads = [
            {"esearchresult": {"idlist": ["123"]}},
            {"result": {"123": {"title": "RNA sequencing study", "expXml": "<Experiment accession='SRX12345'/>"}}},
        ]
        with patch.object(client, "_get_json", side_effect=payloads):
            records = client._search_sra("RNA sequencing", 2)
        self.assertEqual(records[0]["dataset_accession"], "SRX12345")
        self.assertIn("/sra/SRX12345", records[0]["url"])

    def test_new_dataset_connectors_dispatch(self):
        class StubClient:
            def search(self, query, limit, providers):
                return (query, limit, providers)
        manager = ResourceManager(StubClient())
        for key in ("clinical_trials", "zenodo", "harvard_dataverse", "sra", "pdb", "pride", "openml", "huggingface_datasets"):
            result = manager.search("test dataset", limit=2, resources=(key,))
            self.assertEqual(result[2], (key,))


    def test_pdb_search_retrieves_structure_metadata(self):
        client = LiteratureClient()
        payloads = [
            {"result_set": [{"identifier": "1ABC"}]},
            {"struct": {"title": "Test protein"}, "exptl": [{"method": "X-RAY DIFFRACTION"}],
             "rcsb_accession_info": {"initial_release_date": "2024-01-01T00:00:00Z"}},
        ]
        with patch.object(client, "_get_json", side_effect=payloads):
            records = client._search_pdb("test protein", 2)
        self.assertEqual(records[0]["dataset_accession"], "1ABC")
        self.assertIn("X-RAY", records[0]["abstract"])

    def test_pride_search_normalizes_proteomics_project(self):
        client = LiteratureClient()
        payload = {"content": [{"accession": "PXD012345", "title": "Proteomics study",
                                "projectDescription": "Mass spectrometry data"}]}
        with patch.object(client, "_get_json", return_value=payload):
            records = client._search_pride("proteomics", 2)
        self.assertEqual(records[0]["dataset_accession"], "PXD012345")
        self.assertIn("pride/archive/projects/PXD012345", records[0]["url"])

    def test_huggingface_search_preserves_gated_and_license_metadata(self):
        client = LiteratureClient()
        payload = [{"id": "org/longevity-data", "gated": "auto",
                    "cardData": {"description": "A dataset", "license": "cc-by-4.0"}}]
        with patch.object(client, "_get_json", return_value=payload):
            records = client._search_huggingface_datasets("longevity", 2)
        self.assertFalse(records[0]["open_access"])
        self.assertEqual(records[0]["license"], "cc-by-4.0")

    def test_openml_search_normalizes_dataset_identifier(self):
        client = LiteratureClient()
        payload = {"data": {"dataset": [{"did": "42", "name": "A benchmark",
                                         "licence": "Public"}]}}
        with patch.object(client, "_get_json", return_value=payload):
            records = client._search_openml("benchmark", 2)
        self.assertEqual(records[0]["dataset_accession"], "42")
        self.assertIn("/d/42", records[0]["url"])

if __name__ == "__main__":
    unittest.main()

