# Van Helsing's Dossier

Part of [Harker's Archive](../README.md). Companion to [Dr. Seward's Phonograph](../sewards_phonograph/) and [Mina's Typewriter](../mina_typewriter/): compile scattered transcript files into **Obsidian-friendly daily Markdown notes**.

In *Dracula*, Van Helsing gathers and orders testimony from many witnesses into one coherent case file. This module does the same for your record base: typed notes and voice transcripts become one readable journal entry per day.

## What it does

1. Scans `transcripts/` for known source formats.
2. Normalizes them into journal entries with metadata (source file, original source, timestamp, entry id).
3. Deduplicates obvious repeats (especially plain transcript vs segment sidecars).
4. Writes one Markdown file per day to `dossier/`, e.g. `2026-06-02.md`.
5. Tracks processed sources in `dossier/.van_helsings_dossier_manifest.json` so reruns only rebuild affected days.

## Source formats

| Pattern | Example | Treated as |
|---------|---------|------------|
| Typed daily notes | `typed_notes_20260602_390353883.txt` | One entry per `[YYYYMMDD_HHMMSS] message` line |
| Voice transcript | `20260602_013737_390353883.txt` | One entry; timestamp from filename |
| Compact voice transcript | `20260602130336.txt` | One entry; timestamp from filename |
| Segment sidecar | `*_segments.txt` | Paired with matching transcript; used for structured body, never a separate entry |

## Prerequisites

| Requirement | Why |
|-------------|-----|
| **Python 3.13+** | Project dependency |
| **[uv](https://docs.astral.sh/uv/)** | Installs dependencies and runs the compiler |

## Quick start

1. From the [monorepo root](../README.md), install workspace dependencies:

   ```bash
   uv sync --all-packages
   ```

2. Compile transcripts into daily Markdown notes:

   ```bash
   cd van_helsings_dossier
   uv run python compile.py
   ```

   Defaults: read `transcripts/`, write `dossier/`.

3. Open the output folder in Obsidian as part of your vault, or symlink `dossier/` into an existing vault.

4. Re-run after new transcripts arrive. Only changed days are rebuilt.

   ```bash
   uv run python compile.py --force
   ```

   Use `--force` to re-parse every source file.

## Configuration

Optional overrides in the root `.env`:

```bash
HARKERS_TRANSCRIPTS_DIR=/absolute/path/to/harkers_archive/transcripts
HARKERS_DOSSIER_DIR=/absolute/path/to/harkers_archive/dossier
```

CLI flags override environment defaults:

```bash
uv run python compile.py --transcripts-dir ../transcripts --dossier-dir ../dossier
```

## Output format

Each daily file includes YAML frontmatter and structured entries:

```markdown
---
title: "Van Helsing's Dossier - 2026-06-02"
date: 2026-06-02
tags: []
sources:
  - typed_notes_20260602_390353883.txt
generated_by: van_helsings_dossier
---

# 2026-06-02

## Entries

### 00:32:22 - Typed note

> Source: `typed_notes_20260602_390353883.txt`
> Original source: Telegram text
> Entry id: `abc123`
> Tags:

Oi
```

Voice entries with segment sidecars render timestamped bullet lines under metadata. The `Tags:` line is left blank for manual Obsidian tags later.

## Incremental behavior

The manifest stores, per source file:

- content hash and size
- segment sidecar hash (when present)
- parsed entry ids
- affected output days

On each run:

1. New or changed sources are re-parsed.
2. Removed sources drop their entries and mark affected days dirty.
3. Only dirty daily files are rewritten.

## Manual verification

From `van_helsings_dossier/`:

```bash
uv run python compile.py
uv run python compile.py   # second run should report no changes
uv run python compile.py --force
```

Expected:

- Daily files appear under `dossier/`.
- Segment sidecars do not create duplicate entries.
- A second unchanged run logs `No changes detected`.
- Adding a transcript for an existing day updates only that day's Markdown file on the next run.

## Scheduled via `helsings_round.py`

When the root coordinator is running, Van Helsing's Dossier is invoked automatically:

- **Compile** after a transcription pass that produced new voice transcripts, or at least every 24 hours (`DOSSIER_INTERVAL_MINUTES`, default `1440`).

Disable with `DOSSIER_ENABLED=false` in the root `.env`. Dossier failures are logged and do not stop the capture bot. See the [monorepo README](../README.md) section on `helsings_round.py`.

## License

This project is licensed under the [MIT License](../LICENSE).
