from pathlib import Path

from manifest import Manifest, discover_dirty_weeks, update_week_record


def _valid_weekly(week_id: str, source_files: list[str]) -> str:
    sources_yaml = "\n".join(f"  - {path}" for path in source_files)
    return f"""---
week: {week_id}
date_range: 2026-06-22 .. 2026-06-28
tags: [work]
source_days: [2026-06-22]
source_files:
{sources_yaml}
generated_from: dossier
generated_at: 2026-06-26
---

# Semana {week_id}

## Resumo da semana

Resumo.

## Índice de fontes

| Tópico | Dossiê | Dia | Hora | entry_id | Tags |
|--------|--------|-----|------|----------|------|
| test | `dossier/2026-06-22.md` | 2026-06-22 | 10:00:00 | `abc` | work |
"""


def test_discover_dirty_when_weekly_missing(tmp_path):
    dossier = tmp_path / "dossier"
    weekly = tmp_path / "weekly"
    dossier.mkdir()
    weekly.mkdir()
    dossier_file = dossier / "2026-06-22.md"
    dossier_file.write_text("content", encoding="utf-8")

    dirty = discover_dirty_weeks(
        manifest=Manifest(),
        dossier_files_by_week={"2026-W26": [dossier_file]},
        weekly_dir=weekly,
    )
    assert len(dirty) == 1
    assert dirty[0].reason == "weekly note missing"


def test_discover_clean_when_manifest_matches(tmp_path):
    dossier = tmp_path / "dossier"
    weekly = tmp_path / "weekly"
    dossier.mkdir()
    weekly.mkdir()
    dossier_file = dossier / "2026-06-22.md"
    dossier_file.write_text("content", encoding="utf-8")
    weekly_file = weekly / "2026-W26.md"
    weekly_file.write_text(
        _valid_weekly("2026-W26", ["dossier/2026-06-22.md"]),
        encoding="utf-8",
    )

    manifest = Manifest()
    update_week_record(
        manifest,
        "2026-W26",
        [dossier_file],
        weekly_file,
        compiled_at="2026-06-26T00:00:00+00:00",
    )

    dirty = discover_dirty_weeks(
        manifest=manifest,
        dossier_files_by_week={"2026-W26": [dossier_file]},
        weekly_dir=weekly,
    )
    assert dirty == []


def test_discover_dirty_when_dossier_changes(tmp_path):
    dossier = tmp_path / "dossier"
    weekly = tmp_path / "weekly"
    dossier.mkdir()
    weekly.mkdir()
    dossier_file = dossier / "2026-06-22.md"
    dossier_file.write_text("content v1", encoding="utf-8")
    weekly_file = weekly / "2026-W26.md"
    weekly_file.write_text(
        _valid_weekly("2026-W26", ["dossier/2026-06-22.md"]),
        encoding="utf-8",
    )

    manifest = Manifest()
    update_week_record(
        manifest,
        "2026-W26",
        [dossier_file],
        weekly_file,
        compiled_at="2026-06-26T00:00:00+00:00",
    )

    dossier_file.write_text("content v2", encoding="utf-8")
    dirty = discover_dirty_weeks(
        manifest=manifest,
        dossier_files_by_week={"2026-W26": [dossier_file]},
        weekly_dir=weekly,
    )
    assert len(dirty) == 1
    assert "dossier changed" in dirty[0].reason
