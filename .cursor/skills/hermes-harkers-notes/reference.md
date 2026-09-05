# Harker's DB reference (Hermes)

## Tables

### `documents`

| Column | Type | Notes |
|---|---|---|
| `kind` | text | `dossier` or `weekly` |
| `doc_key` | text | `2026-09-05` or `2026-W36` |
| `path` | text | path on archive host (informational) |
| `title` | text | from frontmatter when present |
| `frontmatter` | jsonb | weekly tags live here (`tags` array) |
| `body_md` | text | Markdown body |
| `content_hash` | text | sha256 of full file; sync key |
| `synced_at` | timestamptz | last Quincey's Dispatch upsert |

PK: `(kind, doc_key)`.

### `entries`

| Column | Type | Notes |
|---|---|---|
| `entry_id` | text | stable id from Van Helsing's Dossier |
| `day` | date | journal day |
| `moment` | timestamptz | entry timestamp |
| `source_type` | text | voice / typed, etc. |
| `source_file` | text | transcript basename |
| `original_source` | text | e.g. Telegram voice / OpenAI |
| `body` | text | plain text |
| `segments` | jsonb | timed segments when available |
| `content_hash` | text | |
| `synced_at` | timestamptz | |

## SQL recipes

### Recent weekly notes

```sql
SELECT doc_key, title, frontmatter->'tags' AS tags, left(body_md, 500) AS preview, synced_at
FROM documents
WHERE kind = 'weekly'
ORDER BY doc_key DESC
LIMIT 4;
```

### One week in full

```sql
SELECT doc_key, title, frontmatter, body_md
FROM documents
WHERE kind = 'weekly' AND doc_key = '2026-W36';
```

### Search entries

```sql
SELECT entry_id, day, moment, left(body, 240) AS preview
FROM entries
WHERE body ILIKE '%blog%'
ORDER BY moment DESC
LIMIT 20;
```

### Day dossier + entries

```sql
SELECT body_md FROM documents
WHERE kind = 'dossier' AND doc_key = '2026-09-05';

SELECT entry_id, moment, source_type, body
FROM entries
WHERE day = DATE '2026-09-05'
ORDER BY moment;
```

### Fetch by ids

```sql
SELECT entry_id, day, moment, body
FROM entries
WHERE entry_id = ANY(ARRAY['ad009393b227b1ee','22df74e4ec380ae1']);
```

### Freshness / coverage

```sql
SELECT
  (SELECT count(*) FROM documents WHERE kind = 'dossier') AS dossier_days,
  (SELECT count(*) FROM documents WHERE kind = 'weekly') AS weeks,
  (SELECT count(*) FROM entries) AS entries,
  (SELECT min(day) FROM entries) AS first_day,
  (SELECT max(day) FROM entries) AS last_day,
  (SELECT max(synced_at) FROM documents) AS docs_synced_at,
  (SELECT max(synced_at) FROM entries) AS entries_synced_at;
```

## Workspace sync behavior

`scripts/sync_workspace_notes.py`:

1. Reads all `documents` rows.
2. Writes `dossier/{doc_key}.md` and `weekly/{doc_key}.md` with YAML frontmatter + `body_md`.
3. Skips rewrite when local hash matches `content_hash`.
4. Deletes local files whose keys disappeared from DB.
5. Updates `.sync_manifest.json`.

Env: `HARKERS_DATABASE_URL` (required).

## Security notes

- Role `hermes_reader`: `CONNECT` + `SELECT` only.
- Connect via Tailscale MagicDNS `g-server`, not a public IP.
- Do not log full connection strings in Hermes chat output.
