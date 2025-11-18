-- Add category column to queries table
-- This allows tracking of query topics for better analytics

ALTER TABLE queries
ADD COLUMN IF NOT EXISTS category VARCHAR(100);

-- Create index for category lookups
CREATE INDEX IF NOT EXISTS idx_queries_category ON queries(category);

-- Common categories for Federal Reserve queries:
-- - Interest Rates & Monetary Policy
-- - Banking System & Supervision
-- - Currency & Coin
-- - Employment & Economy
-- - Financial Stability
-- - Payment Systems
-- - Consumer Protection
-- - Federal Reserve Structure
-- - Complaints & Reporting
-- - Other
