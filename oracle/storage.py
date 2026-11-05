"""SQLite persistence for research runs, snapshots, and append-only events."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from .models import (
    Claim, Evidence, EvidenceClaimLink, EvidenceKind, EvidenceStance, Experiment,
    ExperimentStatus, Hypothesis, HypothesisGroup, HypothesisStatus, ResearchMode,
    ResearchRun, ResearchTask, RunStatus, UncertaintyAssessment, utc_now,
)


class ResearchStore:
    def __init__(self, path: str | Path = "data/oracle.sqlite3") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.path)
        db.row_factory = sqlite3.Row
        return db

    def _initialize(self) -> None:
        with self._connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS runs (
                    run_id TEXT PRIMARY KEY, status TEXT NOT NULL,
                    question TEXT NOT NULL, payload TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS events (
                    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL, event_type TEXT NOT NULL,
                    payload TEXT NOT NULL, created_at TEXT NOT NULL
                );
            """)

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
            tasks=[ResearchTask(**x) for x in data.get("tasks", [])],
            evidence=[Evidence(**{**x, "kind": enum_value(EvidenceKind, x.get("kind", "source"))})
                      for x in data.get("evidence", [])],
            claims=[Claim(**x) for x in data.get("claims", [])],
            evidence_claim_links=[EvidenceClaimLink(**{**x, "stance": EvidenceStance(x["stance"])})
                                  for x in data.get("evidence_claim_links", [])],
            hypotheses=[Hypothesis(**{**x, "status": enum_value(HypothesisStatus, x.get("status", "proposed"))})
                        for x in data.get("hypotheses", [])],
            hypothesis_groups=[HypothesisGroup(**x) for x in data.get("hypothesis_groups", [])],
            uncertainty_assessments=[UncertaintyAssessment(**x)
                                     for x in data.get("uncertainty_assessments", [])],
            experiments=[Experiment(**{**x, "status": enum_value(ExperimentStatus, x.get("status", "proposed"))})
                         for x in data.get("experiments", [])],
            findings=data.get("findings", []), decisions=data.get("decisions", []),
            created_at=data.get("created_at", utc_now()),
            updated_at=data.get("updated_at", utc_now()),
        )
        return run

    def log_event(self, run_id: str, event_type: str, payload: dict[str, Any]) -> None:
        with self._connect() as db:
            db.execute(
                "INSERT INTO events(run_id,event_type,payload,created_at) VALUES(?,?,?,?)",
                (run_id, event_type, json.dumps(payload, ensure_ascii=False), utc_now()),
            )

    def list_events(self, run_id: str) -> list[dict[str, Any]]:
        with self._connect() as db:
            rows = db.execute(
                "SELECT event_type,payload,created_at FROM events WHERE run_id=? ORDER BY event_id",
                (run_id,),
            ).fetchall()
        return [{"event_type": r["event_type"], "payload": json.loads(r["payload"]),
                 "created_at": r["created_at"]} for r in rows]

    def list_resumable_runs(self) -> list[dict[str, Any]]:
        with self._connect() as db:
            rows = db.execute(
                "SELECT run_id,question,status,updated_at FROM runs WHERE status IN ('running','paused','failed') ORDER BY updated_at DESC"
            ).fetchall()
        return [dict(row) for row in rows]
