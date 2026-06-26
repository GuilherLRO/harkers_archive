# Rainfields Mind agent

Python workspace for the weekly synthesis agent. Curated output (weekly notes, index, tagging docs) lives one level up in [`../`](../README.md).

## Run

```bash
cd rainfields_mind/agent
uv run python compile_week.py
uv run python compile_week.py --dry-run
```

Set `OPENAI_API_KEY` in the repo root `.env`. See [../README.md](../README.md) for full configuration and cron setup.

## Layout

```text
agent/
├── compile_week.py      # CLI entry point
├── graph.py             # LangGraph pipeline
├── manifest.py          # incremental change detection
├── runs/                # reasoning logs (gitignored)
├── .rainfields_mind_manifest.json
└── tests/
```

## Tests

```bash
uv sync --extra dev
uv run pytest
```
