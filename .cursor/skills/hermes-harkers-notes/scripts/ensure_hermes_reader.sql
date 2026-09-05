-- Run once on the archive Postgres (as guilherme / superuser), then set the password.
-- Example:
--   docker exec -i pgvector-db psql -U guilherme -d harkers < ensure_hermes_reader.sql

\set ON_ERROR_STOP on

DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'hermes_reader') THEN
    CREATE ROLE hermes_reader LOGIN PASSWORD 'change-me-now';
  END IF;
END
$$;

GRANT CONNECT ON DATABASE harkers TO hermes_reader;
GRANT USAGE ON SCHEMA public TO hermes_reader;
GRANT SELECT ON TABLE documents, entries TO hermes_reader;

-- Optional: allow future tables in public to be readable by default
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT SELECT ON TABLES TO hermes_reader;

-- Reminder: set a strong password:
-- ALTER ROLE hermes_reader PASSWORD 'your-strong-password';
--
-- Ensure pg_hba.conf allows Tailscale CGNAT, e.g.:
--   host  harkers  hermes_reader  100.64.0.0/10  scram-sha-256
-- then: SELECT pg_reload_conf();
