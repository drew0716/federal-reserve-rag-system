-- Fixed version: Handles same URL with different source_types
-- Groups only by source_url, uses MAX() for source_type

WITH url_feedback AS (
    SELECT
        d.source_url,
        MAX(d.source_type) as source_type,  -- Pick one type if there are multiple
        AVG(f.rating) as avg_rating,
        AVG(
            CASE
                WHEN f.sentiment IS NOT NULL AND f.confidence > 0.3 THEN
                    0.7 * ((f.rating - 3.0) / 2.0) +
                    0.3 * (CASE f.sentiment
                        WHEN 'positive' THEN 1.0
                        WHEN 'negative' THEN -1.0
                        WHEN 'neutral' THEN 0.0
                        ELSE 0.0
                    END) * f.confidence +
                    CASE f.severity
                        WHEN 'minor' THEN -0.1
                        WHEN 'moderate' THEN -0.3
                        WHEN 'severe' THEN -0.5
                        ELSE 0.0
                    END
                ELSE
                    (f.rating - 3.0) / 2.0
            END
        ) as enhanced_score,
        COUNT(DISTINCT f.id) as feedback_count
    FROM responses r
    JOIN feedback f ON f.response_id = r.id
    JOIN documents d ON d.id = ANY(r.retrieved_doc_ids)
    WHERE r.retrieved_doc_ids IS NOT NULL
        AND d.source_url IS NOT NULL
        AND d.source_url != ''
    GROUP BY d.source_url  -- Only group by URL, not type
)
INSERT INTO source_document_scores (
    source_url, source_type, feedback_score,
    enhanced_feedback_score, feedback_count, last_updated
)
SELECT
    source_url,
    source_type,
    COALESCE((avg_rating - 3.0) / 2.0, 0.0),
    COALESCE(enhanced_score, 0.0),
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
    source_type,
    feedback_score,
    enhanced_feedback_score,
    feedback_count,
    last_updated
FROM source_document_scores
ORDER BY feedback_count DESC;
