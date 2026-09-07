-- Runs once, when the data directory is first created.
--
-- pgvector backs the embedding-based topic matching in Phase 5 (ADR-0013).
-- Creating the extension here rather than in a migration means a fresh
-- developer database is never missing it, and migrations can assume it exists.
CREATE EXTENSION IF NOT EXISTS vector;

-- gen_random_uuid() for the UUID primary keys in DATA_MODEL §4.
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Fuzzy text matching, used by the case and investigation search in the admin
-- console (UX_SPEC §12).
CREATE EXTENSION IF NOT EXISTS pg_trgm;
