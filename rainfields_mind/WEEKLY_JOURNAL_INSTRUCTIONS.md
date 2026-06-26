# Weekly Journal Instructions

Model-agnostic workflow for turning daily dossier files into tagged weekly journal notes. Any LLM or human editor can follow this document.

## Purpose

Transform `dossier/YYYY-MM-DD.md` (generated, read-only) into `rainfields_mind/weekly/YYYY-WNN.md` (curated synthesis). Do not modify `dossier/`, `transcripts/`, Python code, or the compiler.

Tags are always written in **English** (`lowercase/ascii/slash-separated`), even when the narrative is in Portuguese.

The weekly journal must cover **every ISO week represented in `dossier/`**. If a weekly note is missing, reconstruct it from the dossier files. If a weekly note already exists but does not match the current workflow, refresh it from the dossier files instead of leaving it inconsistent.

Each weekly note must include references back to the daily dossier files it was generated from.

## Operating modes

### Single-week mode

Use this when creating or refreshing one target week. Include the instruction files, the previous week if it exists, and every dossier file for the target week.

### Full-corpus reconstruction mode

Use this when setting up the journal, repairing missing weekly files, changing the tag taxonomy, or auditing consistency.

1. List every `dossier/YYYY-MM-DD.md` file.
2. Group dossier files by ISO week (Monday-Sunday, `America/Fortaleza`).
3. For each represented week, ensure `rainfields_mind/weekly/YYYY-WNN.md` exists.
4. If a week is missing, create it from its dossier files.
5. If a week exists but lacks required frontmatter, source references, current tags, or the current source-index format, reconstruct it from its dossier files.
6. Update `rainfields_mind/index.md` so every represented week has one row.
7. Do not create empty future weeks unless explicitly asked; only weeks with at least one dossier file are required in full-corpus mode.

## What to put in your prompt each week

Every week you send **one message** to the model. It must include **two instruction files**, **one optional context file**, and **all dossier files for that week**.

### Checklist (attach or paste)

| # | What | Required | Path / how to find it |
|---|------|----------|------------------------|
| 1 | Workflow spec | **Yes** | `rainfields_mind/WEEKLY_JOURNAL_INSTRUCTIONS.md` — this file |
| 2 | Tag rules | **Yes** | `rainfields_mind/TAGGING_SYSTEM.md` |
| 3 | Last week's note | If it exists | `rainfields_mind/weekly/YYYY-W(N-1).md` — for *Pendências* / open loops |
| 4 | Daily dossiers | **Yes** | Every `dossier/YYYY-MM-DD.md` from Monday through Sunday of the target week |
| 5 | Existing weekly notes | For full-corpus reconstruction | Any existing `rainfields_mind/weekly/*.md` files that may need tag or format updates |

You do **not** need to attach `rainfields_mind/index.md`, `transcripts/`, or `voice_archive/` — only compiled dossiers.

### Find dossier files for a week

ISO week = Monday–Sunday (`America/Fortaleza`). List matching files from the repo root:

```bash
# Example: week 2026-W26 = 2026-06-22 .. 2026-06-28
for d in 2026-06-22 2026-06-23 2026-06-24 2026-06-25 2026-06-26 2026-06-27 2026-06-28; do
  [ -f "dossier/${d}.md" ] && echo "dossier/${d}.md"
done
```

Missing days are normal (no capture that day). Only attach files that exist.

### Find all weeks represented in the dossier

From the repo root:

```bash
python - <<'PY'
from datetime import date
from pathlib import Path

by_week = {}
for path in sorted(Path("dossier").glob("????-??-??.md")):
    d = date.fromisoformat(path.stem)
    year, week, _ = d.isocalendar()
    by_week.setdefault(f"{year}-W{week:02d}", []).append(path)

for week, paths in by_week.items():
    print(week)
    for path in paths:
        print(f"  {path}")
PY
```

Every week printed here must have a corresponding `rainfields_mind/weekly/YYYY-WNN.md` after reconstruction.

### Fill in three values before sending

1. **`YYYY-WNN`** — target week (e.g. `2026-W26`)
2. **Date range** — Mon .. Sun (e.g. `2026-06-22 .. 2026-06-28`)
3. **Dossier list** — output of the loop above (may be 0–7 files)

### Copy-paste prompt (fill the brackets)

```text
Create the weekly journal note for week [YYYY-WNN] ([YYYY-MM-DD .. YYYY-MM-DD]).

Attached / referenced:
- rainfields_mind/WEEKLY_JOURNAL_INSTRUCTIONS.md (follow exactly, all five passes)
- rainfields_mind/TAGGING_SYSTEM.md
- rainfields_mind/weekly/[PREVIOUS-WEEK].md (open loops from last week — skip this line if no previous week)
- dossier files for this week:
  [list each path that exists, one per line, e.g. dossier/2026-06-22.md]

Output:
- Write rainfields_mind/weekly/[YYYY-WNN].md (full file contents)
- Show the one-line entry to add to rainfields_mind/index.md
- Do not modify dossier/ or any Python code
- Include daily dossier file references in frontmatter and in the source index
- If any new tag is introduced, update rainfields_mind/TAGGING_SYSTEM.md and audit previous weekly notes for whether the tag applies there too

Language: Portuguese for the narrative; keep English for reading logs, Cambly notes, and book quotes. Tags must remain English.
```

### Worked example (after W25 exists)

```text
Create the weekly journal note for week 2026-W26 (2026-06-22 .. 2026-06-28).

Attached / referenced:
- rainfields_mind/WEEKLY_JOURNAL_INSTRUCTIONS.md (follow exactly, all five passes)
- rainfields_mind/TAGGING_SYSTEM.md
- rainfields_mind/weekly/2026-W25.md (open loops from last week)
- dossier files for this week:
  dossier/2026-06-22.md
  dossier/2026-06-23.md

Output:
- Write rainfields_mind/weekly/2026-W26.md (full file contents)
- Show the one-line entry to add to rainfields_mind/index.md
- Do not modify dossier/ or any Python code
- Include daily dossier file references in frontmatter and in the source index
- If any new tag is introduced, update rainfields_mind/TAGGING_SYSTEM.md and audit previous weekly notes for whether the tag applies there too

Language: Portuguese for the narrative; keep English for reading logs, Cambly notes, and book quotes. Tags must remain English.
```

In Cursor: use `@` on each file instead of pasting contents. In other tools: paste file bodies under clear headings (`## WEEKLY_JOURNAL_INSTRUCTIONS`, `## dossier/2026-06-22`, …).

## Inputs

- All `dossier/YYYY-MM-DD.md` files whose dates fall in the target ISO week (Monday 00:00 – Sunday 23:59, local time: America/Fortaleza)
- [TAGGING_SYSTEM.md](TAGGING_SYSTEM.md) for vocabulary and normalization rules
- Previous week's `rainfields_mind/weekly/YYYY-W(N-1).md` for open loops (if it exists)
- Existing weekly notes when reconstructing all weeks or changing tags, so older notes can be updated consistently

## Output

One file per represented week: `rainfields_mind/weekly/YYYY-WNN.md` using the template below. Update `rainfields_mind/index.md` when adding or refreshing weeks.

## Five-pass process (run at least five iterations)

Run these passes internally before finalizing. Each pass should refine the previous; do not skip critique.

### Pass 1 — Inventory

For each dossier day in the week:

- List every `### HH:MM:SS` entry
- Record `entry_id`, source type (voice/typed), and a one-line topic guess
- Record the source dossier file path (`dossier/YYYY-MM-DD.md`) for each day and each source-index row
- Note missing days (no dossier file = no capture, not an error)

### Pass 2 — Transcription cleanup

Without editing dossier files:

- Flag Whisper loops (repeated identical segments)
- Flag near-duplicate memos (same topic within minutes)
- Map garbled terms using TAGGING_SYSTEM normalization table
- Mark `capture/fragment`, `capture/test`, `capture/transcription-loop` where appropriate
- For quotes: decide if text is trustworthy verbatim or should be summarized as remembered passage

### Pass 3 — Tagging

Per entry:

- Assign 1–5 English tags from canonical vocabulary; propose candidate tags only when justified
- Separate `reading/progress`, `reading/summary`, and `quote/book`
- Attach book slug (e.g. `reading/twelve-kings`) when identifiable

If introducing a new tag:

- Add it to `rainfields_mind/TAGGING_SYSTEM.md` before publishing the weekly note
- Search existing weekly notes and source-index rows for entries where the new tag also applies
- Update affected prior weekly files so tag usage is consistent across the journal
- Add an alias or evolution note when replacing, splitting, or merging an older tag

### Pass 4 — Synthesis

Write the weekly note in **Portuguese**, except:

- Preserve **English** for reading logs, Cambly notes, and book quotes where original wording matters

Cluster entries by theme. Merge related memos into one bullet. Do not quote transcription loops verbatim.

Sections (include only when relevant):

- Resumo da semana
- Trabalho
- Mestrado e pesquisa
- Leitura
- Vida pessoal
- Projetos e ideias
- Citações e trechos
- Pendências para a próxima semana
- Índice de fontes

### Pass 5 — Critique and refinement

- Reread draft against source entries; remove overconfident interpretations
- Confirm open loops from last week were addressed or carried forward
- Confirm `capture/*` entries are not overstated in narrative
- If a new ambiguity appeared twice, propose a TAGGING_SYSTEM update
- Confirm all tags are English and appear in `TAGGING_SYSTEM.md` as canonical or candidate tags
- Confirm every source-index row points back to its daily dossier file
- In full-corpus reconstruction mode, confirm every ISO week represented in `dossier/` has a weekly note and an index row
- Final text should read like a human journal, not a transcript dump

## Weekly note template

```markdown
---
week: YYYY-WNN
date_range: YYYY-MM-DD .. YYYY-MM-DD
tags: []
source_days: []
source_files:
  - dossier/YYYY-MM-DD.md
generated_from: dossier
generated_at: YYYY-MM-DD
---

# Semana YYYY-WNN

## Resumo da semana

[2–4 sentences: dominant themes, emotional arc, key outcomes]

## Trabalho

[Only if relevant]

## Mestrado e pesquisa

[Only if relevant]

## Leitura

[Progress and summaries; normalized book title]

## Vida pessoal

[Only if relevant]

## Projetos e ideias

[Only if relevant]

## Citações e trechos

[Book quotes, song lines, outdoor text — preserve original language; note if paraphrased from voice]

## Pendências para a próxima semana

- [Open loops with enough context to act on]

## Índice de fontes

| Tópico | Dossiê | Dia | Hora | entry_id | Tags |
|--------|--------|-----|------|----------|------|
| ... | `dossier/YYYY-MM-DD.md` | YYYY-MM-DD | HH:MM:SS | `hexid` | tag1, tag2 |
```

## Book quotes rules

1. **Progress** → `Leitura` section, tag `reading/progress`
2. **Summary** → `Leitura` section, tag `reading/summary`
3. **Quote** → `Citações e trechos`, tag `quote/book` (+ book slug if known)

For voice-captured quotes:

- If transcription is clean and reads like intentional recitation → present as quote with `entry_id` link
- If ASR is uncertain → label as *passagem lembrada (transcrição incerta)* and avoid presenting as exact text
- Never "fix" literary quotes aggressively unless the correction is obvious

## Handling sparse or partial weeks

- Partial weeks (e.g. corpus starts mid-week) are valid; state coverage in the summary
- Missing days: do not invent content
- Single-entry days still belong in the source index
- In full-corpus reconstruction mode, sparse weeks are still required if at least one dossier file exists for that ISO week
- Do not create an empty weekly note for a week with no dossier files unless explicitly requested

## After publishing

1. Add frontmatter `tags` as deduplicated union of entry tags used that week; all tags must be English
2. Add frontmatter `source_days` and `source_files` for the dossier files used
3. Update `rainfields_mind/index.md` with week link and one-line summary
4. If a new tag was introduced, update `TAGGING_SYSTEM.md`, then audit and update previous weekly notes where the tag applies
5. If a tag was renamed, split, or merged, update affected previous weekly notes and document the change in `TAGGING_SYSTEM.md`

## Trigger phrases

Use this workflow when the user asks to:

- create or refresh a weekly journal note
- synthesize dossier files into a week summary
- run Rainfields Mind / weekly aggregation
- tag and compile journal entries for a date range
