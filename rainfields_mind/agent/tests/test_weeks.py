from datetime import date

from weeks import group_dossiers_by_week, previous_week_id, week_bounds, week_id_for_date

def test_week_id_for_date():
    assert week_id_for_date(date(2026, 6, 22)) == "2026-W26"


def test_week_bounds():
    info = week_bounds("2026-W26")
    assert info.start == date(2026, 6, 22)
    assert info.end == date(2026, 6, 28)
    assert info.date_range == "2026-06-22 .. 2026-06-28"


def test_previous_week_id():
    assert previous_week_id("2026-W26") == "2026-W25"


def test_group_dossiers_by_week(tmp_path):
    dossier = tmp_path / "dossier"
    dossier.mkdir()
    (dossier / "2026-06-22.md").write_text("day1", encoding="utf-8")
    (dossier / "2026-06-29.md").write_text("day2", encoding="utf-8")
    grouped = group_dossiers_by_week(dossier)
    assert "2026-W26" in grouped
    assert "2026-W27" in grouped
    assert len(grouped["2026-W26"]) == 1
