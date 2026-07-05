# Rainfields Mind

Curated synthesis layer on top of the generated daily dossiers.

## Relationship to other layers

| Layer | Path | Role |
|-------|------|------|
| Raw audio | `voice_archive/` | Telegram voice capture |
| Transcripts | `transcripts/` | OpenAI transcription output and typed notes |
| Daily dossier | `dossier/` | Compiled daily Markdown (generated; do not hand-edit) |
| **Rainfields Mind** | `rainfields_mind/` | Tagged weekly synthesis and instructions |

The daily dossier is the immutable raw chronicle. Rainfields Mind adds tags, transcription cleanup, thematic clustering, and weekly narrative notes without changing the compiler or capture pipeline.

## Layout

```text
rainfields_mind/
├── README.md
├── TAGGING_SYSTEM.md
├── WEEKLY_JOURNAL_INSTRUCTIONS.md
├── index.md
├── weekly/
│   └── YYYY-WNN.md
└── agent/                   # Python workspace (pyproject.toml lives here)
    ├── README.md
    ├── compile_week.py
    ├── graph.py
    ├── runs/                # reasoning logs (gitignored)
    └── tests/
```

## Automated agent

The agent is a separate uv workspace under [`agent/`](agent/). It follows [WEEKLY_JOURNAL_INSTRUCTIONS.md](WEEKLY_JOURNAL_INSTRUCTIONS.md) and [TAGGING_SYSTEM.md](TAGGING_SYSTEM.md) at runtime. Safe to run daily — most runs skip when dossiers are unchanged.

```bash
cd rainfields_mind/agent
uv run python compile_week.py                 # all dirty weeks
uv run python compile_week.py --week 2026-W26 # single week
uv run python compile_week.py --all           # full-corpus rebuild
uv run python compile_week.py --force         # ignore manifest
uv run python compile_week.py --dry-run       # list dirty weeks, no API calls
uv run python compile_week.py --json-summary  # machine-readable output
```

**Cron example** (after dossier compile):

```bash
cd /path/to/harkers_archive/rainfields_mind/agent && uv run python compile_week.py
```

See [agent/README.md](agent/README.md) for agent-specific details.

### Configuration

Set in the repo root `.env`:

| Variable | Default | Purpose |
|----------|---------|---------|
| `OPENAI_API_KEY` | — | Required for agent runs |
| `RAINFIELDS_MODEL` | `o4-mini` | OpenAI model (`gpt-4.1` also works) |
| `HARKERS_DOSSIER_DIR` | `{repo}/dossier` | Input dossiers |
| `HARKERS_RAINFIELDS_DIR` | `{repo}/rainfields_mind` | Output folder |
| `RAINFIELDS_TIMEZONE` | `America/Fortaleza` | ISO week boundaries |

### Reasoning logs

Every run writes JSON to `agent/runs/{timestamp}-{week_or_skip}.json` (gitignored). Skip runs log `action: skip` with `skip_reason: no_dirty_weeks`.

### Change detection

A week is recompiled only when the weekly note is missing/invalid, dossier files changed (SHA-256 in `agent/.rainfields_mind_manifest.json`), or `--force` / `--all` is passed.

## Manual workflow

1. Ensure `dossier/` is up to date (`van_helsings_dossier/compile.py`).
2. Open [WEEKLY_JOURNAL_INSTRUCTIONS.md § What to put in your prompt each week](WEEKLY_JOURNAL_INSTRUCTIONS.md#what-to-put-in-your-prompt-each-week).
3. Attach to your LLM prompt: this instructions file, `TAGGING_SYSTEM.md`, last week's `weekly/*.md` (if any), and every `dossier/YYYY-MM-DD.md` for that ISO week.
4. Save the result to `weekly/YYYY-WNN.md` and update [index.md](index.md).

Or run the agent instead of steps 2–4.

## Language

Weekly notes are primarily in Portuguese. Preserve English for reading logs, language-learning notes, and book quotes when translation would lose meaning.

## Week boundaries

Use ISO weeks (Monday–Sunday). Partial weeks at the start or end of the corpus are valid.

## Tests

```bash
cd rainfields_mind/agent
uv sync --extra dev
uv run pytest
```

For the wider archive checklist, including coordinator delivery, dossier compile, and Telegram smoke checks, see the root [TEST_PLAN.md](../TEST_PLAN.md).
