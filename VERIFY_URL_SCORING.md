# Verify URL-Level Scoring is Working

Quick diagnostic guide to troubleshoot URL-level scoring in production.

## 🔍 Step-by-Step Verification

### Step 1: Verify Schema Update Applied

**Run in Supabase SQL Editor:**
```sql
-- Check if source_document_scores table exists
SELECT EXISTS (
    SELECT FROM information_schema.tables
    WHERE table_name = 'source_document_scores'
);
-- Should return: true

-- Check table structure
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'source_document_scores'
ORDER BY ordinal_position;
-- Should show: id, source_url, source_type, feedback_score, enhanced_feedback_score, feedback_count, last_updated
```

**If table doesn't exist:**
- Re-run `schema_update_url_scoring.sql` in Supabase SQL Editor
- Check for any SQL errors

---

### Step 2: Check If Documents Have source_url

**Run in Supabase SQL Editor:**
```sql
-- Check how many documents have source_url
SELECT
    COUNT(*) FILTER (WHERE source_url IS NOT NULL AND source_url != '') as with_url,
    COUNT(*) FILTER (WHERE source_url IS NULL OR source_url = '') as without_url,
    COUNT(*) as total
FROM documents;
```

**Expected result:**
- `with_url` should be > 0 (your Federal Reserve documents)
- If `with_url` = 0, your documents don't have URLs - see fix below

**If documents don't have source_url:**
```sql
-- Check what's in documents table
SELECT id, source_type, source_url, LEFT(content, 50) as preview
FROM documents
LIMIT 5;

-- If source_url is NULL, you need to re-import data
```

---

### Step 3: Check If You Have Feedback Data

**Run in Supabase SQL Editor:**
```sql
-- Check feedback exists
SELECT COUNT(*) as total_feedback FROM feedback;
-- Should be > 0 if you've submitted ratings

-- Check feedback is linked to documents with URLs
SELECT
    COUNT(DISTINCT d.source_url) as unique_urls_with_feedback
FROM feedback f
JOIN responses r ON f.response_id = r.id
JOIN documents d ON d.id = ANY(r.retrieved_doc_ids)
WHERE d.source_url IS NOT NULL AND d.source_url != '';
```

**Expected:**
- `total_feedback` > 0
- `unique_urls_with_feedback` > 0

**If no feedback:**
- Submit a rating in your app
- Re-run this query

---

### Step 4: Manually Trigger Score Calculation

**Run in Supabase SQL Editor:**
```sql
-- This is the exact query your app runs
WITH url_feedback AS (
    SELECT
        d.source_url,
        d.source_type,
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
        COUNT(f.id) as feedback_count
    FROM responses r
    JOIN feedback f ON f.response_id = r.id
    JOIN documents d ON d.id = ANY(r.retrieved_doc_ids)
    WHERE r.retrieved_doc_ids IS NOT NULL
        AND d.source_url IS NOT NULL
        AND d.source_url != ''
    GROUP BY d.source_url, d.source_type
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

-- Check results
SELECT * FROM source_document_scores;
```

**Expected:**
- Insert should succeed with N rows
- `source_document_scores` table should now have data

---

### Step 5: Verify Scores After Each Action

#### After Submitting Feedback:

**In Streamlit app:**
1. Submit a rating (1-5 stars)
2. Wait for success message

**In Supabase:**
```sql
-- Check URL scores were updated
SELECT
    source_url,
    feedback_score,
    enhanced_feedback_score,
    feedback_count,
    last_updated
FROM source_document_scores
ORDER BY last_updated DESC
LIMIT 5;
```

**Expected:**
- `last_updated` should be very recent (within last minute)
- `feedback_count` should increment with each rating

#### After Manual Refresh:

**In Streamlit app:**
1. Go to "Source Content Management"
2. Click "🔄 Refresh Now"
3. Wait for completion

**In Supabase:**
```sql
-- Scores should still exist (not deleted!)
SELECT COUNT(*) FROM source_document_scores;
-- Should be same count as before refresh

-- Check last_updated
SELECT source_url, last_updated
FROM source_document_scores
ORDER BY last_updated DESC;
-- Timestamps should be updated if refresh recalculated scores
```

---

## 🐛 Common Issues & Fixes

### Issue 1: Table doesn't exist
**Symptoms:** SQL errors about `source_document_scores`
**Fix:**
```sql
-- Run in Supabase SQL Editor
-- Copy/paste entire contents of schema_update_url_scoring.sql
```

### Issue 2: Documents don't have source_url
**Symptoms:** Query returns 0 rows, with_url = 0
**Fix:**
- Your documents were imported before `source_url` field existed
- Need to re-import Federal Reserve content
- Or manually populate `source_url` from metadata:
```sql
-- If source_url is in metadata JSONB
UPDATE documents
SET source_url = metadata->>'source_url'
WHERE source_url IS NULL
    AND metadata->>'source_url' IS NOT NULL;
```

### Issue 3: Feedback exists but no URL scores
**Symptoms:** feedback table has rows, but source_document_scores is empty
**Fix:**
- Run Step 4 manually to trigger score calculation
- Check Streamlit logs for errors when submitting feedback
- Verify documents linked to responses have source_url:
```sql
SELECT d.id, d.source_url, r.id as response_id
FROM responses r
JOIN documents d ON d.id = ANY(r.retrieved_doc_ids)
WHERE r.id IN (SELECT response_id FROM feedback)
LIMIT 10;
```

### Issue 4: Code deployed but scores not updating
**Symptoms:** Schema is fine, manual SQL works, but app doesn't update scores
**Check:**
1. Streamlit Cloud deployment succeeded (check dashboard)
2. Code changes are in your GitHub repo:
   ```bash
   git log --oneline -5
   # Should see recent commits about URL scoring
   ```
3. Check Streamlit logs for Python errors
4. Verify environment variable (if any) are set

---

## ✅ Success Checklist

- [ ] `source_document_scores` table exists in Supabase
- [ ] Documents have `source_url` populated (check with SQL)
- [ ] Feedback exists in database
- [ ] Manual SQL score calculation works
- [ ] Code changes deployed to Streamlit Cloud
- [ ] Submitting feedback creates/updates URL scores
- [ ] Manual refresh preserves URL scores
- [ ] Search results include URL-level score fields

---

## 📞 Still Not Working?

**Gather this info:**

1. **Schema check:**
   ```sql
   SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'source_document_scores');
   ```

2. **Data check:**
   ```sql
   SELECT
       (SELECT COUNT(*) FROM documents WHERE source_url IS NOT NULL) as docs_with_url,
       (SELECT COUNT(*) FROM feedback) as total_feedback,
       (SELECT COUNT(*) FROM source_document_scores) as url_scores;
   ```

3. **Streamlit logs:** Copy any Python errors from Streamlit Cloud dashboard

4. **Git status:**
   ```bash
   git log --oneline -3
   git status
   ```

Share these results and we can debug further!
