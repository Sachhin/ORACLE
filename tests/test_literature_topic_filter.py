from types import SimpleNamespace

from oracle.literature import LiteratureClient
from oracle.orchestrator import OracleOrchestrator


def test_longevity_topic_gate_rejects_unrelated_unknown_discoveries():
    query = "Can we identify previously unknown biological mechanisms involved in human longevity?"
    unrelated = {"title": "Previously unknown phages discovered in gut metagenomes", "abstract": ""}
    relevant = {"title": "Genetic mechanisms of exceptional human longevity", "abstract": ""}
    ageing = {"title": "Cellular senescence and human ageing", "abstract": "Molecular pathways."}

    assert not LiteratureClient._passes_topic_gate(query, unrelated)
    assert LiteratureClient._passes_topic_gate(query, relevant)
    assert LiteratureClient._passes_topic_gate(query, ageing)


def test_longevity_relevance_score_prefers_title_level_topic_match():
    query = "human longevity biological mechanisms"
    relevant = {"title": "Human longevity and genetic mechanisms", "abstract": ""}
    weak = {"title": "Genetic mechanisms in yeast", "abstract": ""}

    assert LiteratureClient._relevance_score(query, relevant) > LiteratureClient._relevance_score(query, weak)


def test_task_search_query_preserves_longevity_mission_context():
    task = SimpleNamespace(name="Look for overlooked mechanisms",
                           description="Search for counterexamples in available research.")
    query = OracleOrchestrator._task_search_query(
        task, "Can we identify previously unknown biological mechanisms involved in human longevity?"
    )

    assert "human longevity aging mechanisms" in query
