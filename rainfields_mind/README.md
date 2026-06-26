# Rainfields Mind

Curated synthesis layer on top of the generated daily dossiers.

## Relationship to other layers

| Layer | Path | Role |
|-------|------|------|
| Raw audio | `voice_archive/` | Telegram voice capture |
| Transcripts | `transcripts/` | Whisper output and typed notes |
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
└── weekly/
    └── YYYY-WNN.md
```

## How to use

1. Ensure `dossier/` is up to date (`van_helsings_dossier/compile.py`).
2. Open [WEEKLY_JOURNAL_INSTRUCTIONS.md § What to put in your prompt each week](WEEKLY_JOURNAL_INSTRUCTIONS.md#what-to-put-in-your-prompt-each-week).
3. Attach to your LLM prompt: this instructions file, `TAGGING_SYSTEM.md`, last week's `weekly/*.md` (if any), and every `dossier/YYYY-MM-DD.md` for that ISO week.
4. Save the result to `rainfields_mind/weekly/YYYY-WNN.md` and update [index.md](index.md).

## Language

Weekly notes are primarily in Portuguese. Preserve English for reading logs, language-learning notes, and book quotes when translation would lose meaning.

## Week boundaries

Use ISO weeks (Monday–Sunday). Partial weeks at the start or end of the corpus are valid.
