# Quincey's Dispatch

Part of [Harker's Archive](../README.md). Companion to [Van Helsing's Dossier](../van_helsings_dossier/) and [Rainfields Mind](../rainfields_mind/): copy the compiled daily and weekly record into **Postgres** so other VPS apps can query it over SQL.

In *Dracula*, Quincey Morris is the practical courier of the circle — he carries the work forward. This module does the same for your archive: Obsidian Markdown stays the source of truth on disk; Postgres holds a derived mirror for other services.

## What it does

1. Reads daily files from `dossier/*.md` and weekly notes from `rainfields_mind/weekly/*.md`.
2. Loads structured entries from `dossier/.van_helsings_dossier_manifest.json`.
3. Upserts into database `harkers` on the shared `pgvector-db` Postgres:
   - `documents` — one row per day or week Markdown file
   - `entries` — one row per dossier `entry_id`
4. Deletes rows that no longer exist on disk (hard mirror).
5. Applies `schema.sql` automatically on first run.

## Prerequisites

| Requirement | Why |
|-------------|-----|
| **Python 3.13+** | Project dependency |
| **[uv](https://docs.astral.sh/uv/)** | Installs dependencies and runs the CLI |
| **Postgres** (`harkers` DB) | Target store on `pgvector-db` |
| **`HARKERS_DATABASE_URL`** | Connection string in the root `.env` |

## Quick start

1. Create the database once (volume already initialized):

   ```bash
   docker exec -it pgvector-db psql -U guilherme -d postgres \
     -c "CREATE DATABASE harkers OWNER guilherme;"
   ```

2. From the [monorepo root](../README.md):

   ```bash
   uv sync --all-packages
   ```

3. Set in the root `.env`:

   ```bash
   HARKERS_DATABASE_URL=postgresql://guilherme:postgui123@localhost:5432/harkers
   ```

4. Run a sync:

   ```bash
   cd quinceys_dispatch
   uv run python sync.py --json-summary
   ```

## Configuration

| Variable | Required | Description |
|----------|----------|-------------|
| `HARKERS_DATABASE_URL` | Yes | Postgres URL for database `harkers` |
| `HARKERS_DOSSIER_DIR` | No | Override dossier folder |
| `HARKERS_RAINFIELDS_DIR` | No | Override Rainfields Mind root |
| `QUINCEYS_DISPATCH_ENABLED` | No | When `true`, `helsings_round.py` runs this after Rainfields (default `false`) |

CLI flags override directory defaults:

```bash
uv run python sync.py \
  --dossier-dir ../dossier \
  --rainfields-dir ../rainfields_mind \
  --json-summary
```

## Consumer queries

```sql
SELECT day, moment, body FROM entries
WHERE body ILIKE '%blog%' ORDER BY moment DESC LIMIT 20;

SELECT body_md FROM documents
WHERE kind = 'weekly' AND doc_key = '2026-W36';
```

## Coordinator

When `helsings_round.py` is running and `QUINCEYS_DISPATCH_ENABLED=true`, Quincey's Dispatch runs after each Rainfields pass. Failures are logged and do not stop the Telegram bot: connection errors, timeouts, and per-row upsert failures are soft-failed (one bad file does not roll back the rest).
