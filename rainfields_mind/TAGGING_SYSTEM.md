# Tagging System

Controlled vocabulary for entry-level and weekly tags. Tags improve over time; start broad, split when crowded.

## Format

- Tags must be in English, even when weekly narrative prose is Portuguese
- Lowercase, ASCII, slash-separated: `domain/subtopic`
- Apply at entry granularity in the source index; derive day/week frontmatter tags as the union of entry tags
- Maximum ~5 tags per entry; prefer precision over volume

## Initial canonical tags

Use these from the first weekly pass:

| Tag | When to use |
|-----|-------------|
| `life/daily-reflection` | End-of-day journal, mood, routine, productivity self-assessment |
| `life/routine` | Wake time, sleep goals, schedule intentions |
| `work` | Consulting, clients, deliverables, meetings (any employer/client) |
| `study/mestrado` | Thesis, article, experiments, scholarship, congress submission |
| `reading/progress` | Chapter/page markers, "starting chapter N" |
| `reading/summary` | Plot or concept summaries in your own words |
| `quote/book` | Direct or near-direct literary passages from a book |
| `quote/other` | Quotes from songs, outdoors, people, non-book sources |
| `learning/english` | Cambly, pronunciation, English practice notes |
| `project/harkers-archive` | This journaling pipeline, capture, transcription, dossier |
| `project/rainfields-mind` | Weekly aggregation, tagging, synthesis layer (Rainfields Mind) |
| `social` | Dates, forró, family, friends, social outings |
| `health` | Therapy, grief, emotional processing, dreams affecting mood |
| `capture/fragment` | Stubs, empty prompts, single words, incomplete lists |
| `capture/test` | Recorder tests, hostname/ID clipboard captures |
| `capture/transcription-loop` | Whisper repetition artifacts |
| `life/phone-distraction` | Phone overuse, leaving phone at home strategies |
| `life/sleep` | Sleep schedule, late nights, early wake goals |
| `reading/twelve-kings` | *Twelve Kings in Sharakai* (Bradley P. Beaulieu) |
| `work/kroger` | Kroger grocery client deliverables |
| `work/nike` | Nike client QA and deliverables |
| `work/ariat` | Ariat client work |
| `work/uber` | Uber-related client tasks |
| `work/ipt` | IPT client tasks |
| `work/azana` | Azana project tasks |
| `study/article` | Mestrado article writing and experiments |
| `study/cbeb` | CBEB/Sebeb congress submission |
| `study/reasoning-agents` | Reasoning-agent follow-up on QA experiments |
| `learning/cambly` | Cambly English lessons |
| `learning/pronunciation` | Pronunciation notes from language practice |
| `project/android-app` | Android app idea for Harker's Archive |
| `project/home-server` | Home server stack (Immich, Calibre, Paperless, etc.) |
| `social/date` | Dates and romantic outings |
| `social/forro` | Forró dancing and social nights |
| `social/family` | Family dynamics (Das Dores, Bubu, parents) |
| `health/therapy` | Therapy reminders and session topics |
| `health/grief` | Grief processing around socorro's illness and death |

## Candidate tags (promote when recurring)

Introduce only when at least two entries need the tag, or one entry is a clear recurring search path:

- `work/shipt` — Shipt/Amazon same-day delivery client work
- `work/beauty` — Beauty client QA
- `social/mossoro` — Trip and family time in Mossoró

## Book material: three tag types

Do not collapse these:

1. **`reading/progress`** — chapter/page markers only
2. **`reading/summary`** — your paraphrase of plot or ideas
3. **`quote/book`** — memorable lines read aloud or typed from the book

Add `reading/twelve-kings` (or book slug) alongside progress/summary/quote when the work is identifiable.

## Transcription normalization

Map ASR drift to stable identities in tags and weekly prose:

| Raw ASR variants | Normalized |
|------------------|------------|
| Sharakai, Characals, Charikai, Cherokee, Shirk Eye, Reading Long/Lungs | *Twelve Kings in Sharakai* (Bradley P. Beaulieu) |
| dedo de diário | nota de diário |
| Exist de leitura / Reading lungs | Registro de leitura / Reading log |
| Ariete | Ariat |
| grocery clients | Kroger clients |

Rules:

- Use normalized names in weekly prose and tags
- Keep raw spelling in the source index when it aids provenance
- Do not present uncertain Whisper quotes as verbatim; label as `passagem lembrada` or link `entry_id`

## Quality tags

Use `capture/*` to isolate noise instead of deleting entries:

- **`capture/fragment`** — "Oi", "Tw", "Querido diário," with no body
- **`capture/test`** — "Testando… gravador", hostname fragments
- **`capture/transcription-loop`** — repeated identical segments

Weekly synthesis should down-weight or omit `capture/*` entries from narrative sections; still list them in the source index.

## Tag evolution rules

1. **Prefer broad tags first** — use `work` before `work/kroger` until Kroger notes are hard to browse under `work` alone
2. **Promote on recurrence** — two or more entries in a week, or three+ across weeks
3. **Never rename silently** — add an alias note in this file when splitting or merging tags
4. **Document new tags** — append to "Candidate tags" or promote to canonical with one-line definition
5. **Contradictions stay** — if one day says "productive" and another "did nothing", keep both; synthesis may note the tension
6. **Audit previous notes** — when adding, promoting, splitting, merging, or renaming a tag, search existing `rainfields_mind/weekly/*.md` files and update prior source-index rows/frontmatter where the new tag also applies
7. **Keep the vocabulary English** — do not introduce Portuguese tag labels; translate the concept into a stable English tag

## Alias log

| Date | Change |
|------|--------|
| 2026-06-26 | Initial vocabulary from dossier corpus May 24 – Jun 21 |
| 2026-06-26 | Promoted 20 candidate tags to canonical after full-corpus reconstruction (W21–W25) |
