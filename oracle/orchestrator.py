"""Offline end-to-end research-cycle orchestrator."""
from __future__ import annotations

from .agents import (
    AgentContext, AuditorAgent, ExperimentDesignerAgent, ExplorerAgent,
    HypothesisAgent, NoveltyAssessorAgent, PlannerAgent, ResearcherAgent,
    SkepticAgent,
)
from .decision import choose_next_action
from .models import ResearchMode, ResearchRun, RunStatus
from .storage import ResearchStore


class OracleOrchestrator:
    def __init__(self, store: ResearchStore | None = None) -> None:
        self.store = store or ResearchStore()
        self.planner = PlannerAgent()
        self.researcher = ResearcherAgent()
        self.explorer = ExplorerAgent()
        self.hypothesizer = HypothesisAgent()
        self.skeptic = SkepticAgent()
        self.auditor = AuditorAgent()
        self.experiment_designer = ExperimentDesignerAgent()
        self.novelty = NoveltyAssessorAgent()

    def _event(self, run: ResearchRun, kind: str, payload: dict) -> None:
        self.store.log_event(run.run_id, kind, payload)
        self.store.save_run(run)

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
        self._event(run, "run_started", {"mode": mode.value, "max_cycles": max_cycles})

        try:
            plan = self.planner.run(AgentContext(question, 0, mode.value))
            run.tasks.extend(plan.items)
            self._event(run, "plan_created", {"task_count": len(run.tasks)})

            for cycle in range(1, max_cycles + 1):
                run.current_cycle = cycle
                context = AgentContext(question, cycle, mode.value, run.evidence,
                                       run.hypotheses, run.findings)
                research = self.researcher.run(context)
                run.evidence.extend(research.items)
                self._event(run, "research_completed", {"summary": research.summary})

                if mode in (ResearchMode.AUTONOMOUS_DISCOVERY, ResearchMode.BOTH):
                    discovery = self.explorer.run(context)
                    run.findings.extend(discovery.items)
                    self._event(run, "discovery_completed", {"directions": discovery.items})

                if not run.hypotheses:
                    hypotheses = self.hypothesizer.run(context)
                    run.hypotheses.extend(hypotheses.items)
                    self._event(run, "hypotheses_created", {"count": len(hypotheses.items)})

                skeptic = self.skeptic.run(context)
                audit = self.auditor.run(context)
                design = self.experiment_designer.run(context)
                if design.items:
                    run.experiments.extend(design.items)
                novelty = self.novelty.run(context)

                warnings = skeptic.warnings + audit.warnings + novelty.warnings
                run.findings.extend([
                    "Skeptic review: " + warning for warning in skeptic.warnings
                ])
                run.findings.append("Novelty assessment: " + novelty.summary)
                decision = choose_next_action(cycle, max_cycles, progress=True)
                run.decisions.append(f"{decision.action}: {decision.reason}")
                self._event(run, "cycle_decided", {
                    "cycle": cycle, "action": decision.action,
                    "reason": decision.reason, "warnings": warnings,
                })
                if decision.action == "conclude":
                    break

            run.status = RunStatus.COMPLETED
            run.findings.append(
                "Offline baseline limitation: no external sources, real AI model, or physical experiment was used."
            )
            self._event(run, "run_completed", {"cycles": run.current_cycle})
        except Exception as exc:
            run.status = RunStatus.FAILED
            self._event(run, "run_failed", {"error": str(exc)})
            raise
        finally:
            self.store.save_run(run)
        return run
