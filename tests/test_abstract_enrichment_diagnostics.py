from oracle.literature import LiteratureClient


def test_abstract_enrichment_reports_exact_recovery(monkeypatch):
    client = LiteratureClient()
    record = {"pmid": "12345", "doi": "", "abstract": ""}
    monkeypatch.setattr(client, "_get_json", lambda url: {
        "resultList": {"result": {"pmid": "12345", "title": "Aging study",
                                  "abstractText": "An abstract about aging."}}
    })

    stats = client._enrich_missing_abstracts([record])

    assert record["abstract"] == "An abstract about aging."
    assert stats == {"attempted": 1, "recovered": 1, "no_match": 0,
                     "failed": 0, "skipped_no_identifier": 0}


def test_abstract_enrichment_reports_missing_identifier_and_no_match(monkeypatch):
    client = LiteratureClient()
    records = [{"title": "No identifier", "abstract": ""},
               {"pmid": "999", "abstract": ""}]
    monkeypatch.setattr(client, "_get_json", lambda url: {"resultList": {"result": []}})

    stats = client._enrich_missing_abstracts(records)

    assert stats == {"attempted": 1, "recovered": 0, "no_match": 1,
                     "failed": 0, "skipped_no_identifier": 1}


def test_abstract_enrichment_reports_provider_failure(monkeypatch):
    client = LiteratureClient()
    record = {"doi": "10.1000/example", "abstract": ""}

    def fail(url):
        raise RuntimeError("temporary provider outage")

    monkeypatch.setattr(client, "_get_json", fail)
    stats = client._enrich_missing_abstracts([record])

    assert stats["attempted"] == 1
    assert stats["failed"] == 1
    assert stats["recovered"] == 0
