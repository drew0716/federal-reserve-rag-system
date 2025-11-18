-- Schema Update: Add URL-Level Scoring
-- This migration adds URL-level scoring to preserve learning across data refreshes

-- URL-level document scores (preserves learning across data refreshes)
CREATE TABLE IF NOT EXISTS source_document_scores (
    id SERIAL PRIMARY KEY,
    source_url TEXT NOT NULL,
    source_type VARCHAR(50),
    feedback_score FLOAT DEFAULT 0.0,
    enhanced_feedback_score FLOAT DEFAULT 0.0,
    feedback_count INTEGER DEFAULT 0,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(source_url)
);

-- Add indexes for performance
CREATE INDEX IF NOT EXISTS idx_source_document_scores_url ON source_document_scores(source_url);
CREATE INDEX IF NOT EXISTS idx_source_document_scores_type ON source_document_scores(source_type);
CREATE INDEX IF NOT EXISTS idx_documents_source_url ON documents(source_url);

-- Add documentation
COMMENT ON TABLE source_document_scores IS 'URL-level scores that persist across data refreshes - applied to all chunks from same source URL';
COMMENT ON COLUMN source_document_scores.source_url IS 'Source URL - scores are aggregated at this level';
COMMENT ON COLUMN source_document_scores.feedback_score IS 'Simple rating-based score: (avg_rating - 3.0) / 2.0';
COMMENT ON COLUMN source_document_scores.enhanced_feedback_score IS 'Enhanced score combining rating + sentiment + severity';
COMMENT ON COLUMN source_document_scores.feedback_count IS 'Number of feedback items used to calculate this score';

-- Update document_scores table comment
COMMENT ON TABLE document_scores IS 'DEPRECATED: Chunk-level scores (kept for backward compatibility). Use source_document_scores for new implementations.';

-- Migration notice
DO $$
BEGIN
    RAISE NOTICE '✅ URL-level scoring schema update complete!';
    RAISE NOTICE '';
    RAISE NOTICE 'Next steps:';
    RAISE NOTICE '1. Run migration script: python migrate_to_url_scores.py';
    RAISE NOTICE '2. System will automatically use URL-level scoring';
    RAISE NOTICE '3. Scores will now persist across data refreshes';
    RAISE NOTICE '';
    RAISE NOTICE 'See URL_SCORING.md for full documentation';
END $$;
