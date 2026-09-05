-- Quincey's Dispatch — consumer contract for other VPS apps.
-- Source of truth remains dossier/ and rainfields_mind/weekly/ on disk.

CREATE TABLE IF NOT EXISTS documents (
    kind         TEXT NOT NULL CHECK (kind IN ('dossier', 'weekly')),
    doc_key      TEXT NOT NULL,
    path         TEXT NOT NULL,
    title        TEXT,
    frontmatter  JSONB NOT NULL DEFAULT '{}'::jsonb,
    body_md      TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    synced_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (kind, doc_key)
);

CREATE INDEX IF NOT EXISTS documents_kind_synced_at_idx
    ON documents (kind, synced_at DESC);

CREATE TABLE IF NOT EXISTS entries (
    entry_id         TEXT PRIMARY KEY,
    day              DATE NOT NULL,
    moment           TIMESTAMPTZ NOT NULL,
    source_type      TEXT NOT NULL,
    source_file      TEXT NOT NULL,
    original_source  TEXT NOT NULL DEFAULT '',
    body             TEXT NOT NULL,
    segments         JSONB NOT NULL DEFAULT '[]'::jsonb,
    content_hash     TEXT NOT NULL,
    synced_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS entries_day_moment_idx
    ON entries (day, moment);
