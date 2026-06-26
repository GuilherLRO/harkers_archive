"""Update rainfields_mind/index.md week table deterministically."""

from __future__ import annotations

import re

from weeks import week_bounds

WEEKS_HEADER = "## Weeks"
TABLE_HEADER = "| Week | Range | Summary |"
ROW_PATTERN = re.compile(
    r"^\| \[(\d{4}-W\d{2})\]\(weekly/\1\.md\) \| ([^|]+) \| ([^|]+) \|$"
)


def upsert_week_row(index_text: str, week_id: str, summary: str) -> str:
    info = week_bounds(week_id)
    new_row = (
        f"| [{week_id}](weekly/{week_id}.md) | {info.date_range} | {summary.strip()} |"
    )
    lines = index_text.splitlines()
    if WEEKS_HEADER not in lines:
        raise ValueError(f"{WEEKS_HEADER} section not found in index.md")

    weeks_idx = lines.index(WEEKS_HEADER)
    table_start = _find_table_start(lines, weeks_idx)
    table_end = _find_table_end(lines, table_start)

    existing_rows: dict[str, str] = {}
    for line in lines[table_start + 2 : table_end]:
        match = ROW_PATTERN.match(line.strip())
        if match:
            existing_rows[match.group(1)] = line.strip()

    existing_rows[week_id] = new_row
    sorted_rows = [existing_rows[key] for key in sorted(existing_rows)]

    new_lines = (
        lines[: table_start + 2]
        + sorted_rows
        + lines[table_end:]
    )
    return "\n".join(new_lines) + ("\n" if index_text.endswith("\n") else "")


def _find_table_start(lines: list[str], weeks_idx: int) -> int:
    for idx in range(weeks_idx + 1, len(lines)):
        if lines[idx].strip() == TABLE_HEADER:
            return idx
    raise ValueError("Weeks table header not found in index.md")


def _find_table_end(lines: list[str], table_start: int) -> int:
    for idx in range(table_start + 2, len(lines)):
        if lines[idx].startswith("## ") or lines[idx].startswith("# "):
            return idx
        if lines[idx].strip() == "" and idx > table_start + 2:
            return idx
    return len(lines)
