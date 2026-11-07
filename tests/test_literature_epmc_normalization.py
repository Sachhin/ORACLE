from oracle.literature import LiteratureClient, LiteratureSearchError


def test_epmc_record_accepts_scalar_pubtype_and_license_values():
    record = LiteratureClient._epmc_record({
        "id": "123", "doi": "10.1000/example", "pmid": "456",
        "title": "Aging mechanisms", "abstractText": "An abstract.",
        "pubTypeList": {"pubType": ["Journal Article", {"type": "Review"}]},
        "licenseList": {"license": ["CC BY", {"license": "CC0"}]},
        "isOpenAccess": "Y",
    })

    assert record["publication_type"] == "Journal Article, Review"
    assert record["license"] == "CC BY, CC0"
    assert record["abstract"] == "An abstract."
    assert record["open_access"] is True


def test_epmc_record_rejects_non_object_result_with_clear_error():
    try:
        LiteratureClient._epmc_record("unexpected scalar")
    except ValueError as exc:
        assert "must be an object" in str(exc)
    else:
        raise AssertionError("Expected malformed result to be rejected")


def test_europepmc_search_accepts_single_object_result():
    client = LiteratureClient()
    client._get_json = lambda _url: {
        "resultList": {
            "result": {
                "id": "1", "title": "Human longevity",
                "pubTypeList": {"pubType": "Journal Article"},
                "licenseList": {"license": "CC BY"},
            }
        }
    }

    records = client._search_europepmc("human longevity", 5)

    assert len(records) == 1
    assert records[0]["title"] == "Human longevity"
    assert records[0]["publication_type"] == "Journal Article"
    assert records[0]["license"] == "CC BY"


def test_europepmc_search_reports_invalid_response_shape():
    client = LiteratureClient()
    client._get_json = lambda _url: {"resultList": "invalid"}

    try:
        client._search_europepmc("human longevity", 5)
    except LiteratureSearchError as exc:
        assert "invalid resultList" in str(exc)
    else:
        raise AssertionError("Expected invalid Europe PMC response to fail clearly")
