"""Load instruction documents for the Rainfields Mind agent."""

from __future__ import annotations

from pathlib import Path

from paths import AGENT_DIR, RAINFIELDS_ROOT

AGENT_DOCS = ("agent_system.md",)
RAINFIELDS_DOCS = (
    "WEEKLY_JOURNAL_INSTRUCTIONS.md",
    "TAGGING_SYSTEM.md",
)


def load_system_prompt(rainfields_dir: Path | None = None) -> str:
    root = rainfields_dir or RAINFIELDS_ROOT
    parts: list[str] = []
    for name in AGENT_DOCS:
        path = AGENT_DIR / name
        parts.append(f"<!-- {name} -->\n{path.read_text(encoding='utf-8').strip()}")
    for name in RAINFIELDS_DOCS:
        path = root / name
        parts.append(f"<!-- {name} -->\n{path.read_text(encoding='utf-8').strip()}")
    return "\n\n---\n\n".join(parts)


def build_user_prompt(
    *,
    week_id: str,
    date_range: str,
    action: str,
    dossier_files: list[tuple[str, str]],
    previous_week_text: str | None,
) -> str:
    lines = [
        f"Create the weekly journal note for week {week_id} ({date_range}).",
        f"Action: {action}",
        "",
        "Dossier files for this week:",
    ]
    for relpath, _content in dossier_files:
        lines.append(f"- {relpath}")

    if previous_week_text:
        lines.extend(
            [
                "",
                "Previous week note (open loops):",
                previous_week_text.strip(),
            ]
        )

    lines.extend(
        [
            "",
            "Dossier contents:",
        ]
    )
    for relpath, content in dossier_files:
        lines.extend([f"## {relpath}", content.strip(), ""])

    return "\n".join(lines).strip() + "\n"
