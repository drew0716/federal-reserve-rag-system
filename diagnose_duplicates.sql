-- Diagnose why we're getting duplicate source_url values

-- Check 1: Are there URLs with multiple source_types?
SELECT
    source_url,
    COUNT(DISTINCT source_type) as type_count,
    array_agg(DISTINCT source_type) as types
FROM documents
WHERE source_url IS NOT NULL AND source_url != ''
GROUP BY source_url
HAVING COUNT(DISTINCT source_type) > 1;

-- If this returns rows, that's the problem!
-- The same URL appears with different source_type values

-- Check 2: What does the url_feedback CTE produce?
WITH url_feedback AS (
    SELECT
        d.source_url,
        d.source_type,
        AVG(f.rating) as avg_rating,
        COUNT(DISTINCT f.id) as feedback_count
    FROM responses r
    JOIN feedback f ON f.response_id = r.id
    JOIN documents d ON d.id = ANY(r.retrieved_doc_ids)
    WHERE r.retrieved_doc_ids IS NOT NULL
        AND d.source_url IS NOT NULL
        AND d.source_url != ''
    GROUP BY d.source_url, d.source_type
)
SELECT
    source_url,
    COUNT(*) as times_appears
FROM url_feedback
GROUP BY source_url
HAVING COUNT(*) > 1;

-- If this returns rows, those URLs appear multiple times (with different source_types)
