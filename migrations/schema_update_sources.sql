-- Schema update to support external source documents
-- This allows us to manage Federal Reserve content separately from user queries/responses

-- Add source tracking to documents table
ALTER TABLE documents ADD COLUMN IF NOT EXISTS source_type VARCHAR(50) DEFAULT 'user_uploaded';
ALTER TABLE documents ADD COLUMN IF NOT EXISTS source_url TEXT;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS source_title TEXT;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS last_refreshed TIMESTAMP;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS is_external_source BOOLEAN DEFAULT FALSE;

-- Create index for efficient filtering
CREATE INDEX IF NOT EXISTS idx_documents_source_type ON documents(source_type);
CREATE INDEX IF NOT EXISTS idx_documents_external ON documents(is_external_source);
CREATE INDEX IF NOT EXISTS idx_documents_refreshed ON documents(last_refreshed);

-- Create a table to track source refresh history
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

-- Create index for refresh log
CREATE INDEX IF NOT EXISTS idx_refresh_log_source ON source_refresh_log(source_type);
CREATE INDEX IF NOT EXISTS idx_refresh_log_status ON source_refresh_log(status);

-- Comment the tables
COMMENT ON COLUMN documents.source_type IS 'Type of source: user_uploaded, fed_about, fed_faq, fed_press_release, etc.';
COMMENT ON COLUMN documents.is_external_source IS 'True if document comes from automated crawling/refresh';
COMMENT ON COLUMN documents.last_refreshed IS 'When the document was last updated from its source';
COMMENT ON TABLE source_refresh_log IS 'Tracks history of automatic source document refreshes';
