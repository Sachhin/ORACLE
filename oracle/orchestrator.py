"""Resumable research-cycle orchestrator with measured progress and safe stopping."""
from __future__ import annotations

from copy import deepcopy

from .agents import (
    AgentContext, AuditorAgent, ExperimentDesignerAgent, ExplorerAgent,
    HypothesisAgent, NoveltyAssessorAgent, PlannerAgent, ResearcherAgent,
    SkepticAgent,
)
from .decision import choose_next_action
from .knowledge import KnowledgeBase
from .models import EvidenceStance, ResearchMode, ResearchRun, RunStatus
from .storage import ResearchStore


class OracleOrchestrator:
    def __init__(self, store: ResearchStore | None = None,
                 max_no_progress_cycles: int = 2,
                 agent_suite=None,
                 literature_enabled: bool = False,
                 literature_providers: tuple[str, ...] = ("europepmc", "crossref"),
                 literature_limit: int = 10,
                 literature_mailto: str = "",
                 extract_literature_claims: bool = False,
                 compare_literature_papers: bool = False,
                 review_literature_evidence: bool = False,
                 gemini_model: str = "gemini-2.5-flash") -> None:
        if not 1 <= max_no_progress_cycles <= 10:
            raise ValueError("max_no_progress_cycles must be between 1 and 10.")
        if not 1 <= literature_limit <= 50:
            raise ValueError("literature_limit must be between 1 and 50.")
        if compare_literature_papers and not extract_literature_claims:
            raise ValueError("Cross-paper comparison requires Gemini claim extraction.")
        self.store = store or ResearchStore()
        self.max_no_progress_cycles = max_no_progress_cycles
        self.literature_enabled = literature_enabled
        self.literature_providers = literature_providers
        self.literature_limit = literature_limit
        self.literature_mailto = literature_mailto
        self.extract_literature_claims = extract_literature_claims
        self.compare_literature_papers = compare_literature_papers
        self.review_literature_evidence = review_literature_evidence
        self.gemini_model = gemini_model
        # Every agent implements run(context) -> AgentResult. Deterministic
        # agents remain the default; an optional suite can replace selected agents.
        self.planner = agent_suite.planner if agent_suite else PlannerAgent()
        self.researcher = agent_suite.researcher if agent_suite else ResearcherAgent()
        self.explorer = agent_suite.explorer if agent_suite else ExplorerAgent()
        self.hypothesizer = agent_suite.hypothesizer if agent_suite else HypothesisAgent()
        self.skeptic = agent_suite.skeptic if agent_suite else SkepticAgent()
        self.auditor = AuditorAgent()
        self.experiment_designer = (
            agent_suite.experiment_designer if agent_suite else ExperimentDesignerAgent()
        )
        self.novelty = NoveltyAssessorAgent()
        self.knowledge = KnowledgeBase()

    def _event(self, run: ResearchRun, kind: str, payload: dict,
               checkpoint: bool = True, event_key: str | None = None) -> None:
        self.store.log_event(run.run_id, kind, payload, event_key=event_key)
        if checkpoint:
            self.store.save_run(run)

    @staticmethod
    def _normalise(value: str) -> str:
        return " ".join(value.casefold().split())

    def _add_unique_evidence(self, run: ResearchRun, evidence_items: list) -> int:
        added = 0
        known = {
            (item.kind.value, item.source_id, self._normalise(item.source),
             self._normalise(item.locator), self._normalise(item.claim))
            for item in run.evidence
        }
        for item in evidence_items:
            key = (item.kind.value, item.source_id, self._normalise(item.source),
                   self._normalise(item.locator), self._normalise(item.claim))
            if key in known:
                continue
            run.evidence.append(item)
            known.add(key)
            added += 1
        return added

    def _add_unique_strings(self, target: list[str], values: list[str]) -> int:
        known = {self._normalise(value) for value in target}
        added = 0
        for value in values:
            key = self._normalise(value)
            if key and key not in known:
                target.append(value)
                known.add(key)
                added += 1
        return added

    def _add_unique_experiments(self, run: ResearchRun, items: list) -> int:
        known = {
            (self._normalise(item.question),
             tuple(self._normalise(x) for x in item.protocol),
             tuple(self._normalise(x) for x in item.predictions))
            for item in run.experiments
        }
        added = 0
        for item in items:
            key = (self._normalise(item.question),
                   tuple(self._normalise(x) for x in item.protocol),
                   tuple(self._normalise(x) for x in item.predictions))
            if key not in known:
                run.experiments.append(item)
                known.add(key)
                added += 1
        return added

    def _critical_integrity_warnings(self, run: ResearchRun) -> list[str]:
        """Check structural invariants; never infer scientific truth here."""
        warnings: list[str] = []
        claim_ids = {claim.claim_id for claim in run.claims}
        evidence_ids = {item.evidence_id for item in run.evidence}
        source_ids = {source.source_id for source in run.sources}
        for link in run.evidence_claim_links:
            if link.claim_id not in claim_ids or link.evidence_id not in evidence_ids:
                warnings.append("Evidence graph contains a dangling claim/evidence link.")
                break
            if not 0.0 <= link.strength <= 1.0:
                warnings.append("Evidence link strength is outside the permitted 0..1 range.")
                break
        for item in run.evidence:
            if item.source_id and item.source_id not in source_ids:
                warnings.append("Evidence references a source absent from the run's provenance store.")
                break
        for experiment in run.experiments:
            if experiment.status.value == "performed" and not experiment.results.strip():
                warnings.append("An experiment is marked performed without recorded results.")
                break
        for candidate in run.evidence_review_candidates:
            evidence = next((item for item in run.evidence if item.evidence_id == candidate.evidence_id), None)
            claim = next((item for item in run.claims if item.claim_id == candidate.claim_id), None)
            if (evidence is None or claim is None or not candidate.source_quote
                    or candidate.source_quote not in evidence.claim):
                warnings.append("Evidence review candidate has invalid claim/evidence provenance.")
                break
        return warnings

    def run(self, question: str, mode: ResearchMode = ResearchMode.BOTH,
            max_cycles: int = 3) -> ResearchRun:
        question = question.strip()
        if not question:
            raise ValueError("Research question cannot be empty.")
        if not 1 <= max_cycles <= 20:
            raise ValueError("max_cycles must be between 1 and 20.")
        run = ResearchRun(question=question, mode=mode, max_cycles=max_cycles,
                          status=RunStatus.RUNNING)
        self.store.save_run(run)
        self._event(run, "run_started", {"mode": mode.value, "max_cycles": max_cycles}, event_key="run_started")
        return self._execute(run)

    def resume(self, run_id: str, additional_cycles: int = 1) -> ResearchRun:
        if not 1 <= additional_cycles <= 20:
            raise ValueError("additional_cycles must be between 1 and 20.")
        run = self.store.load_run(run_id)
        if run is None:
            raise ValueError(f"Research run not found: {run_id}")
        if run.status not in (RunStatus.RUNNING, RunStatus.PAUSED, RunStatus.FAILED, RunStatus.STOPPED):
            raise ValueError(f"Run cannot be resumed from status: {run.status.value}")
        run.max_cycles = min(100, run.max_cycles + additional_cycles)
        run.status = RunStatus.RUNNING
        # An explicit resume is a user-authorised fresh attempt, not an endless retry.
        run.consecutive_no_progress_cycles = 0
        self._event(run, "run_resumed", {"from_cycle": run.current_cycle,
                                         "new_cycle_limit": run.max_cycles}, event_key=f"resume:{run.current_cycle}:{run.max_cycles}")
        return self._execute(run)

    def _prepare_literature(self, run: ResearchRun) -> None:
        """Optionally retrieve source-backed literature before the reasoning cycle."""
        if not self.literature_enabled and not self.extract_literature_claims:
            return
        if self.literature_enabled and not run.sources:
            from .literature import LiteratureClient
            client = LiteratureClient(mailto=self.literature_mailto)
            report = client.search(
                run.question, limit=self.literature_limit,
                providers=self.literature_providers,
            )
            client.ingest(run, report)
            run.findings.append(
                f"Literature retrieval: {report.retrieved} records retrieved; "
                f"{report.ingested_sources} sources and {report.evidence_records} evidence records ingested."
            )
            run.findings.extend("Literature warning: " + item for item in report.warnings)
            self._event(run, "literature_ingested", {
                "retrieved": report.retrieved,
                "sources": report.ingested_sources,
                "evidence": report.evidence_records,
                "providers": report.providers,
                "warnings": report.warnings,
            })
        if self.extract_literature_claims:
            from .llm import GeminiClaimExtractor
            extractor = GeminiClaimExtractor(model=self.gemini_model)
            extraction = extractor.extract(run)
            self._event(run, "literature_claims_extracted", extraction.__dict__)
        if self.compare_literature_papers:
            from .comparison import CrossPaperComparator
            comparison = CrossPaperComparator(model=self.gemini_model).compare(run)
            self._event(run, "literature_papers_compared", comparison.__dict__)
        if self.review_literature_evidence:
            from .evidence_review import GeminiEvidenceReviewer
            review = GeminiEvidenceReviewer(model=self.gemini_model).review(run)
            self._event(run, "literature_evidence_reviewed", review.__dict__)

    def _execute(self, run: ResearchRun) -> ResearchRun:
        checkpoint = deepcopy(run)
        final_action = "conclude"
        try:
            self._prepare_literature(run)
            if not run.tasks:
                plan = self.planner.run(AgentContext(run.question, 0, run.mode.value))
                run.tasks.extend(plan.items)
                self._event(run, "plan_created", {"task_count": len(run.tasks)})

            for cycle in range(run.current_cycle + 1, run.max_cycles + 1):
                checkpoint = deepcopy(run)
                before = (len(run.evidence), len(run.hypotheses), len(run.experiments),
                          len(run.sources), len(run.claims), len(run.findings),
                          len(run.evidence_comparisons))
                context = AgentContext(run.question, cycle, run.mode.value,
                                       run.evidence, run.hypotheses, run.findings)

                research = self.researcher.run(context)
                self._add_unique_evidence(run, research.items)
                for evidence in run.evidence:
                    if evidence in research.items:
                        claim = self.knowledge.add_claim(run, evidence.claim, "inference")
                        if not any(link.claim_id == claim.claim_id and link.evidence_id == evidence.evidence_id
                                   for link in run.evidence_claim_links):
                            self.knowledge.link_evidence(
                                run, claim.claim_id, evidence.evidence_id,
                                EvidenceStance.CONTEXTUAL, 0.0,
                                "Generated by the deterministic offline scaffold; not external evidence.",
                            )
                self._event(run, "research_completed", {"summary": research.summary}, False,
                            f"cycle:{cycle}:research")

                if run.mode in (ResearchMode.AUTONOMOUS_DISCOVERY, ResearchMode.BOTH):
                    discovery = self.explorer.run(context)
                    self._add_unique_strings(run.findings, discovery.items)
                    self._event(run, "discovery_completed", {"directions": discovery.items}, False,
                                f"cycle:{cycle}:discovery")

                if not run.hypotheses:
                    hypotheses = self.hypothesizer.run(context)
                    for hypothesis in hypotheses.items:
                        self.knowledge.add_hypothesis(run, hypothesis)
                    self._event(run, "hypotheses_created", {"count": len(hypotheses.items)}, False,
                                f"cycle:{cycle}:hypotheses")

                skeptic = self.skeptic.run(context)
                audit = self.auditor.run(context)
                design = self.experiment_designer.run(context)
                self._add_unique_experiments(run, design.items)
                novelty = self.novelty.run(context)
                warnings = skeptic.warnings + audit.warnings + novelty.warnings
                self._add_unique_strings(
                    run.findings,
                    ["Skeptic review: " + warning for warning in skeptic.warnings]
                    + ["Novelty assessment: " + novelty.summary],
                )

                after = (len(run.evidence), len(run.hypotheses), len(run.experiments),
                         len(run.sources), len(run.claims), len(run.findings),
                         len(run.evidence_comparisons))
                progress = after != before
                if progress:
                    run.consecutive_no_progress_cycles = 0
                else:
                    run.consecutive_no_progress_cycles += 1

                critical = self._critical_integrity_warnings(run)
                decision = choose_next_action(
                    cycle, run.max_cycles, progress=progress,
                    critical_warnings=len(critical),
                    consecutive_no_progress=max(0, run.consecutive_no_progress_cycles - 1),
                    max_no_progress=self.max_no_progress_cycles,
                )
                final_action = decision.action
                run.decisions.append(f"{decision.action}: {decision.reason}")
                run.current_cycle = cycle
                self._event(run, "cycle_decided", {
                    "cycle": cycle, "action": decision.action,
                    "reason": decision.reason, "progress": progress,
                    "consecutive_no_progress_cycles": run.consecutive_no_progress_cycles,
                    "warnings": warnings, "critical_integrity_warnings": critical,
                }, event_key=f"cycle:{cycle}:decision")
                if decision.action in {"conclude", "stop"}:
                    break

            if final_action == "stop":
                run.status = RunStatus.STOPPED
                run.findings.append("Run stopped safely. Existing findings are retained; no unsupported conclusion was made.")
                self._event(run, "run_stopped", {
                    "cycles": run.current_cycle,
                    "no_progress_cycles": run.consecutive_no_progress_cycles,
                }, event_key=f"run_stopped:{run.current_cycle}")
            else:
                run.status = RunStatus.COMPLETED
                run.findings.append(
                    "Offline baseline limitation: no external sources, live AI reasoning, or physical experiment was used by this cycle."
                )
                self._event(run, "run_completed", {"cycles": run.current_cycle}, event_key="run_completed")
        except Exception as exc:
            run = checkpoint
            run.status = RunStatus.FAILED
            self.store.log_event(run.run_id, "run_failed", {"error": str(exc)})
            self.store.save_run(run)
            raise
        return run
