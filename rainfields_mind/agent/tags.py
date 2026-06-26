"""Append proposed tags to TAGGING_SYSTEM.md candidate section."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from typing import Protocol

CANDIDATE_HEADER = "## Candidate tags (promote when recurring)"


class TagProposal(Protocol):
    tag: str
    definition: str


@dataclass(frozen=True)
class ProposedTag:
    tag: str
    definition: str


def known_tags(tagging_text: str) -> set[str]:
    tags: set[str] = set()
    for match in re.finditer(r"`([a-z0-9/-]+)`", tagging_text):
        tags.add(match.group(1))
    return tags


def append_candidate_tags(
    tagging_text: str,
    proposed: list[TagProposal | ProposedTag],
    *,
    today: date | None = None,
) -> tuple[str, list[ProposedTag]]:
    if not proposed:
        return tagging_text, []

    existing = known_tags(tagging_text)
    to_add = [item for item in proposed if item.tag not in existing]
    if not to_add:
        return tagging_text, []

    if CANDIDATE_HEADER not in tagging_text:
        raise ValueError(f"{CANDIDATE_HEADER} section not found")

    stamp = (today or date.today()).isoformat()
    insertion_lines = [f"- `{item.tag}` — {item.definition.strip()}" for item in to_add]
    comment = f"<!-- agent {stamp} -->"

    lines = tagging_text.splitlines()
    header_idx = lines.index(CANDIDATE_HEADER)
    insert_at = header_idx + 2
    new_lines = lines[:insert_at] + [comment] + insertion_lines + lines[insert_at:]
    return "\n".join(new_lines) + ("\n" if tagging_text.endswith("\n") else ""), to_add
