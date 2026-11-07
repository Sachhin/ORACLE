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



def test_plain_language_young_old_gene_expression_question_routes_to_aging_profile():
    query = "How does gene expression change between young and old humans?"
    assert LiteratureClient._topic_profile(query) == "human_longevity"
    assert len(LiteratureClient.geo_dataset_queries(query)) == 3


def test_age_related_paper_is_kept_but_figure_caption_is_rejected():
    query = "How does gene expression change between young and old humans?"
    paper = {"title": "Age-related gene expression changes in human blood", "abstract": ""}
    caption = {"title": "Figure 3. Gene decoding of age-related changes in expression", "abstract": ""}
    assert LiteratureClient._passes_topic_gate(query, paper)
    assert not LiteratureClient._passes_topic_gate(query, caption)


def test_young_old_query_filters_unrelated_titles():
    query = "How does gene expression change between young and old humans?"
    unrelated = {"title": "Rice genes show drought-induced differential expression", "abstract": ""}
    assert not LiteratureClient._passes_topic_gate(query, unrelated)
