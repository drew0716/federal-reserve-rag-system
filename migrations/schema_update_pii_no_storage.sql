-- Schema update: Remove PII storage capability
-- This ensures original queries with PII are NEVER stored in the database

-- Drop the original_query_text column (it should never be used)
ALTER TABLE queries DROP COLUMN IF EXISTS original_query_text;

-- Update comment on query_text to clarify it's always redacted if PII present
COMMENT ON COLUMN queries.query_text IS 'Query text - PII is redacted before storage if detected. Original query with PII is NEVER stored.';

-- Drop the PII access log table (no longer needed since we don't store originals)
DROP TABLE IF EXISTS pii_access_log;

-- Add constraint to ensure we're tracking redactions properly
-- (has_pii should be true if redaction_count > 0)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'queries_pii_tracking_check'
    ) THEN
        ALTER TABLE queries
        ADD CONSTRAINT queries_pii_tracking_check
        CHECK (
            (has_pii = FALSE AND redaction_count = 0) OR
            (has_pii = TRUE AND redaction_count > 0)
        );
    END IF;
END $$;

COMMENT ON CONSTRAINT queries_pii_tracking_check ON queries IS 'Ensures PII tracking is consistent: if has_pii is true, there must be redactions';
