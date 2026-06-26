"""JSON reasoning logs for Rainfields Mind agent runs."""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path


@dataclass
class RunLog:
    run_id: str
    started_at: str
    week: str | None
    action: str
    skip_reason: str | None = None
    model: str | None = None
    dirty_reason: str | None = None
    reasoning: str | None = None
    dossier_files: list[str] = field(default_factory=list)
    validation: dict | None = None
    outputs: dict | None = None
    proposed_tags: list[dict] = field(default_factory=list)
    error: str | None = None

    @classmethod
    def new(cls, *, week: str | None = None, action: str = "skip") -> RunLog:
        return cls(
            run_id=str(uuid.uuid4()),
            started_at=datetime.now(UTC).isoformat(),
            week=week,
            action=action,
        )

    def write(self, runs_dir: Path) -> Path:
        runs_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        suffix = self.week or "skip"
        path = runs_dir / f"{stamp}-{suffix}.json"
        path.write_text(
            json.dumps(asdict(self), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return path
