"""Shared path constants for the Rainfields Mind agent."""

from __future__ import annotations

from pathlib import Path

AGENT_DIR = Path(__file__).resolve().parent
RAINFIELDS_ROOT = AGENT_DIR.parent
ARCHIVE_ROOT = AGENT_DIR.parents[1]

MANIFEST_PATH = AGENT_DIR / ".rainfields_mind_manifest.json"
RUNS_DIR = AGENT_DIR / "runs"
