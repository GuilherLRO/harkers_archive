from validate import validate_weekly_note


def _valid_note() -> str:
    return """---
week: 2026-W26
date_range: 2026-06-22 .. 2026-06-28
tags: [work/kroger]
source_days: [2026-06-22]
source_files:
  - dossier/2026-06-22.md
generated_from: dossier
generated_at: 2026-06-26
---

# Semana 2026-W26

## Resumo da semana

Resumo.

## Índice de fontes

| Tópico | Dossiê | Dia | Hora | entry_id | Tags |
|--------|--------|-----|------|----------|------|
| test | `dossier/2026-06-22.md` | 2026-06-22 | 10:00:00 | `abc` | work/kroger |
"""


def test_validate_accepts_valid_note():
    result = validate_weekly_note(
        _valid_note(),
        week_id="2026-W26",
        expected_source_files={"dossier/2026-06-22.md"},
    )
    assert result.ok


def test_validate_rejects_missing_frontmatter_key():
    text = _valid_note().replace("generated_at: 2026-06-26\n", "")
    result = validate_weekly_note(
        text,
        week_id="2026-W26",
        expected_source_files={"dossier/2026-06-22.md"},
    )
    assert not result.ok
    assert any("generated_at" in err for err in result.errors)


def test_validate_rejects_mismatched_source_files():
    result = validate_weekly_note(
        _valid_note(),
        week_id="2026-W26",
        expected_source_files={"dossier/2026-06-23.md"},
    )
    assert not result.ok
