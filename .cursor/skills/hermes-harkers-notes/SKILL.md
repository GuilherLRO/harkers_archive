---
name: hermes-harkers-notes
description: >-
  Explore Guilherme's personal Harker's Archive notes via the Postgres `harkers`
  database (Quincey's Dispatch) over Tailscale, sync a Markdown cache under
  /workspace/notes, and answer questions with cited entry_id / day / week
  evidence. Use when Hermes (or any agent) should read the journal, dossier,
  weekly Rainfields notes, search personal notes, or refresh the shared
  workspace notes folder.
---

# Hermes ↔ Harker's Notes

Personal journal lives on **g-server** (Tailscale). Files on the archive host
are source of truth; Postgres DB `harkers` is the cross-server contract;
`/workspace/notes` is a **cache** for file-oriented tools.

## Non-negotiables

- **Read-only** against `harkers`. Never `INSERT`/`UPDATE`/`DELETE` journal tables.
- Prefer **retrieval then reason** — do not dump the whole archive into context.
- Cite evidence with `entry_id`, `day`, and/or weekly `doc_key` (e.g. `2026-W36`).
- Write Hermes-derived analysis only under `/workspace/hermes/` (never as canonical notes).
- Notes mix **Portuguese and English**; voice transcripts are approximate.

## Connection (Tailscale)

Archive host MagicDNS: `g-server` (`100.98.225.45`).

```bash
# Required on Hermes host (read-only role — see scripts/ensure_hermes_reader.sql)
export HARKERS_DATABASE_URL='postgresql://hermes_reader:PASSWORD@g-server:5432/harkers'
```

Test:

```bash
psql "$HARKERS_DATABASE_URL" -c "SELECT count(*) FROM entries; SELECT max(synced_at) FROM documents;"
```

If connection fails: confirm Tailscale is up on both machines, Postgres listens on
Tailscale, and `pg_hba.conf` allows `100.64.0.0/10` for `hermes_reader`.

## Workspace layout

```text
/workspace/
├── notes/                 # cache materialized from DB (sync script owns this tree)
│   ├── dossier/YYYY-MM-DD.md
│   ├── weekly/YYYY-Wnn.md
│   └── .sync_manifest.json
└── hermes/                # agent outputs only (analyses, answers, drafts)
```

Refresh cache before a heavy session:

```bash
python scripts/sync_workspace_notes.py --out /workspace/notes
```

Details: [reference.md](reference.md).

## Answer workflow

Copy and track:

```text
Notes Q&A:
- [ ] 1. Check freshness (max synced_at)
- [ ] 2. Refresh /workspace/notes if stale or missing
- [ ] 3. Retrieve (weekly overview and/or search entries)
- [ ] 4. Pull cited days/entries only
- [ ] 5. Answer with citations
- [ ] 6. Optionally save write-up under /workspace/hermes/
```

### 1. Freshness

```sql
SELECT
  (SELECT max(synced_at) FROM documents) AS docs_synced,
  (SELECT max(synced_at) FROM entries) AS entries_synced,
  (SELECT count(*) FROM entries) AS entry_count;
```

Treat `synced_at` as last Quincey's Dispatch — not live Telegram.

### 2. Retrieve (pick tools)

| Question type | Start with |
|---|---|
| “What was I focused on this week / lately?” | `documents` where `kind='weekly'` |
| “What did I say about X?” | `entries.body` search (`ILIKE` / later `pg_trgm`) |
| “What happened on date D?” | `documents` dossier day + `entries` for that `day` |
| “Expand on this weekly bullet” | follow `entry_id`s mentioned in weekly body |

Default limits: **20 entries**, **4 weekly docs**, **7 dossier days** unless the user asks for more.

### 3. Answer format

```markdown
## Answer
[Direct answer in the user's language]

## Evidence
- `entry_id` `YYYY-MM-DD` — short quote or paraphrase
- weekly `YYYY-Wnn` — theme / summary point

## Freshness
DB last synced: [synced_at]. Gaps: [anything missing / uncertain].
```

## Schema (short)

**`documents`**: `(kind, doc_key)` PK — `kind` in (`dossier`,`weekly`); `body_md`, `frontmatter` jsonb, `content_hash`, `synced_at`.

**`entries`**: `entry_id` PK — `day`, `moment`, `source_type`, `body`, `segments` jsonb, `content_hash`, `synced_at`.

Full SQL recipes: [reference.md](reference.md).

## Scripts

| Script | Purpose |
|---|---|
| [scripts/ensure_hermes_reader.sql](scripts/ensure_hermes_reader.sql) | One-time: create read-only role on archive Postgres |
| [scripts/sync_workspace_notes.py](scripts/sync_workspace_notes.py) | Materialize/update `/workspace/notes` from DB |

## Anti-patterns

- Opening `5432` to the public internet (use Tailscale only)
- Giving Hermes the `guilherme` superuser password
- Treating `/workspace/notes` as editable source of truth
- Answering without citations when evidence exists in DB
- Loading all entries “just in case”
