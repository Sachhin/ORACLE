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
from .task_manager import TaskManager


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
                 full_text_enabled: bool = False,
                 geo_files_enabled: bool = False,
                 geo_download_enabled: bool = False,
                 geo_analysis_enabled: bool = False,
                 geo_max_file_bytes: int = 50_000_000,
                 citation_network_enabled: bool = False,
                 incoming_citation_network_enabled: bool = False,
                 max_tasks: int = 50,
                 max_task_attempts: int = 3,
                 gemini_model: str = "gemini-2.5-flash",
                 literature_client=None,
                 research_domain: str = "auto") -> None:
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
        self.full_text_enabled = full_text_enabled
        self.geo_analysis_enabled = geo_analysis_enabled
        self.geo_files_enabled = geo_files_enabled or geo_download_enabled or geo_analysis_enabled
        self.geo_download_enabled = geo_download_enabled or geo_analysis_enabled
        self.geo_max_file_bytes = geo_max_file_bytes
        self.citation_network_enabled = citation_network_enabled
        self.incoming_citation_network_enabled = incoming_citation_network_enabled
        self.task_manager = TaskManager(max_attempts=max_task_attempts, max_tasks=max_tasks)
        self.gemini_model = gemini_model
        self.research_domain = research_domain
        self.domain_profile: dict = {}
        self.domain_diagnostics: dict = {}
        # Injectable for deterministic tests; production creates the public-API client lazily.
        self._literature_client = literature_client
        # Every agent implements run(context) -> AgentResult. Deterministic
        # agents remain the default; an optional suite can replace selected agents.
        self.planner = agent_suite.planner if agent_suite else PlannerAgent()
        self.researcher = agent_suite.researcher if agent_suite else ResearcherAgent()
        self.explorer = agent_suite.explorer if agent_suite else ExplorerAgent()
        self.hypothesizer = agent_suite.hypothesizer if agent_suite else HypothesisAgent()
        self.skeptic = agent_suite.skeptic if agent_suite else SkepticAgent()
        self.auditor = agent_suite.auditor if agent_suite and hasattr(agent_suite, "auditor") else AuditorAgent()
        self.experiment_designer = (
            agent_suite.experiment_designer if agent_suite else ExperimentDesignerAgent()
        )
        self.novelty = agent_suite.novelty if agent_suite and hasattr(agent_suite, "novelty") else NoveltyAssessorAgent()
        self.connection_explorer = (
            agent_suite.connection_explorer if agent_suite and hasattr(agent_suite, "connection_explorer")
            else None
        )
        self.knowledge = KnowledgeBase()

    def _event(self, run: ResearchRun, kind: str, payload: dict,
               checkpoint: bool = True, event_key: str | None = None) -> None:
        self.store.log_event(run.run_id, kind, payload, event_key=event_key)
        if checkpoint:
            self.store.save_run(run)

    @staticmethod
    def _normalise(value: str) -> str:
        return " ".join(value.casefold().split())

    @staticmethod
    def _task_search_query(task) -> str:
        """Build a focused scholarly query from the task, not repeated planner boilerplate."""
        words = " ".join((task.name, task.description)).split()
        return " ".join(words[:32])[:350]

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
            if experiment.status.value == "simulated" and (
                experiment.execution_kind != "simulated" or not experiment.simulation_engine.strip()
                or not experiment.results.strip()
            ):
                warnings.append("A simulated experiment lacks simulation provenance or results.")
                break
            if experiment.status.value == "performed" and (
                experiment.execution_kind != "performed" or not experiment.execution_method.strip()
                or not experiment.operator.strip() or not experiment.results.strip()
            ):
                warnings.append("A performed experiment lacks execution provenance or results.")
                break
            if experiment.status.value == "evaluated" and (
                experiment.execution_kind not in {"simulated", "performed"}
                or not experiment.evaluation_note.strip()
            ):
                warnings.append("An evaluated experiment lacks its execution kind or evaluation note.")
                break
        for connection in run.cross_domain_connections:
            if (len(set(connection.source_ids)) < 2
                    or any(source_id not in source_ids for source_id in connection.source_ids)):
                warnings.append("Cross-domain connection has insufficient or invalid source provenance.")
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
        from .domain_router import profile_dict, resolve_domain
        profile, diagnostics = resolve_domain(question, self.research_domain)
        self.domain_profile = profile_dict(profile)
        self.domain_diagnostics = diagnostics
        run = ResearchRun(question=question, mode=mode, max_cycles=max_cycles,
                          status=RunStatus.RUNNING)
        run.findings.append(
            f"Domain routing: {profile.label} ({diagnostics.get('method')}; "
            f"confidence={diagnostics.get('confidence', 0.0)}). "
            "This selects research guidance only; specialist tools must still be explicitly executed."
        )
        self.store.save_run(run)
        self._event(run, "domain_routed", {
            "domain": profile.key, "label": profile.label,
            "diagnostics": diagnostics, "profile": self.domain_profile,
        }, event_key="domain_routed")
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
        from .domain_router import profile_dict, resolve_domain
        profile, diagnostics = resolve_domain(run.question, self.research_domain)
        self.domain_profile = profile_dict(profile)
        self.domain_diagnostics = diagnostics
        run.max_cycles = min(100, run.max_cycles + additional_cycles)
        run.status = RunStatus.RUNNING
        # An explicit resume is a user-authorised fresh attempt, not an endless retry.
        run.consecutive_no_progress_cycles = 0
        self._event(run, "domain_routed", {
            "domain": profile.key, "label": profile.label,
            "diagnostics": diagnostics, "profile": self.domain_profile,
        }, event_key=f"domain-routed-resume:{run.current_cycle}:{run.max_cycles}")
        self._event(run, "run_resumed", {"from_cycle": run.current_cycle,
                                         "new_cycle_limit": run.max_cycles}, event_key=f"resume:{run.current_cycle}:{run.max_cycles}")
        return self._execute(run)

    def _search_literature(self, query: str, limit: int):
        """Route research retrieval through the auditable resource registry."""
        from .resource_manager import ResourceManager
        from .literature import LiteratureClient
        client = self._literature_client or LiteratureClient(mailto=self.literature_mailto)
        self._literature_client = client
        return ResourceManager(client).search(
            query, limit=limit, resources=self.literature_providers,
        )

    def _prepare_literature(self, run: ResearchRun) -> None:
        """Optionally retrieve source-backed literature before the reasoning cycle."""
        if (not self.literature_enabled and not self.extract_literature_claims
                and not self.full_text_enabled and not self.geo_files_enabled
                and not self.geo_analysis_enabled and not self.citation_network_enabled
                and not self.incoming_citation_network_enabled):
            return
        if self.literature_enabled and not run.sources:
            report = self._search_literature(run.question, self.literature_limit)
            self._literature_client.ingest(run, report)
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
        if self.full_text_enabled:
            from .fulltext import OpenAccessFullTextClient
            full_text = OpenAccessFullTextClient().ingest(run)
            self._event(run, "open_access_full_text_ingested", full_text.__dict__)
        if self.geo_files_enabled:
            from .geo_data import GEOSupplementaryClient
            geo_client = GEOSupplementaryClient()
            discovery = geo_client.discover(run)
            download_report = (
                geo_client.download(run, max_file_bytes=self.geo_max_file_bytes)
                if self.geo_download_enabled else None
            )
            analysis_report = None
            if self.geo_analysis_enabled:
                from .geo_analysis import GEOExpressionAnalyzer
                analysis_report = GEOExpressionAnalyzer().analyze(run)
            self._event(run, "geo_supplementary_files_discovered", {
                "discovery": discovery.__dict__,
                "download": download_report.__dict__ if download_report else None,
                "analysis": analysis_report.__dict__ if analysis_report else None,
            })
        if self.citation_network_enabled:
            from .citation_network import CrossrefCitationClient
            citation_report = CrossrefCitationClient(mailto=self.literature_mailto).discover(run)
            self._event(run, "citation_network_discovered", citation_report.__dict__)
        if self.incoming_citation_network_enabled:
            from .incoming_citations import OpenAlexIncomingCitationClient
            incoming_report = OpenAlexIncomingCitationClient(mailto=self.literature_mailto).discover(run)
            self._event(run, "incoming_citation_network_discovered", incoming_report.__dict__)
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

    def _execute_research_tasks(self, run: ResearchRun, cycle: int,
                                max_per_cycle: int = 2) -> list[str]:
        """Execute a bounded number of pending research tasks against scholarly APIs.

        A task is completed only when retrieval yields source-backed abstract/dataset
        evidence. Metadata-only hits and provider failures leave an explicit blocked
        task; retrieved abstracts are not treated as reviewed scientific conclusions.
        """
        if not self.literature_enabled:
            return []
        candidates = sorted(
            (task for task in run.tasks
             if task.status in {"pending", "blocked"}
             and task.attempts < self.task_manager.max_attempts),
            key=lambda task: (task.priority, task.task_id),
        )[:max_per_cycle]
        events = []
        for task in candidates:
            try:
                if task.status == "blocked":
                    self.task_manager.retry(run, task.task_id)
                self.task_manager.start(run, task.task_id)
                self._event(run, "research_task_started", {
                    "task_id": task.task_id, "name": task.name,
                    "cycle": cycle, "attempt": task.attempts,
                }, False, f"task:{task.task_id}:attempt:{task.attempts}:started")
                # Search the task's concrete objective first. Repeating the entire
                # natural-language question plus generic planner prose often dilutes
                # scholarly API relevance (and returns metadata-only noise).
                query = self._task_search_query(task)
                report = self._search_literature(query, min(8, self.literature_limit))
                self._literature_client.ingest(run, report)

                # A focused task query can be too narrow for short/generic task
                # descriptions. Retry once with the original question as a fallback,
                # but only when the focused search produced no abstract/dataset evidence.
                focused_source_ids = {
                    source.source_id for source in run.sources
                    if any(
                        (item.get("doi") and source.doi and item["doi"].casefold() == source.doi.casefold())
                        or (item.get("pmid") and source.pmid and item["pmid"] == source.pmid)
                        or (item.get("url") and source.url and item["url"] == source.url)
                        or (item.get("title") and source.title.casefold() == item["title"].strip().casefold())
                        for item in report.records
                    )
                }
                focused_evidence = [
                    item for item in run.evidence
                    if item.source_id in focused_source_ids and item.kind.value != "inference"
                ]
                fallback_report = None
                if not focused_evidence and self._normalise(query) != self._normalise(run.question):
                    fallback_report = self._search_literature(run.question, min(8, self.literature_limit))
                    self._literature_client.ingest(run, fallback_report)
                all_records = list(report.records)
                if fallback_report is not None:
                    all_records.extend(fallback_report.records)
                titles = {str(item.get("title", "")).strip().casefold()
                          for item in all_records if item.get("title")}
                dois = {str(item.get("doi", "")).strip().casefold()
                        for item in all_records if item.get("doi")}
                pmids = {str(item.get("pmid", "")).strip().casefold()
                         for item in all_records if item.get("pmid")}
                urls = {str(item.get("url", "")).strip()
                        for item in all_records if item.get("url")}
                source_ids = {
                    source.source_id for source in run.sources
                    if (source.title.strip().casefold() in titles
                        or (source.doi and source.doi.casefold() in dois)
                        or (source.pmid and source.pmid.casefold() in pmids)
                        or (source.url and source.url in urls))
                }
                evidence_ids = [
                    item.evidence_id for item in run.evidence
                    if item.source_id in source_ids and item.kind.value != "inference"
                ]
                if evidence_ids:
                    self.task_manager.complete(
                        run, task.task_id, evidence_ids,
                        f"Retrieved {len(evidence_ids)} source-backed abstract/dataset evidence "
                        "record(s). Relevance, methods, and study quality remain unreviewed.",
                    )
                    outcome = "completed"
                else:
                    reason = (
                        "Search returned no abstract-backed source evidence; metadata-only "
                        "records are insufficient for task completion."
                    )
                    self.task_manager.block(run, task.task_id, reason)
                    outcome = "blocked"
                self._event(run, "research_task_finished", {
                    "task_id": task.task_id, "status": task.status,
                    "evidence_ids": task.evidence_ids,
                    "blocked_reason": task.blocked_reason,
                    "focused_query": query,
                    "fallback_used": fallback_report is not None,
                    "records_retrieved": report.retrieved + (fallback_report.retrieved if fallback_report else 0),
                    "warnings": report.warnings + (fallback_report.warnings if fallback_report else []),
                }, False, f"task:{task.task_id}:attempt:{task.attempts}:finished")
                events.append(f"Task {task.name}: {outcome} ({len(task.evidence_ids)} linked evidence record(s)).")
            except Exception as exc:
                if task.status != "completed":
                    try:
                        self.task_manager.block(run, task.task_id, f"Retrieval attempt failed: {exc}")
                    except ValueError:
                        pass
                self._event(run, "research_task_failed", {
                    "task_id": task.task_id, "status": task.status,
                    "error": str(exc)[:1200],
                }, False, f"task:{task.task_id}:attempt:{task.attempts}:failed")
                events.append(f"Task {task.name}: blocked ({str(exc)[:300]}).")
        if events:
            self._add_unique_strings(run.findings, events)
        return events

    def _execute(self, run: ResearchRun) -> ResearchRun:
        checkpoint = deepcopy(run)
        final_action = "conclude"
        try:
            self._prepare_literature(run)
            if not run.tasks:
                plan = self.planner.run(AgentContext(
                    run.question, 0, run.mode.value, domain_profile=self.domain_profile,
                ))
                self.task_manager.validate_plan(plan.items)
                run.tasks.extend(plan.items)
                self._event(run, "plan_created", {"task_count": len(run.tasks)})

            for cycle in range(run.current_cycle + 1, run.max_cycles + 1):
                checkpoint = deepcopy(run)
                before = (len(run.evidence), len(run.hypotheses), len(run.experiments),
                          len(run.sources), len(run.claims), len(run.findings),
                          len(run.evidence_comparisons), len(run.cross_domain_connections),
                          tuple((task.task_id, task.status) for task in run.tasks))
                self._execute_research_tasks(run, cycle)
                context = AgentContext(
                    run.question, cycle, run.mode.value,
                    run.evidence, run.hypotheses, run.findings, run.tasks,
                    self.domain_profile,
                )

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

                # Rebuild the review context after research and hypothesis generation.
                # Previously these agents received the pre-cycle snapshot, so the skeptic,
                # auditor, experiment designer, and novelty assessor could miss the very
                # inferences/hypotheses produced earlier in this cycle.
                review_context = AgentContext(
                    run.question, cycle, run.mode.value,
                    run.evidence, run.hypotheses, run.findings, run.tasks,
                    self.domain_profile,
                )
                skeptic = self.skeptic.run(review_context)
                audit = self.auditor.run(review_context)
                design = self.experiment_designer.run(review_context)
                self._add_unique_experiments(run, design.items)
                novelty = self.novelty.run(review_context)
                connection_result = None
                if self.connection_explorer is not None:
                    connection_context = AgentContext(
                        run.question, cycle, run.mode.value,
                        run.evidence, run.hypotheses, run.findings, run.tasks,
                    )
                    connection_result = self.connection_explorer.run(connection_context)
                    known_connections = {
                        (self._normalise(item.statement), tuple(sorted(item.source_ids)))
                        for item in run.cross_domain_connections
                    }
                    for item in connection_result.items:
                        key = (self._normalise(item.statement), tuple(sorted(item.source_ids)))
                        if key not in known_connections:
                            run.cross_domain_connections.append(item)
                            known_connections.add(key)
                    if connection_result.items:
                        self._event(run, "cross_domain_connections_proposed", {
                            "count": len(connection_result.items),
                            "connection_ids": [item.connection_id for item in connection_result.items],
                        }, False, f"cycle:{cycle}:cross-domain-connections")
                warnings = skeptic.warnings + audit.warnings + novelty.warnings
                if connection_result:
                    warnings.extend(connection_result.warnings)
                self._add_unique_strings(
                    run.findings,
                    ["Skeptic review: " + warning for warning in skeptic.warnings]
                    + ["Novelty assessment: " + novelty.summary],
                )

                after = (len(run.evidence), len(run.hypotheses), len(run.experiments),
                         len(run.sources), len(run.claims), len(run.findings),
                         len(run.evidence_comparisons), len(run.cross_domain_connections),
                         tuple((task.task_id, task.status) for task in run.tasks))
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
                if decision.action == "replan":
                    # Replanning must see the completed cycle's latest evidence,
                    # hypotheses, findings, and task outcomes—not the stale pre-cycle
                    # snapshot that was used to start the agents.
                    replan_context = AgentContext(
                        run.question, cycle, run.mode.value,
                        run.evidence, run.hypotheses, run.findings, run.tasks,
                    )
                    revised = self.planner.run(replan_context)
                    self.task_manager.validate_plan(revised.items)
                    known_tasks = {
                        (self._normalise(task.name), self._normalise(task.description))
                        for task in run.tasks
                    }
                    added_tasks = []
                    for task in revised.items:
                        key = (self._normalise(task.name), self._normalise(task.description))
                        if key in known_tasks:
                            continue
                        if len(run.tasks) >= self.task_manager.max_tasks:
                            break
                        run.tasks.append(task)
                        known_tasks.add(key)
                        added_tasks.append(task.task_id)
                    self._event(run, "plan_revised", {
                        "cycle": cycle, "new_task_ids": added_tasks,
                        "task_count": len(run.tasks),
                        "reason": "No unique research information was added in the preceding cycle.",
                    }, False, f"cycle:{cycle}:replan")
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
