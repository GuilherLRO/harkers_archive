from compile_week import compile_weeks


def test_dry_run_lists_dirty_week(tmp_path, monkeypatch):
    runs_dir = tmp_path / "agent_runs"
    monkeypatch.setattr("compile_week.RUNS_DIR", runs_dir)

    dossier = tmp_path / "dossier"
    rainfields = tmp_path / "rainfields_mind"
    weekly = rainfields / "weekly"
    dossier.mkdir(parents=True)
    weekly.mkdir(parents=True)
    (rainfields / "index.md").write_text(
        "# Rainfields Mind Index\n\n## Weeks\n\n| Week | Range | Summary |\n|------|-------|---------|\n",
        encoding="utf-8",
    )
    (dossier / "2026-06-22.md").write_text("note", encoding="utf-8")

    summary = compile_weeks(
        dossier_dir=dossier,
        rainfields_dir=rainfields,
        model="o4-mini",
        dry_run=True,
    )
    assert summary["dirty_weeks"] == ["2026-W26"]
    assert summary.get("dry_run") is True


def test_skip_when_nothing_dirty(tmp_path, monkeypatch):
    runs_dir = tmp_path / "agent_runs"
    monkeypatch.setattr("compile_week.RUNS_DIR", runs_dir)

    dossier = tmp_path / "dossier"
    rainfields = tmp_path / "rainfields_mind"
    weekly = rainfields / "weekly"
    dossier.mkdir(parents=True)
    weekly.mkdir(parents=True)
    (rainfields / "index.md").write_text("index", encoding="utf-8")

    summary = compile_weeks(
        dossier_dir=dossier,
        rainfields_dir=rainfields,
        model="o4-mini",
        dry_run=False,
    )
    assert summary["skipped"] is True
    assert runs_dir.exists()
