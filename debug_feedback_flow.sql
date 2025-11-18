-- Debug: Track what happens when feedback is submitted

-- Step 1: Check current state
SELECT
    'Current URL scores' as check_point,
    COUNT(*) as count,
    MAX(last_updated) as most_recent_update
FROM source_document_scores;

-- Step 2: Check recent feedback submissions
SELECT
    'Recent feedback' as check_point,
    COUNT(*) as count,
    MAX(created_at) as most_recent_feedback
FROM feedback;

-- Step 3: Check if new feedback is linked to documents with URLs
SELECT
    f.id as feedback_id,
    f.created_at as feedback_time,
    f.rating,
    r.id as response_id,
    array_length(r.retrieved_doc_ids, 1) as doc_count,
    string_agg(DISTINCT d.source_url, ', ') as urls
FROM feedback f
JOIN responses r ON f.response_id = r.id
LEFT JOIN documents d ON d.id = ANY(r.retrieved_doc_ids)
WHERE f.created_at > NOW() - INTERVAL '1 hour'
GROUP BY f.id, f.created_at, f.rating, r.id, r.retrieved_doc_ids
ORDER BY f.created_at DESC
LIMIT 5;

-- Step 4: What would the score calculation query produce right now?
WITH url_feedback AS (
    SELECT
        d.source_url,
        MAX(d.source_type) as source_type,
        AVG(f.rating) as avg_rating,
        COUNT(DISTINCT f.id) as feedback_count,
        MAX(f.created_at) as latest_feedback
    FROM responses r
    JOIN feedback f ON f.response_id = r.id
    JOIN documents d ON d.id = ANY(r.retrieved_doc_ids)
    WHERE r.retrieved_doc_ids IS NOT NULL
        AND d.source_url IS NOT NULL
        AND d.source_url != ''
    GROUP BY d.source_url
)
SELECT
    uf.source_url,
    uf.feedback_count,
    uf.latest_feedback,
    sds.feedback_count as current_count_in_table,
    sds.last_updated as table_last_updated,
    CASE
        WHEN uf.latest_feedback > sds.last_updated THEN '⚠️ FEEDBACK NEWER THAN TABLE'
        WHEN sds.last_updated IS NULL THEN '⚠️ NOT IN TABLE YET'
        ELSE '✅ Table is up to date'
    END as sync_status
FROM url_feedback uf
LEFT JOIN source_document_scores sds ON uf.source_url = sds.source_url
ORDER BY uf.latest_feedback DESC;
