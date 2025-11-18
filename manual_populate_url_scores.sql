-- Manual population of URL scores from existing feedback
-- This fixes the duplicate row issue by using DISTINCT

-- Step 1: Check what data we have to work with
SELECT
    'Total feedback' as metric,
    COUNT(*)::text as count
FROM feedback
UNION ALL
SELECT
    'Feedback with documents',
    COUNT(DISTINCT f.id)::text
FROM feedback f
JOIN responses r ON f.response_id = r.id
WHERE r.retrieved_doc_ids IS NOT NULL
UNION ALL
SELECT
    'Documents with source_url',
    COUNT(*)::text
FROM documents
WHERE source_url IS NOT NULL AND source_url != ''
UNION ALL
SELECT
    'Unique URLs that will get scores',
    COUNT(DISTINCT d.source_url)::text
FROM responses r
JOIN feedback f ON f.response_id = r.id
JOIN documents d ON d.id = ANY(r.retrieved_doc_ids)
WHERE d.source_url IS NOT NULL AND d.source_url != '';

-- Step 2: Preview what will be inserted (doesn't modify data)
WITH url_feedback AS (
    SELECT DISTINCT ON (d.source_url)
        d.source_url,
        d.source_type,
        AVG(f.rating) OVER (PARTITION BY d.source_url) as avg_rating,
        COUNT(f.id) OVER (PARTITION BY d.source_url) as feedback_count
    FROM responses r
    JOIN feedback f ON f.response_id = r.id
    JOIN documents d ON d.id = ANY(r.retrieved_doc_ids)
    WHERE r.retrieved_doc_ids IS NOT NULL
        AND d.source_url IS NOT NULL
        AND d.source_url != ''
)
SELECT
    source_url,
    source_type,
    ROUND(CAST((avg_rating - 3.0) / 2.0 AS numeric), 3) as feedback_score,
    feedback_count
FROM url_feedback
ORDER BY feedback_count DESC;

-- Step 3: Actually insert the data (uncomment to run)
-- Comment out the preview above and uncomment this section when ready:

/*
WITH url_feedback AS (
    SELECT
        d.source_url,
        d.source_type,
        AVG(f.rating) as avg_rating,
        COUNT(DISTINCT f.id) as feedback_count  -- Use DISTINCT to avoid counting duplicates
    FROM responses r
    JOIN feedback f ON f.response_id = r.id
    JOIN documents d ON d.id = ANY(r.retrieved_doc_ids)
    WHERE r.retrieved_doc_ids IS NOT NULL
        AND d.source_url IS NOT NULL
        AND d.source_url != ''
    GROUP BY d.source_url, d.source_type  -- Proper GROUP BY eliminates duplicates
)
INSERT INTO source_document_scores (
    source_url, source_type, feedback_score,
    enhanced_feedback_score, feedback_count, last_updated
)
SELECT
    source_url,
    source_type,
    COALESCE((avg_rating - 3.0) / 2.0, 0.0),
    COALESCE((avg_rating - 3.0) / 2.0, 0.0),
    feedback_count,
    CURRENT_TIMESTAMP
FROM url_feedback
ON CONFLICT (source_url) DO UPDATE
SET feedback_score = EXCLUDED.feedback_score,
    enhanced_feedback_score = EXCLUDED.enhanced_feedback_score,
    feedback_count = EXCLUDED.feedback_count,
    source_type = EXCLUDED.source_type,
    last_updated = EXCLUDED.last_updated;

-- Verify results
SELECT
    source_url,
    feedback_score,
    enhanced_feedback_score,
    feedback_count,
    last_updated
FROM source_document_scores
ORDER BY feedback_count DESC;
*/
