from index_writer import upsert_week_row

INDEX = """# Rainfields Mind Index

## Weeks

| Week | Range | Summary |
|------|-------|---------|
| [2026-W25](weekly/2026-W25.md) | 2026-06-15 .. 2026-06-21 | Old summary |

## Recurring topics

- Work
"""


def test_upsert_adds_new_week():
    updated = upsert_week_row(INDEX, "2026-W26", "New summary")
    assert "[2026-W26](weekly/2026-W26.md)" in updated
    assert "New summary" in updated
    assert "[2026-W25](weekly/2026-W25.md)" in updated


def test_upsert_replaces_existing_week():
    updated = upsert_week_row(INDEX, "2026-W25", "Updated summary")
    assert updated.count("[2026-W25](weekly/2026-W25.md)") == 1
    assert "Updated summary" in updated
    assert "Old summary" not in updated
