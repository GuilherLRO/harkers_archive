"""Validate generated weekly notes against the Rainfields Mind template."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import yaml

REQUIRED_FRONTMATTER_KEYS = frozenset(
    {
        "week",
        "date_range",
        "tags",
        "source_days",
        "source_files",
        "generated_from",
        "generated_at",
    }
)
TAG_PATTERN = re.compile(r"^[a-z0-9/-]+$")
REQUIRED_SECTIONS = ("# Semana ", "## Índice de fontes")


@dataclass
class ValidationResult:
    ok: bool
    errors: list[str] = field(default_factory=list)


def split_frontmatter(text: str) -> tuple[dict | None, str, list[str]]:
    errors: list[str] = []
    if not text.startswith("---\n"):
        return None, text, ["missing YAML frontmatter opener"]
    end = text.find("\n---\n", 4)
    if end == -1:
        return None, text, ["missing YAML frontmatter closer"]
    raw_yaml = text[4:end]
    body = text[end + 5 :]
    try:
        data = yaml.safe_load(raw_yaml)
    except yaml.YAMLError as exc:
        return None, body, [f"invalid YAML frontmatter: {exc}"]
    if not isinstance(data, dict):
        return None, body, ["frontmatter must be a mapping"]
    return data, body, errors


def validate_weekly_note(
    text: str,
    *,
    week_id: str,
    expected_source_files: set[str],
) -> ValidationResult:
    errors: list[str] = []
    frontmatter, body, fm_errors = split_frontmatter(text)
    errors.extend(fm_errors)
    if frontmatter is None:
        return ValidationResult(ok=False, errors=errors)

    missing_keys = REQUIRED_FRONTMATTER_KEYS - set(frontmatter)
    if missing_keys:
        errors.append(f"missing frontmatter keys: {', '.join(sorted(missing_keys))}")

    if frontmatter.get("week") != week_id:
        errors.append(f"frontmatter week mismatch: {frontmatter.get('week')!r} != {week_id!r}")

    tags = frontmatter.get("tags")
    if not isinstance(tags, list):
        errors.append("tags must be a list")
    else:
        for tag in tags:
            if not isinstance(tag, str) or not TAG_PATTERN.match(tag):
                errors.append(f"invalid tag format: {tag!r}")

    source_files = frontmatter.get("source_files")
    if not isinstance(source_files, list):
        errors.append("source_files must be a list")
    else:
        actual = {str(item) for item in source_files}
        if actual != expected_source_files:
            missing = expected_source_files - actual
            extra = actual - expected_source_files
            if missing:
                errors.append(f"source_files missing: {', '.join(sorted(missing))}")
            if extra:
                errors.append(f"source_files unexpected: {', '.join(sorted(extra))}")

    for marker in REQUIRED_SECTIONS:
        if marker not in text:
            errors.append(f"missing section marker: {marker!r}")

    if frontmatter.get("generated_from") != "dossier":
        errors.append("generated_from must be 'dossier'")

    return ValidationResult(ok=not errors, errors=errors)
