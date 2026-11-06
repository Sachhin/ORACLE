"""SQLite persistence for runs, normalized knowledge records, and idempotent events."""
from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from .models import (
    Claim, ClaimRevision, ContradictionCandidate, CrossDomainConnection, Evidence, EvidenceClaimLink, EvidenceComparison,
    EvidenceReviewCandidate, DatasetFileRecord, DatasetAnalysisRecord, DifferentialExpressionAnalysisRecord, CitationLink,
    EvidenceKind, EvidenceStance, Experiment, ExperimentStatus, Hypothesis,
    HypothesisGroup, HypothesisStatus, ResearchMode, ResearchRun, ResearchTask,
    RunStatus, SourceRecord, UncertaintyAssessment, utc_now,
)


class ResearchStore:
    def __init__(self, path: str | Path = "data/oracle.sqlite3") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.path, timeout=30)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        return db

    @contextmanager
    def _session(self):
        db = self._connect()
        try:
            with db:
                yield db
        finally:
            db.close()

    def _initialize(self) -> None:
        with self._session() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS runs (
                    run_id TEXT PRIMARY KEY, status TEXT NOT NULL,
                    question TEXT NOT NULL, payload TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS events (
                    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL, event_type TEXT NOT NULL,
                    payload TEXT NOT NULL, created_at TEXT NOT NULL,
                    event_key TEXT
                );
                CREATE TABLE IF NOT EXISTS sources (
                    source_id TEXT PRIMARY KEY, run_id TEXT NOT NULL, payload TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS claims (
                    claim_id TEXT PRIMARY KEY, run_id TEXT NOT NULL,
                    statement TEXT NOT NULL, revision INTEGER NOT NULL, payload TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS claim_revisions (
                    revision_id TEXT PRIMARY KEY, run_id TEXT NOT NULL,
                    claim_id TEXT NOT NULL, revision INTEGER NOT NULL, payload TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS evidence (
                    evidence_id TEXT PRIMARY KEY, run_id TEXT NOT NULL,
                    source_id TEXT NOT NULL, dependence_group TEXT NOT NULL, payload TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS evidence_claim_links (
                    link_id TEXT PRIMARY KEY, run_id TEXT NOT NULL,
                    claim_id TEXT NOT NULL, evidence_id TEXT NOT NULL, payload TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS contradiction_candidates (
                    candidate_id TEXT PRIMARY KEY, run_id TEXT NOT NULL,
                    claim_a_id TEXT NOT NULL, claim_b_id TEXT NOT NULL, status TEXT NOT NULL,
                    payload TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS differential_expression_analyses (
                    analysis_id TEXT PRIMARY KEY, run_id TEXT NOT NULL,
                    dataset_accession TEXT NOT NULL, matrix_sha256 TEXT NOT NULL,
                    review_status TEXT NOT NULL, payload TEXT NOT NULL
                );
            """)
            # Upgrade databases created before event idempotency was introduced.
            columns = {row["name"] for row in db.execute("PRAGMA table_info(events)")}
            if "event_key" not in columns:
                db.execute("ALTER TABLE events ADD COLUMN event_key TEXT")
            db.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_events_idempotency ON events(run_id,event_key) WHERE event_key IS NOT NULL")

    def _sync_graph(self, db: sqlite3.Connection, run: ResearchRun) -> None:
        rows = [
            ("sources", "source_id", [x.source_id for x in run.sources],
             [(x.source_id, run.run_id, json.dumps(x.__dict__, ensure_ascii=False)) for x in run.sources]),
            ("claims", "claim_id", [x.claim_id for x in run.claims],
             [(x.claim_id, run.run_id, x.statement, x.revision, json.dumps(x.__dict__, ensure_ascii=False)) for x in run.claims]),
            ("claim_revisions", "revision_id", [x.revision_id for x in run.claim_revisions],
             [(x.revision_id, run.run_id, x.claim_id, x.revision, json.dumps(x.__dict__, ensure_ascii=False)) for x in run.claim_revisions]),
            ("evidence", "evidence_id", [x.evidence_id for x in run.evidence],
             [(x.evidence_id, run.run_id, x.source_id, x.dependence_group, json.dumps({**x.__dict__, "kind": x.kind.value}, ensure_ascii=False)) for x in run.evidence]),
            ("evidence_claim_links", "link_id", [x.link_id for x in run.evidence_claim_links],
             [(x.link_id, run.run_id, x.claim_id, x.evidence_id, json.dumps({**x.__dict__, "stance": x.stance.value}, ensure_ascii=False)) for x in run.evidence_claim_links]),
            ("contradiction_candidates", "candidate_id", [x.candidate_id for x in run.contradiction_candidates],
             [(x.candidate_id, run.run_id, x.claim_a_id, x.claim_b_id, x.status, json.dumps(x.__dict__, ensure_ascii=False)) for x in run.contradiction_candidates]),
        ]
        for table, key, ids, values in rows:
            if table == "sources":
                sql = "INSERT INTO sources VALUES(?,?,?) ON CONFLICT(source_id) DO UPDATE SET payload=excluded.payload"
            elif table == "claims":
                sql = "INSERT INTO claims VALUES(?,?,?,?,?) ON CONFLICT(claim_id) DO UPDATE SET statement=excluded.statement,revision=excluded.revision,payload=excluded.payload"
            elif table == "claim_revisions":
                sql = "INSERT INTO claim_revisions VALUES(?,?,?,?,?) ON CONFLICT(revision_id) DO UPDATE SET payload=excluded.payload"
            elif table == "evidence":
                sql = "INSERT INTO evidence VALUES(?,?,?,?,?) ON CONFLICT(evidence_id) DO UPDATE SET source_id=excluded.source_id,dependence_group=excluded.dependence_group,payload=excluded.payload"
            elif table == "evidence_claim_links":
                sql = "INSERT INTO evidence_claim_links VALUES(?,?,?,?,?) ON CONFLICT(link_id) DO UPDATE SET payload=excluded.payload"
            else:
                sql = "INSERT INTO contradiction_candidates VALUES(?,?,?,?,?,?) ON CONFLICT(candidate_id) DO UPDATE SET status=excluded.status,payload=excluded.payload"
            if values:
                db.executemany(sql, values)
        if run.differential_expression_analyses:
            db.executemany(
                """INSERT INTO differential_expression_analyses
                   (analysis_id,run_id,dataset_accession,matrix_sha256,review_status,payload)
                   VALUES(?,?,?,?,?,?)
                   ON CONFLICT(analysis_id) DO UPDATE SET
                     dataset_accession=excluded.dataset_accession,
                     matrix_sha256=excluded.matrix_sha256,
                     review_status=excluded.review_status,payload=excluded.payload""",
                [(x.analysis_id, run.run_id, x.dataset_accession, x.matrix_sha256,
                  x.review_status, json.dumps(x.__dict__, ensure_ascii=False))
                 for x in run.differential_expression_analyses],
            )

    def save_run(self, run: ResearchRun) -> None:
        run.touch()
        payload = json.dumps(run.to_dict(), ensure_ascii=False)
        with self._connect() as db:
            db.execute("""
                INSERT INTO runs(run_id,status,question,payload,updated_at)
                VALUES(?,?,?,?,?)
                ON CONFLICT(run_id) DO UPDATE SET
                  status=excluded.status, payload=excluded.payload,
                  updated_at=excluded.updated_at
            """, (run.run_id, run.status.value, run.question, payload, run.updated_at))
            self._sync_graph(db, run)

    def load_payload(self, run_id: str) -> dict[str, Any] | None:
        with self._connect() as db:
            row = db.execute("SELECT payload FROM runs WHERE run_id=?", (run_id,)).fetchone()
        return json.loads(row["payload"]) if row else None

    def load_run(self, run_id: str) -> ResearchRun | None:
        data = self.load_payload(run_id)
        if data is None:
            return None
        def enum_value(enum_type, value):
            return enum_type(value) if value is not None else None
        run = ResearchRun(
            question=data["question"], mode=ResearchMode(data.get("mode", "both")),
            max_cycles=data.get("max_cycles", 3), run_id=data["run_id"],
            status=RunStatus(data.get("status", "created")),
            current_cycle=data.get("current_cycle", 0),
            consecutive_no_progress_cycles=data.get("consecutive_no_progress_cycles", 0),
            tasks=[ResearchTask(**x) for x in data.get("tasks", [])],
            sources=[SourceRecord(**x) for x in data.get("sources", [])],
            evidence=[Evidence(**{**x, "kind": enum_value(EvidenceKind, x.get("kind", "source"))})
                      for x in data.get("evidence", [])],
            claims=[Claim(**x) for x in data.get("claims", [])],
            claim_revisions=[ClaimRevision(**x) for x in data.get("claim_revisions", [])],
            evidence_claim_links=[EvidenceClaimLink(**{**x, "stance": EvidenceStance(x["stance"])})
                                  for x in data.get("evidence_claim_links", [])],
            evidence_comparisons=[EvidenceComparison(**x) for x in data.get("evidence_comparisons", [])],
            evidence_review_candidates=[
                EvidenceReviewCandidate(**{**x, "proposed_stance": EvidenceStance(x["proposed_stance"])})
                for x in data.get("evidence_review_candidates", [])
            ],
            dataset_files=[DatasetFileRecord(**x) for x in data.get("dataset_files", [])],
            dataset_analyses=[DatasetAnalysisRecord(**x) for x in data.get("dataset_analyses", [])],
            differential_expression_analyses=[
                DifferentialExpressionAnalysisRecord(**x)
                for x in data.get("differential_expression_analyses", [])
            ],
            citation_links=[CitationLink(**x) for x in data.get("citation_links", [])],
            cross_domain_connections=[CrossDomainConnection(**x) for x in data.get("cross_domain_connections", [])],
            contradiction_candidates=[ContradictionCandidate(**x) for x in data.get("contradiction_candidates", [])],
            hypotheses=[Hypothesis(**{**x, "status": enum_value(HypothesisStatus, x.get("status", "proposed"))})
                        for x in data.get("hypotheses", [])],
            hypothesis_groups=[HypothesisGroup(**x) for x in data.get("hypothesis_groups", [])],
            uncertainty_assessments=[UncertaintyAssessment(**x)
                                     for x in data.get("uncertainty_assessments", [])],
            experiments=[Experiment(**{**x, "status": enum_value(ExperimentStatus, x.get("status", "proposed"))})
                         for x in data.get("experiments", [])],
            findings=data.get("findings", []), decisions=data.get("decisions", []),
            created_at=data.get("created_at", utc_now()), updated_at=data.get("updated_at", utc_now()),
        )
        return run

    def log_event(self, run_id: str, event_type: str, payload: dict[str, Any],
                  event_key: str | None = None) -> None:
        with self._connect() as db:
            db.execute(
                "INSERT OR IGNORE INTO events(run_id,event_type,payload,created_at,event_key) VALUES(?,?,?,?,?)",
                (run_id, event_type, json.dumps(payload, ensure_ascii=False), utc_now(), event_key),
            )

    def list_differential_expression_analyses(self, run_id: str) -> list[dict[str, Any]]:
        """Return persisted DE analyses in creation order, including their full result payloads."""
        with self._connect() as db:
            rows = db.execute(
                """SELECT payload FROM differential_expression_analyses
                   WHERE run_id=? ORDER BY rowid""", (run_id,)
            ).fetchall()
        return [json.loads(row["payload"]) for row in rows]

    def list_events(self, run_id: str) -> list[dict[str, Any]]:
        with self._connect() as db:
            rows = db.execute(
                "SELECT event_type,payload,created_at,event_key FROM events WHERE run_id=? ORDER BY event_id",
                (run_id,),
            ).fetchall()
        return [{"event_type": r["event_type"], "payload": json.loads(r["payload"]),
                 "created_at": r["created_at"], "event_key": r["event_key"]} for r in rows]


    def list_runs(self, limit: int = 100) -> list[dict[str, Any]]:
        """List recent research runs without loading every full knowledge graph."""
        if not 1 <= limit <= 500:
            raise ValueError("limit must be between 1 and 500.")
        with self._connect() as db:
            rows = db.execute(
                "SELECT run_id,status,question,updated_at FROM runs ORDER BY updated_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    def list_resumable_runs(self) -> list[dict[str, Any]]:
        with self._connect() as db:
            rows = db.execute(
                "SELECT run_id,question,status,updated_at FROM runs WHERE status IN ('running','paused','failed','stopped') ORDER BY updated_at DESC"
            ).fetchall()
        return [dict(row) for row in rows]
