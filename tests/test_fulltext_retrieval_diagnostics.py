from oracle.fulltext import OpenAccessFullTextClient
from oracle.models import ResearchRun, SourceRecord


def test_eligible_open_access_fulltext_fetch_is_counted_and_ingested():
    source = SourceRecord(
        title="Open access ageing study", pmcid="PMC12345",
        open_access=True, license="CC BY 4.0",
    )
    run = ResearchRun(question="human longevity", sources=[source])
    client = OpenAccessFullTextClient()
    client._fetch_xml = lambda _pmcid: b"<article><body><p>Ageing biology and longevity.</p></body></article>"

    report = client.ingest(run)

    assert report.eligible_sources == 1
    assert report.fetch_attempts == 1
    assert report.fetch_failures == 0
    assert report.full_text_records == 1
    assert any(item.locator == "Full text (PMC12345)" for item in run.evidence)


def test_fulltext_fetch_failure_is_reported_not_silently_counted_as_license_skip():
    source = SourceRecord(
        title="Open access ageing study", pmcid="PMC12345",
        open_access=True, license="CC BY 4.0",
    )
    run = ResearchRun(question="human longevity", sources=[source])
    client = OpenAccessFullTextClient()

    def fail(_pmcid):
        raise RuntimeError("test network failure")

    client._fetch_xml = fail
    report = client.ingest(run)

    assert report.eligible_sources == 1
    assert report.fetch_attempts == 1
    assert report.fetch_failures == 1
    assert report.skipped_license == 0
    assert "test network failure" in report.warnings[0]
