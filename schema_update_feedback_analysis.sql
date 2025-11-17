-- Schema update for feedback comment analysis
-- Adds columns to store AI-analyzed feedback insights

-- Add comment analysis columns to feedback table
ALTER TABLE feedback
ADD COLUMN IF NOT EXISTS sentiment_score FLOAT DEFAULT 0.0,
ADD COLUMN IF NOT EXISTS issue_types TEXT[] DEFAULT '{}',
ADD COLUMN IF NOT EXISTS severity VARCHAR(20) DEFAULT 'none',
ADD COLUMN IF NOT EXISTS needs_review BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS analysis_confidence FLOAT DEFAULT 0.0,
ADD COLUMN IF NOT EXISTS analysis_summary TEXT,
ADD COLUMN IF NOT EXISTS analyzed_at TIMESTAMP;

-- Add enhanced feedback score column to document_scores
ALTER TABLE document_scores
ADD COLUMN IF NOT EXISTS enhanced_feedback_score FLOAT DEFAULT 0.0;

-- Create index on needs_review for quick filtering
CREATE INDEX IF NOT EXISTS idx_feedback_needs_review ON feedback(needs_review) WHERE needs_review = TRUE;

-- Create index on severity for analytics
CREATE INDEX IF NOT EXISTS idx_feedback_severity ON feedback(severity);

-- Create document review flags table
CREATE TABLE IF NOT EXISTS document_review_flags (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
    flagged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    reason TEXT NOT NULL,
    common_issues JSONB,
    severity_distribution JSONB,
    total_feedbacks INTEGER DEFAULT 0,
    status VARCHAR(20) DEFAULT 'pending',  -- pending, reviewed, resolved, dismissed
    reviewed_at TIMESTAMP,
    reviewer_notes TEXT,
    UNIQUE(document_id)
);

-- Create index for pending reviews
CREATE INDEX IF NOT EXISTS idx_document_review_status ON document_review_flags(status) WHERE status = 'pending';

-- Create index for flagged documents
CREATE INDEX IF NOT EXISTS idx_document_review_document_id ON document_review_flags(document_id);

-- Comments for documentation
COMMENT ON COLUMN feedback.sentiment_score IS 'AI-analyzed sentiment from -1.0 (negative) to +1.0 (positive)';
COMMENT ON COLUMN feedback.issue_types IS 'Array of identified issues: outdated, incorrect, too_technical, etc.';
COMMENT ON COLUMN feedback.severity IS 'Issue severity: none, minor, moderate, severe';
COMMENT ON COLUMN feedback.needs_review IS 'Flag indicating document needs manual review';
COMMENT ON COLUMN feedback.analysis_confidence IS 'AI confidence in analysis (0.0-1.0)';
COMMENT ON COLUMN document_scores.enhanced_feedback_score IS 'Enhanced score combining rating and comment analysis';
COMMENT ON TABLE document_review_flags IS 'Tracks documents flagged for review based on feedback patterns';
