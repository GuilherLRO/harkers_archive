"""LangGraph state and structured output models."""

from __future__ import annotations

from typing import Literal, TypedDict

from pydantic import BaseModel, Field


class ProposedTag(BaseModel):
    tag: str
    definition: str


class WeeklySynthesis(BaseModel):
    reasoning: str = Field(description="Audit trail written before the weekly note.")
    weekly_markdown: str = Field(description="Complete weekly note with YAML frontmatter.")
    index_summary: str = Field(description="One-line summary for index.md.")
    proposed_tags: list[ProposedTag] = Field(default_factory=list)


class GraphState(TypedDict, total=False):
    week_id: str
    date_range: str
    action: Literal["create", "refresh"]
    dossier_files: list[str]
    dossier_contents: list[tuple[str, str]]
    previous_week_text: str | None
    rainfields_dir: str
    dossier_dir: str
    model: str
    system_prompt: str
    synthesis: WeeklySynthesis | None
    validation_errors: list[str]
    retry_count: int
    reasoning: str
    weekly_markdown: str
    index_summary: str
    proposed_tags: list[ProposedTag]
    weekly_path: str
    index_updated: bool
    tags_appended: list[str]
    error: str | None
