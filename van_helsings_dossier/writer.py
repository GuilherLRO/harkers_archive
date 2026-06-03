"""Render daily Markdown files for Obsidian."""

from __future__ import annotations

from datetime import date

from models import JournalEntry, Segment


def _yaml_quote(value: str) -> str:
    if not value:
        return '""'
    if any(char in value for char in ['"', ":", "#", "\n", "'"]):
        escaped = value.replace('"', '\\"')
        return f'"{escaped}"'
    return value


def _render_segments(segments: list[Segment]) -> str:
    lines = [
        f"- `[{segment.start} - {segment.end}]` {segment.text}"
        for segment in segments
    ]
    return "\n".join(lines)


def _render_entry(entry: JournalEntry) -> str:
    title = entry.source_type.replace("_", " ").title()
    lines = [
        f"### {entry.time_label} - {title}",
        "",
        f"> Source: `{entry.source_file}`",
    ]

    if entry.segment_file:
        lines.append(f"> Segments: `{entry.segment_file}`")
    if entry.extra_sources:
        joined = ", ".join(f"`{source}`" for source in entry.extra_sources)
        lines.append(f"> Also seen in: {joined}")

    lines.extend(
        [
            f"> Original source: {entry.original_source}",
            f"> Entry id: `{entry.entry_id}`",
            "> Tags:",
            "",
        ]
    )

    if entry.segments:
        lines.append(_render_segments(entry.segments))
    else:
        lines.append(entry.body)

    lines.append("")
    return "\n".join(lines)


def render_daily_file(day: date, entries: list[JournalEntry]) -> str:
    day_iso = day.isoformat()
    sources = sorted({entry.source_file for entry in entries})
    source_lines = "\n".join(f"  - {source}" for source in sources)

    title = f"Van Helsing's Dossier - {day_iso}"
    frontmatter = "\n".join(
        [
            "---",
            f"title: {_yaml_quote(title)}",
            f"date: {day_iso}",
            "tags: []",
            "sources:",
            source_lines or "  []",
            "generated_by: van_helsings_dossier",
            "---",
        ]
    )

    body_lines = [f"# {day_iso}", "", "## Entries", ""]
    for entry in sorted(entries, key=lambda item: item.moment):
        body_lines.append(_render_entry(entry))

    return frontmatter + "\n\n" + "\n".join(body_lines).rstrip() + "\n"
