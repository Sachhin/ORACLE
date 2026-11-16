import unittest
from types import SimpleNamespace

from oracle.models import ResearchRun
from oracle.orchestrator import OracleOrchestrator


class FakeStore:
    def log_event(self, *args, **kwargs):
        return None

    def save_run(self, *args, **kwargs):
        return None


class FakeLiteratureClient:
    def __init__(self):
        self.queries = []
        self.ingested = 0

    def search(self, query, limit=1, providers=("europepmc",)):
        self.queries.append((query, limit, providers))
        pmid = query.split(":", 1)[1]
        return SimpleNamespace(records=[{"pmid": pmid}],
                               retrieved=1, warnings=[])

    def ingest(self, run, report):
        self.ingested += 1
        source = report.records[0]
        run.sources.append(SimpleNamespace(
            doi=source.get("doi"), pmid=source.get("pmid")
        ))


class LongevityPriorArtSeedTests(unittest.TestCase):
    def test_longevity_mission_ingests_curated_pmid_seed(self):
        client = FakeLiteratureClient()
        orchestrator = OracleOrchestrator(
            store=FakeStore(), literature_enabled=True, literature_client=client
        )
        run = ResearchRun(question="Can we identify unknown mechanisms in human longevity?")
        orchestrator._ingest_longevity_prior_art_seed(run)
        self.assertEqual(client.queries[0][0], "EXT_ID:42030936")
        self.assertEqual(client.ingested, 5)
        self.assertTrue(any("known prior art" in item for item in run.findings))

    def test_non_longevity_mission_does_not_ingest_longevity_seed(self):
        client = FakeLiteratureClient()
        orchestrator = OracleOrchestrator(
            store=FakeStore(), literature_enabled=True, literature_client=client
        )
        run = ResearchRun(question="How do galaxies form?")
        orchestrator._ingest_longevity_prior_art_seed(run)
        self.assertEqual(client.queries, [])

    def test_existing_seed_source_is_not_duplicated(self):
        client = FakeLiteratureClient()
        orchestrator = OracleOrchestrator(
            store=FakeStore(), literature_enabled=True, literature_client=client
        )
        run = ResearchRun(question="Human longevity and mitochondrial translation")
        run.sources.append(SimpleNamespace(doi="10.1016/j.xcrm.2026.102767", pmid="42030936"))
        orchestrator._ingest_longevity_prior_art_seed(run)
        self.assertEqual(
            [query[0] for query in client.queries],
            ["EXT_ID:23698443", "EXT_ID:33472542", "EXT_ID:35078808", "EXT_ID:35476452"],
        )
        self.assertTrue(any("already present" in item for item in run.findings))


if __name__ == "__main__":
    unittest.main()
