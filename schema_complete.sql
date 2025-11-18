-- Complete Schema for Federal Reserve RAG System (Local PostgreSQL)
-- This is the consolidated schema for fresh installations
-- For existing database migrations, see files in migrations/ folder

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Documents table for knowledge base
CREATE TABLE IF NOT EXISTS documents (
    id SERIAL PRIMARY KEY,
    content TEXT NOT NULL,
    embedding vector(384),  -- Dimension for all-MiniLM-L6-v2
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    source_type VARCHAR(50) DEFAULT 'user_uploaded',
    source_url TEXT,
    source_title TEXT,
    last_refreshed TIMESTAMP,
    is_external_source BOOLEAN DEFAULT FALSE,
    is_flagged BOOLEAN DEFAULT FALSE
);

-- Queries table
CREATE TABLE IF NOT EXISTS queries (
    id SERIAL PRIMARY KEY,
    query_text TEXT NOT NULL,
    query_embedding vector(384),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    category VARCHAR(100),
    has_pii BOOLEAN DEFAULT FALSE,
    redaction_count INTEGER DEFAULT 0,
    redaction_details JSONB
);

-- Responses table
CREATE TABLE IF NOT EXISTS responses (
    id SERIAL PRIMARY KEY,
    query_id INTEGER REFERENCES queries(id) ON DELETE CASCADE,
    response_text TEXT NOT NULL,
    model_version TEXT DEFAULT 'claude-sonnet-4-20250514',
    retrieved_doc_ids INTEGER[],
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    document_ids INTEGER[]
);

-- Feedback table
CREATE TABLE IF NOT EXISTS feedback (
    id SERIAL PRIMARY KEY,
    response_id INTEGER REFERENCES responses(id) ON DELETE CASCADE,
    query_id INTEGER REFERENCES queries(id) ON DELETE CASCADE,
    document_id INTEGER REFERENCES documents(id) ON DELETE SET NULL,
    rating INTEGER CHECK (rating >= 1 AND rating <= 5),
    comment TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    sentiment VARCHAR(20),
    confidence FLOAT,
    issues TEXT[],
    severity VARCHAR(20),
    summary TEXT,
    enhanced_feedback_score FLOAT DEFAULT 0.0
);

-- Document scores for reranking (DEPRECATED - kept for backward compatibility)
-- Use source_document_scores for new implementations
CREATE TABLE IF NOT EXISTS document_scores (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
    base_score FLOAT DEFAULT 1.0,
    feedback_score FLOAT DEFAULT 0.0,
    enhanced_feedback_score FLOAT DEFAULT 0.0,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(document_id)
);

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

-- Source refresh log table
CREATE TABLE IF NOT EXISTS source_refresh_log (
    id SERIAL PRIMARY KEY,
    source_type VARCHAR(50) NOT NULL,
    documents_added INTEGER DEFAULT 0,
    documents_updated INTEGER DEFAULT 0,
    documents_deleted INTEGER DEFAULT 0,
    refresh_started TIMESTAMP NOT NULL,
    refresh_completed TIMESTAMP,
    status VARCHAR(20) DEFAULT 'in_progress',
    error_message TEXT,
    CONSTRAINT valid_status CHECK (status IN ('in_progress', 'completed', 'failed'))
);

-- Document review flags table
CREATE TABLE IF NOT EXISTS document_review_flags (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
    flagged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    reason TEXT NOT NULL,
    common_issues JSONB,
    severity_distribution JSONB,
    total_feedbacks INTEGER DEFAULT 0,
    status VARCHAR(20) DEFAULT 'pending',
    reviewed_at TIMESTAMP,
    reviewer_notes TEXT,
    is_flagged BOOLEAN DEFAULT TRUE,
    UNIQUE(document_id)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_documents_embedding ON documents USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX IF NOT EXISTS idx_queries_embedding ON queries USING ivfflat (query_embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX IF NOT EXISTS idx_responses_query_id ON responses(query_id);
CREATE INDEX IF NOT EXISTS idx_feedback_response_id ON feedback(response_id);
CREATE INDEX IF NOT EXISTS idx_feedback_query_id ON feedback(query_id);
CREATE INDEX IF NOT EXISTS idx_feedback_document_id ON feedback(document_id);
CREATE INDEX IF NOT EXISTS idx_document_scores_document_id ON document_scores(document_id);
CREATE INDEX IF NOT EXISTS idx_source_document_scores_url ON source_document_scores(source_url);
CREATE INDEX IF NOT EXISTS idx_source_document_scores_type ON source_document_scores(source_type);
CREATE INDEX IF NOT EXISTS idx_documents_source_url ON documents(source_url);
CREATE INDEX IF NOT EXISTS idx_documents_source_type ON documents(source_type);
CREATE INDEX IF NOT EXISTS idx_documents_external ON documents(is_external_source);
CREATE INDEX IF NOT EXISTS idx_documents_refreshed ON documents(last_refreshed);
CREATE INDEX IF NOT EXISTS idx_queries_category ON queries(category);
CREATE INDEX IF NOT EXISTS idx_queries_created_at ON queries(created_at);
CREATE INDEX IF NOT EXISTS idx_refresh_log_source ON source_refresh_log(source_type);
CREATE INDEX IF NOT EXISTS idx_refresh_log_status ON source_refresh_log(status);
CREATE INDEX IF NOT EXISTS idx_document_review_status ON document_review_flags(status) WHERE status = 'pending';
CREATE INDEX IF NOT EXISTS idx_document_review_document_id ON document_review_flags(document_id);
CREATE INDEX IF NOT EXISTS idx_documents_flagged ON documents(is_flagged) WHERE is_flagged = TRUE;

-- Add constraint for PII tracking
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

-- Comments for documentation
COMMENT ON COLUMN documents.source_type IS 'Type of source: user_uploaded, faq, press_release, about_fed, etc.';
COMMENT ON COLUMN documents.is_external_source IS 'True if document comes from automated crawling/refresh';
COMMENT ON COLUMN documents.last_refreshed IS 'When the document was last updated from its source';
COMMENT ON TABLE source_refresh_log IS 'Tracks history of automatic source document refreshes';
COMMENT ON COLUMN queries.query_text IS 'Query text - PII is redacted before storage if detected. Original query with PII is NEVER stored.';
COMMENT ON CONSTRAINT queries_pii_tracking_check ON queries IS 'Ensures PII tracking is consistent: if has_pii is true, there must be redactions';
COMMENT ON COLUMN feedback.enhanced_feedback_score IS 'Enhanced score combining rating and sentiment analysis';
COMMENT ON TABLE document_review_flags IS 'Tracks documents flagged for review based on feedback patterns';
COMMENT ON TABLE source_document_scores IS 'URL-level scores that persist across data refreshes - applied to all chunks from same source URL';
