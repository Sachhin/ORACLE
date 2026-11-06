"""Tests for ORACLE's offline research and knowledge foundation."""
import tempfile
import unittest
from pathlib import Path

from oracle.decision import choose_next_action
from oracle.knowledge import KnowledgeBase
from oracle.models import (
    Evidence, EvidenceKind, EvidenceStance, ExperimentStatus, Hypothesis,
    ResearchMode, ResearchRun, RunStatus,
)
from oracle.orchestrator import OracleOrchestrator
from oracle.storage import ResearchStore


class OracleTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = ResearchStore(Path(self.tmp.name) / "test.sqlite3")

    def tearDown(self):
        self.tmp.cleanup()

    def test_empty_question_rejected(self):
        with self.assertRaises(ValueError):
            OracleOrchestrator(self.store).run("  ")

    def test_cycle_budget_validated(self):
        with self.assertRaises(ValueError):
            OracleOrchestrator(self.store).run("A question?", max_cycles=0)

    def test_integrated_run_completes_and_persists(self):
        run = OracleOrchestrator(self.store).run(
            "How does a fertilized egg develop into an organism?", max_cycles=2
        )
        self.assertEqual(run.status, RunStatus.COMPLETED)
        self.assertEqual(run.current_cycle, 2)
        self.assertGreaterEqual(len(run.evidence), 1)
        self.assertGreaterEqual(len(run.hypotheses), 2)
        self.assertEqual(len(run.hypothesis_groups), 1)
        self.assertEqual(len(run.hypothesis_groups[0].hypothesis_ids), 2)
        self.assertGreaterEqual(len(run.experiments), 1)
        self.assertEqual(self.store.load_run(run.run_id).status, RunStatus.COMPLETED)
        self.assertGreater(len(self.store.list_events(run.run_id)), 0)

    def test_experiment_is_proposed_not_performed(self):
        run = OracleOrchestrator(self.store).run("Test question", max_cycles=1)
        self.assertTrue(all(e.status == ExperimentStatus.PROPOSED for e in run.experiments))

    def test_research_only_mode_skips_discovery_directions(self):
        run = OracleOrchestrator(self.store).run(
            "Test question", ResearchMode.DEEP_RESEARCH, max_cycles=1
        )
        self.assertEqual(run.findings.count("Look for overlooked mechanisms"), 0)

    def test_decision_stops_on_no_progress(self):
        self.assertEqual(choose_next_action(1, 4, progress=False).action, "stop")

    def test_decision_allows_one_bounded_stagnant_cycle(self):
        decision = choose_next_action(
            2, 5, progress=False, consecutive_no_progress=0, max_no_progress=2
        )
        self.assertEqual(decision.action, "continue")
        decision = choose_next_action(
            3, 5, progress=False, consecutive_no_progress=1, max_no_progress=2
        )
        self.assertEqual(decision.action, "stop")

    def test_critical_integrity_warning_stops_run(self):
        decision = choose_next_action(1, 5, progress=True, critical_warnings=1)
        self.assertEqual(decision.action, "stop")

    def test_evidence_links_and_uncertainty_are_auditable(self):
        run = OracleOrchestrator(self.store).run("Test claim", max_cycles=1)
        kb = KnowledgeBase()
        claim = kb.add_claim(run, "Cell fate depends on signaling.")
        ev = Evidence("Signaling observation", "Dataset X", EvidenceKind.DATASET)
        run.evidence.append(ev)
        kb.link_evidence(run, claim.claim_id, ev.evidence_id, EvidenceStance.SUPPORTS, 0.7)
        assessment = kb.assess_claim(run, claim.claim_id)
        self.assertEqual(assessment.evidence_count, 1)
        self.assertAlmostEqual(assessment.confidence_estimate, 1.0)
        self.assertIn("not a calibrated probability", assessment.rationale)

    def test_contradictions_are_detected_and_not_silently_resolved(self):
        run = OracleOrchestrator(self.store).run("Test", max_cycles=1)
        kb = KnowledgeBase()
        a = kb.add_claim(run, "Gene X is required.")
        b = kb.add_claim(run, "Gene X is not required.")
        self.assertIn((a.claim_id, b.claim_id), kb.detect_contradictions(run))
        self.assertEqual(a.status, "unassessed")
        self.assertEqual(b.status, "unassessed")

    def test_competing_hypotheses_share_a_group(self):
        run = ResearchRun("Test")
        kb = KnowledgeBase()
        first = Hypothesis("Model A", "Reason A")
        second = Hypothesis("Model B", "Reason B")
        group = kb.add_hypothesis(run, first)
        same = kb.add_hypothesis(run, second, group.group_id)
        self.assertEqual(group.group_id, same.group_id)
        self.assertEqual(len(group.hypothesis_ids), 2)

    def test_provenance_revisions_and_source_reliability_persist(self):
        from oracle.models import SourceRecord
        run = ResearchRun("Provenance test")
        kb = KnowledgeBase()
        source = kb.add_source(run, SourceRecord(
            title="Example paper", url="https://example.org/paper",
            reliability_score=0.8, reliability_rationale="Peer-reviewed primary study."
        ))
        evidence = Evidence("Observation", source.title, source_id=source.source_id,
                            reliability=0.8, dependence_group="same-study")
        run.evidence.append(evidence)
        claim = kb.add_claim(run, "Observation A is associated with outcome B.")
        kb.link_evidence(run, claim.claim_id, evidence.evidence_id, EvidenceStance.SUPPORTS)
        kb.revise_claim(run, claim.claim_id, "Observation A may be associated with outcome B.",
                        "New evidence narrowed the wording.")
        self.store.save_run(run)
        loaded = self.store.load_run(run.run_id)
        self.assertEqual(loaded.claims[0].revision, 2)
        self.assertEqual(len(loaded.claim_revisions), 1)
        self.assertEqual(loaded.sources[0].source_id, source.source_id)
        self.assertEqual(len(loaded.evidence_claim_links), 1)

    def test_correlated_evidence_is_not_double_counted(self):
        run = ResearchRun("Dependence test")
        kb = KnowledgeBase()
        claim = kb.add_claim(run, "X causes Y.")
        for label in ("republished result", "same underlying cohort"):
            evidence = Evidence(label, "One cohort", reliability=0.9, dependence_group="cohort-1")
            run.evidence.append(evidence)
            kb.link_evidence(run, claim.claim_id, evidence.evidence_id, EvidenceStance.SUPPORTS)
        assessment = kb.assess_claim(run, claim.claim_id)
        self.assertEqual(assessment.supporting_weight, 0.9)
        self.assertEqual(assessment.independent_evidence_groups, 1)

    def test_contradiction_candidates_require_review(self):
        run = ResearchRun("Contradiction review")
        kb = KnowledgeBase()
        first = kb.add_claim(run, "Gene X is required.")
        kb.add_claim(run, "Gene X is not required.")
        candidate = run.contradiction_candidates[0]
        self.assertEqual(candidate.status, "pending_review")
        kb.review_contradiction(run, candidate.candidate_id, "needs_context", "Different tissues.")
        assessment = kb.assess_claim(run, first.claim_id)
        self.assertEqual(assessment.unresolved_contradictions, 1)

    def test_event_keys_are_idempotent(self):
        self.store.log_event("run-id", "cycle_done", {"cycle": 1}, event_key="cycle:1:done")
        self.store.log_event("run-id", "cycle_done", {"cycle": 1}, event_key="cycle:1:done")
        self.assertEqual(len(self.store.list_events("run-id")), 1)

    def test_literature_ingestion_preserves_provenance_and_marks_candidates(self):
        from oracle.literature import LiteratureClient, LiteratureSearchReport
        run = ResearchRun("Literature ingestion")
        report = LiteratureSearchReport(query="test", providers=["europepmc"])
        report.records = [{
            "provider":"Europe PMC","provider_id":"123","doi":"10.1000/example","pmid":"12345",
            "title":"A study of cell signaling","authors":"A Author; B Author","journal":"Example Journal",
            "year":"2024","url":"https://doi.org/10.1000/example",
            "abstract":"Cell signaling controls developmental outcomes in several contexts. The authors measured gene expression across multiple independent samples.",
            "publication_type":"journal article","open_access":True,"license":"CC-BY","citation_count":5
        }]
        client = LiteratureClient()
        client.ingest(run, report)
        self.assertEqual(len(run.sources), 1)
        self.assertEqual(run.sources[0].doi, "10.1000/example")
        self.assertEqual(run.sources[0].pmid, "12345")
        self.assertEqual(run.evidence[0].locator, "Abstract")
        self.assertEqual(len(run.claims), 2)
        self.assertTrue(all(c.status == "unreviewed_candidate" for c in run.claims))
        self.assertTrue(all(x.stance == EvidenceStance.CONTEXTUAL and x.strength == 0
                            for x in run.evidence_claim_links))
        self.store.save_run(run)
        loaded = self.store.load_run(run.run_id)
        self.assertEqual(loaded.sources[0].provider, "Europe PMC")
        self.assertEqual(loaded.evidence[0].source_id, loaded.sources[0].source_id)

    def test_literature_search_deduplicates_doi_across_providers(self):
        from unittest.mock import patch
        from oracle.literature import LiteratureClient
        client = LiteratureClient()
        europe = {"resultList":{"result":[{
            "doi":"10.1000/same","pmid":"111","title":"Shared paper",
            "abstractText":"An abstract.","authorString":"A Author","pubYear":"2024"}]}}
        crossref = {"message":{"items":[{
            "DOI":"10.1000/same","title":["Shared paper"],
            "abstract":"<jats:p>An abstract.</jats:p>","author":[],
            "published":{"date-parts":[[2024]]}}]}}
        def fake_get(url):
            return europe if "europepmc" in url else crossref
        with patch.object(client, "_get_json", side_effect=fake_get):
            result = client.search("shared paper", limit=5)
        self.assertEqual(result.retrieved, 1)
        self.assertEqual(result.records[0]["doi"], "10.1000/same")
        self.assertTrue(result.records[0]["abstract"])

    def test_geo_dataset_records_are_persisted_as_dataset_evidence(self):
        from oracle.literature import LiteratureClient, LiteratureSearchReport
        run = ResearchRun("GEO dataset test")
        report = LiteratureSearchReport(query="heat stress", providers=["geo"])
        report.records = [{
            "provider":"NCBI GEO","provider_id":"123","doi":"","pmid":"",
            "title":"Heat stress in seedlings","authors":"","journal":"","year":"2025",
            "url":"https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE12345",
            "abstract":"Expression profiles from seedlings exposed to heat stress.",
            "publication_type":"gene expression dataset","open_access":False,"license":"",
            "citation_count":None,"dataset":True,"dataset_accession":"GSE12345",
            "organism":"Arabidopsis thaliana","sample_count":18,"platform":"GPL198",
            "dataset_type":"Expression profiling by array","pubmed_ids":[]
        }]
        client = LiteratureClient()
        client.ingest(run, report)
        self.assertEqual(run.sources[0].dataset_accession, "GSE12345")
        self.assertEqual(run.sources[0].organism, "Arabidopsis thaliana")
        self.assertEqual(run.evidence[0].kind, EvidenceKind.DATASET)
        self.assertEqual(run.evidence[0].locator, "GEO dataset summary")
        self.store.save_run(run)
        loaded = self.store.load_run(run.run_id)
        self.assertEqual(loaded.sources[0].dataset_accession, "GSE12345")
        self.assertEqual(loaded.evidence[0].kind, EvidenceKind.DATASET)

    def test_geo_search_uses_esearch_then_esummary(self):
        from unittest.mock import patch
        from oracle.literature import LiteratureClient
        client = LiteratureClient()
        search = {"esearchresult":{"idlist":["123"]}}
        summary = {"result":{"123":{"accession":"GSE123","title":"Example dataset",
            "summary":"Dataset summary.","taxon":"Arabidopsis thaliana",
            "n_samples":"12","gpl":"GPL1","gdsType":"Expression profiling"}}}
        with patch.object(client,"_get_json",side_effect=[search,summary]):
            records = client._search_geo("plant stress",5)
        self.assertEqual(records[0]["dataset_accession"],"GSE123")
        self.assertEqual(records[0]["sample_count"],"12")

    def test_literature_query_and_limit_validation(self):
        from oracle.literature import LiteratureClient
        client = LiteratureClient()
        with self.assertRaises(ValueError): client.search(" ")
        with self.assertRaises(ValueError): client.search("valid", limit=0)

    def test_gemini_extraction_requires_verbatim_quote_and_persists_provenance(self):
        from unittest.mock import patch
        from oracle.llm import GeminiClaimExtractor
        from oracle.models import SourceRecord
        run = ResearchRun("How does cell fate change?")
        source = SourceRecord(title="Example developmental study", source_id="src-example")
        run.sources.append(source)
        quote_text = "Cell signaling controls developmental outcomes in several contexts."
        evidence = Evidence(quote_text + " The authors measured gene expression across multiple independent samples.",
                            source.title, source_id=source.source_id, locator="Abstract")
        run.evidence.append(evidence)
        extractor = GeminiClaimExtractor(api_key="test-key")
        response = {"claims": [
            {"statement":"Cell signaling controls developmental outcomes in multiple contexts.",
             "evidence_quote":quote_text},
            {"statement":"A made-up mechanism explains all cell fate decisions in embryos.",
             "evidence_quote":"This quotation does not occur in the paper."},
        ]}
        with patch.object(extractor, "_generate_json", return_value=response):
            report = extractor.extract(run)
        self.assertEqual(report.evidence_examined, 1)
        self.assertEqual(report.candidates_created, 1)
        self.assertEqual(report.candidates_rejected, 1)
        claim = run.claims[0]
        self.assertEqual(claim.status, "unreviewed_candidate")
        self.assertEqual(claim.source_quote, quote_text)
        self.assertEqual(claim.extraction_model, "gemini-2.5-flash")
        self.assertEqual(run.evidence_claim_links[0].stance, EvidenceStance.CONTEXTUAL)
        self.assertEqual(run.evidence_claim_links[0].strength, 0.0)
        self.store.save_run(run)
        loaded = self.store.load_run(run.run_id)
        self.assertEqual(loaded.claims[0].source_quote, quote_text)
        self.assertEqual(loaded.claims[0].extraction_model, "gemini-2.5-flash")

    def test_gemini_extractor_requires_api_key(self):
        from unittest.mock import patch
        from oracle.llm import GeminiClaimExtractor
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaises(ValueError):
                GeminiClaimExtractor(api_key="")

    def test_cross_paper_comparisons_require_two_exact_quotes_and_persist(self):
        from unittest.mock import patch
        from oracle.comparison import CrossPaperComparator
        from oracle.models import SourceRecord
        run = ResearchRun("Do two papers agree about signaling and cell fate?")
        source_a = SourceRecord(title="Paper A", source_id="paper-a", doi="10.1000/a")
        source_b = SourceRecord(title="Paper B", source_id="paper-b", doi="10.1000/b")
        run.sources.extend([source_a, source_b])
        text_a = "In this study, pathway activation increased the fraction of cells adopting the neuronal fate."
        text_b = "Our results show that pathway activation increased neuronal cell fate under the tested conditions."
        ev_a = Evidence(text_a, source_a.title, source_id=source_a.source_id, locator="Abstract")
        ev_b = Evidence(text_b, source_b.title, source_id=source_b.source_id, locator="Abstract")
        run.evidence.extend([ev_a, ev_b])
        kb = KnowledgeBase()
        claim_a = kb.add_claim(run, "Pathway activation increases neuronal cell fate.")
        claim_b = kb.add_claim(run, "Pathway activation increases neuronal fate in tested conditions.")
        claim_a.status = claim_b.status = "unreviewed_candidate"
        kb.link_evidence(run, claim_a.claim_id, ev_a.evidence_id, EvidenceStance.CONTEXTUAL, 0.0)
        kb.link_evidence(run, claim_b.claim_id, ev_b.evidence_id, EvidenceStance.CONTEXTUAL, 0.0)
        comparator = CrossPaperComparator(api_key="test-key")
        response = {"claims": [
            {"pair_index": 0, "relation": "corroborates",
             "rationale": "Both abstracts report an increase under pathway activation.",
             "quote_a": text_a, "quote_b": text_b},
            {"pair_index": 0, "relation": "contrasts",
             "rationale": "Invalid duplicate pair.",
             "quote_a": "not in source", "quote_b": text_b},
        ]}
        with patch.object(comparator.extractor, "_generate_json", return_value=response):
            report = comparator.compare(run)
        self.assertEqual(report.pairs_submitted, 1)
        self.assertEqual(report.comparisons_created, 1)
        self.assertEqual(report.comparisons_rejected, 1)
        comparison = run.evidence_comparisons[0]
        self.assertEqual(comparison.relation, "corroborates")
        self.assertEqual(comparison.status, "pending_review")
        self.assertEqual(comparison.source_a_id, source_a.source_id)
        self.assertEqual(comparison.quote_b, text_b)
        self.store.save_run(run)
        loaded = self.store.load_run(run.run_id)
        self.assertEqual(len(loaded.evidence_comparisons), 1)
        self.assertEqual(loaded.evidence_comparisons[0].status, "pending_review")

    def test_repeated_no_progress_stops_without_duplicate_records(self):
        run = OracleOrchestrator(self.store, max_no_progress_cycles=2).run(
            "A deterministic question", max_cycles=5
        )
        self.assertEqual(run.status, RunStatus.STOPPED)
        self.assertEqual(run.current_cycle, 3)
        self.assertEqual(run.consecutive_no_progress_cycles, 2)
        self.assertEqual(len(run.evidence), 1)
        self.assertEqual(len(run.experiments), 1)
        self.assertIn("run_stopped", [event["event_type"] for event in self.store.list_events(run.run_id)])
        loaded = self.store.load_run(run.run_id)
        self.assertEqual(loaded.consecutive_no_progress_cycles, 2)

    def test_resume_interrupted_run_without_resetting_history(self):
        run = OracleOrchestrator(self.store).run("Resume this", max_cycles=1)
        run.status = RunStatus.PAUSED
        self.store.save_run(run)
        resumed = OracleOrchestrator(self.store).resume(run.run_id, additional_cycles=1)
        self.assertEqual(resumed.status, RunStatus.COMPLETED)
        self.assertEqual(resumed.current_cycle, 2)
        self.assertEqual(len(resumed.evidence), 1)
        self.assertEqual(resumed.run_id, run.run_id)



    def test_gemini_agents_keep_model_outputs_provisional(self):
        from oracle.agents import AgentContext
        from oracle.model_agents import (
            GeminiExperimentDesignerAgent, GeminiHypothesisAgent,
            GeminiResearcherAgent,
        )
        from oracle.models import EvidenceKind, ExperimentStatus

        class FakeProvider:
            model = "fake-gemini"

            def generate_json(self, prompt):
                if "AGENT: researcher" in prompt:
                    return {"inferences": [{
                        "statement": "Several interacting mechanisms may contribute to cell fate.",
                        "rationale": "A provisional synthesis that needs source verification.",
                    }]}
                if "AGENT: hypothesis_generator" in prompt:
                    return {"hypotheses": [
                        {"statement": "Model A explains the outcome through pathway A.",
                         "rationale": "Provisional mechanism A.",
                         "predictions": ["Blocking pathway A changes the measured outcome."]},
                        {"statement": "Model B explains the outcome through mechanical cues.",
                         "rationale": "Competing provisional mechanism B.",
                         "predictions": ["Changing mechanical cues changes the measured outcome."]},
                    ]}
                if "AGENT: experiment_designer" in prompt:
                    return {"question": "Which mechanism predicts the measured outcome?",
                            "protocol": ["Define conditions", "Measure the outcome", "Compare controls"],
                            "predictions": ["Model A predicts one outcome", "Model B predicts another"],
                            "limitations": "Requires domain expert review."}
                raise AssertionError("Unexpected agent prompt")

        context = AgentContext("How do cells choose a fate?", 1, "both")
        researcher = GeminiResearcherAgent(FakeProvider()).run(context)
        self.assertTrue(researcher.items)
        self.assertTrue(all(item.kind == EvidenceKind.INFERENCE for item in researcher.items))
        self.assertTrue(all("not an external" in item.source for item in researcher.items))

        hypotheses = GeminiHypothesisAgent(FakeProvider()).run(context)
        self.assertEqual(len(hypotheses.items), 2)
        context.hypotheses = hypotheses.items
        design = GeminiExperimentDesignerAgent(FakeProvider()).run(context)
        self.assertEqual(len(design.items), 1)
        self.assertEqual(design.items[0].status, ExperimentStatus.PROPOSED)
        self.assertIn("not performed or simulated", design.items[0].limitations)

    def test_gemini_agent_suite_requires_environment_key(self):
        from unittest.mock import patch
        from oracle.model_agents import GeminiAgentSuite
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaises(ValueError):
                GeminiAgentSuite()


    def test_full_research_cycle_can_ingest_literature_before_agents(self):
        from types import SimpleNamespace
        from unittest.mock import patch
        from oracle.models import Evidence, EvidenceKind, SourceRecord

        class FakeLiteratureClient:
            def __init__(self, mailto=""):
                self.mailto = mailto

            def search(self, query, limit, providers):
                return SimpleNamespace(
                    retrieved=1, ingested_sources=1, evidence_records=1,
                    providers=list(providers), warnings=[], records=[],
                )

            def ingest(self, run, report):
                source = SourceRecord(
                    title="A source-grounded paper", source_id="source-1",
                    url="https://example.org/paper", provider="Fake provider",
                )
                run.sources.append(source)
                run.evidence.append(Evidence(
                    "The abstract reports a measured association.",
                    source.title, kind=EvidenceKind.SOURCE, source_id=source.source_id,
                    locator="Abstract", method="Published abstract",
                ))
                report.ingested_sources = 1
                report.evidence_records = 1

        with patch("oracle.literature.LiteratureClient", FakeLiteratureClient):
            run = OracleOrchestrator(
                self.store, literature_enabled=True, literature_providers=("europepmc",)
            ).run("What mechanism explains the measured association?", max_cycles=1)

        self.assertEqual(len(run.sources), 1)
        self.assertEqual(len(run.evidence), 2)  # one retrieved source plus one labelled scaffold inference
        self.assertEqual(run.evidence[0].locator, "Abstract")
        self.assertIn("literature_ingested", [e["event_type"] for e in self.store.list_events(run.run_id)])


    def test_gemini_evidence_review_is_quote_grounded_and_requires_human_acceptance(self):
        from unittest.mock import patch
        from oracle.evidence_review import GeminiEvidenceReviewer
        from oracle.models import SourceRecord

        run = ResearchRun("Does pathway activation change cell fate?")
        source_a = SourceRecord(title="Paper A", source_id="paper-a")
        source_b = SourceRecord(title="Paper B", source_id="paper-b")
        run.sources.extend([source_a, source_b])
        own_text = "Pathway activation increased the neuronal cell fraction in this assay."
        other_text = "The measured neuronal fraction decreased after pathway activation in this tissue."
        own_evidence = Evidence(own_text, source_a.title, source_id=source_a.source_id, locator="Abstract")
        other_evidence = Evidence(other_text, source_b.title, source_id=source_b.source_id, locator="Abstract")
        run.evidence.extend([own_evidence, other_evidence])
        kb = KnowledgeBase()
        claim = kb.add_claim(run, "Pathway activation increases neuronal cell fraction.")
        claim.status = "unreviewed_candidate"
        kb.link_evidence(run, claim.claim_id, own_evidence.evidence_id, EvidenceStance.CONTEXTUAL, 0.0)

        reviewer = GeminiEvidenceReviewer(api_key="test-key")
        reviewer.provider.generate_json = lambda prompt: {"reviews": [
            {"pair_index": 0, "stance": "refutes",
             "rationale": "The other paper reports the opposite direction in its stated tissue.",
             "source_quote": other_text},
            {"pair_index": 0, "stance": "supports",
             "rationale": "Invalid duplicate pair and quote.",
             "source_quote": "not present"},
        ]}
        report = reviewer.review(run)
        self.assertEqual(report.pairs_submitted, 1)
        self.assertEqual(report.candidates_created, 1)
        self.assertEqual(report.candidates_rejected, 1)
        candidate = run.evidence_review_candidates[0]
        self.assertEqual(candidate.status, "pending_review")
        self.assertEqual(candidate.proposed_stance, EvidenceStance.REFUTES)
        self.assertEqual(len(run.evidence_claim_links), 1)  # model suggestion did not change evidence links

        kb.review_evidence_candidate(
            run, candidate.candidate_id, "accepted", "Human checked the source context.", strength=0.6
        )
        self.assertEqual(candidate.status, "accepted")
        self.assertEqual(len(run.evidence_claim_links), 2)
        self.assertEqual(run.evidence_claim_links[-1].stance, EvidenceStance.REFUTES)
        self.store.save_run(run)
        loaded = self.store.load_run(run.run_id)
        self.assertEqual(loaded.evidence_review_candidates[0].status, "accepted")
        self.assertEqual(loaded.evidence_review_candidates[0].proposed_stance, EvidenceStance.REFUTES)

    def test_evidence_review_rejects_inference_as_source_evidence(self):
        run = ResearchRun("Review integrity")
        kb = KnowledgeBase()
        claim = kb.add_claim(run, "A sufficiently long scientific candidate statement.")
        evidence = Evidence("A model inference passage.", "ORACLE", EvidenceKind.INFERENCE)
        run.evidence.append(evidence)
        with self.assertRaises(ValueError):
            kb.add_evidence_review_candidate(
                run, claim.claim_id, evidence.evidence_id, EvidenceStance.SUPPORTS,
                "A rationale.", "model inference", "test-model",
            )


    def test_knowledge_gap_score_is_transparent_and_improves_after_review(self):
        from oracle.models import SourceRecord
        from oracle.portfolio import KnowledgeGapAssessor, ResearchPortfolio

        run = ResearchRun("How does signaling influence cell fate?")
        source = SourceRecord(title="Paper on cell signaling", source_id="source-gap")
        run.sources.append(source)
        evidence = Evidence(
            "The paper reports a measured signaling association.", source.title,
            source_id=source.source_id, locator="Abstract",
        )
        run.evidence.append(evidence)
        claim = KnowledgeBase().add_claim(run, "Signaling is associated with cell fate.")
        claim.status = "unreviewed_candidate"
        KnowledgeBase().link_evidence(
            run, claim.claim_id, evidence.evidence_id, EvidenceStance.CONTEXTUAL, 0.0
        )
        run.hypotheses.extend([
            Hypothesis("Model A", "Reason A"),
            Hypothesis("Model B", "Reason B"),
        ])

        assessor = KnowledgeGapAssessor()
        before = assessor.assess(run)
        self.assertEqual(before.criteria["source_coverage_gap"], 0.8)
        self.assertGreater(before.score, 50)
        self.assertTrue(any("lack accepted support/refute" in gap for gap in before.gaps))

        KnowledgeBase().link_evidence(
            run, claim.claim_id, evidence.evidence_id, EvidenceStance.SUPPORTS, 0.7,
            "Human-reviewed source relationship.",
        )
        after = assessor.assess(run)
        self.assertLess(after.score, before.score)
        self.assertEqual(after.counts["reviewed_claims"], 1)

        self.store.save_run(run)
        portfolio = ResearchPortfolio(self.store)
        entries = portfolio.list_entries()
        self.assertEqual(entries[0]["run_id"], run.run_id)
        related = portfolio.related_runs("cell fate signaling pathways")
        self.assertEqual(related[0]["run_id"], run.run_id)
        self.assertGreater(related[0]["lexical_similarity"], 0)

    def test_portfolio_rejects_missing_run_gap_assessment(self):
        from oracle.portfolio import ResearchPortfolio
        with self.assertRaises(ValueError):
            ResearchPortfolio(self.store).assess("missing-run")


    def test_experiment_lifecycle_keeps_simulation_distinct_from_real_execution(self):
        from oracle.experiment_manager import ExperimentManager
        from oracle.models import Experiment, ExperimentStatus

        run = ResearchRun("Test experimental lifecycle")
        simulated = Experiment("Test simulation", ["Run a toy model"], ["Output A"])
        performed = Experiment("Test physical experiment", ["Collect samples"], ["Outcome B"])
        run.experiments.extend([simulated, performed])
        manager = ExperimentManager()

        manager.record_simulation(
            run, simulated.experiment_id, "Python toy simulator v1",
            "Synthetic output: A=0.7", "No biological measurements; simplified assumptions.",
        )
        self.assertEqual(simulated.status, ExperimentStatus.SIMULATED)
        self.assertEqual(simulated.execution_kind, "simulated")
        self.assertIn("not a real-world experiment", simulated.limitations)
        with self.assertRaises(ValueError):
            manager.record_performed(
                run, simulated.experiment_id, "wet lab", "Researcher", "Some result",
            )

        manager.record_performed(
            run, performed.experiment_id, "qPCR with three biological replicates",
            "Lab operator", "Recorded Ct values in lab notebook.",
        )
        self.assertEqual(performed.status, ExperimentStatus.PERFORMED)
        self.assertEqual(performed.execution_kind, "performed")
        self.assertTrue(performed.executed_at)

        manager.mark_evaluated(run, simulated.experiment_id, "Simulation checked against expected toy behavior.")
        manager.mark_evaluated(run, performed.experiment_id, "Observed results compared with preregistered predictions.")
        self.assertEqual(simulated.status, ExperimentStatus.EVALUATED)
        self.assertEqual(simulated.execution_kind, "simulated")
        self.assertEqual(performed.status, ExperimentStatus.EVALUATED)
        self.assertEqual(performed.execution_kind, "performed")
        self.store.save_run(run)
        loaded = self.store.load_run(run.run_id)
        self.assertEqual(loaded.experiments[0].execution_kind, "simulated")
        self.assertEqual(loaded.experiments[1].execution_kind, "performed")

    def test_experiment_lifecycle_requires_provenance(self):
        from oracle.experiment_manager import ExperimentManager
        from oracle.models import Experiment
        run = ResearchRun("Provenance test")
        experiment = Experiment("Real experiment", ["Protocol"], ["Prediction"])
        run.experiments.append(experiment)
        with self.assertRaises(ValueError):
            ExperimentManager().record_performed(
                run, experiment.experiment_id, "", "Operator", "Results",
            )

if __name__ == "__main__":
    unittest.main()
