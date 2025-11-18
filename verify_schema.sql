-- Quick verification that schema update worked

-- 1. Check if source_document_scores table exists
SELECT
    CASE
        WHEN EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_name = 'source_document_scores'
        )
        THEN '✅ source_document_scores table EXISTS'
        ELSE '❌ source_document_scores table MISSING - run schema_update_url_scoring.sql'
    END as table_status;

-- 2. Check table structure
SELECT
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_name = 'source_document_scores'
ORDER BY ordinal_position;

-- 3. Check indexes
SELECT
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename = 'source_document_scores';

-- 4. Check current data
SELECT COUNT(*) as current_row_count FROM source_document_scores;

-- 5. Sample any existing data
SELECT * FROM source_document_scores LIMIT 5;
