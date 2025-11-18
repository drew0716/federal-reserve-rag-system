# Upgrade Guide: URL-Level Scoring

This guide helps you upgrade from chunk-level to URL-level scoring to preserve learning across data refreshes.

## What Changed?

**Before:** Chunk-level scoring
- Scores stored per document chunk
- CASCADE deleted when documents refreshed
- ❌ Learning lost on every refresh

**After:** URL-level scoring
- Scores stored per source URL
- Independent of document lifecycle
- ✅ Learning persists across refreshes

## Quick Start

### 1. Update Database Schema

For **local database**:
```bash
psql -h localhost -p 5433 -U rag_user -d rag_system -f schema_update_url_scoring.sql
```

For **Supabase**:
```bash
# Option 1: Run via psql
psql "$SUPABASE_URL" -f schema_update_url_scoring.sql

# Option 2: Copy/paste into Supabase SQL Editor
# 1. Open Supabase dashboard → SQL Editor
# 2. Copy contents of schema_update_url_scoring.sql
# 3. Paste and run
```

### 2. Migrate Existing Data (Optional)

If you have existing feedback and scores to preserve:
```bash
python migrations/migrate_to_url_scores.py
```

**Output:**
```
================================================================================
Migration: Chunk-level scores → URL-level scores
================================================================================

Step 1: Checking database schema...
  ✅ source_document_scores table exists

Step 2: Analyzing existing data...
  Found 247 chunk-level scores
  Will create scores for 45 unique URLs

Step 3: Migrating chunk-level scores to URL-level...
  ✅ Migrated 45 URL-level scores

Step 4: Verifying migration...

  Sample of migrated URL scores:
  ----------------------------------------------------------------------------
  URL: https://federalreserve.gov/aboutthefed/mission.htm
    Type: fed_about
    Feedback Score: 0.450
    Enhanced Score: 0.520
    Based on 8 chunks

================================================================================
✅ Migration completed successfully!
================================================================================
```

### 3. Verify Everything Works

Test a query to ensure URL-level scoring is working:
```bash
# In your application or Python REPL
from database import Database
import numpy as np

db = Database()
with db:
    # This should now use URL-level scores
    test_embedding = np.random.rand(384)  # Replace with real embedding
    results = db.search_similar_documents(test_embedding, top_k=5)

    # Check that results include URL-level score fields
    if results:
        print(f"✅ URL-level scoring active")
        print(f"   Sample result has feedback_score: {results[0].get('feedback_score', 'N/A')}")
```

### 4. Test Data Refresh

Verify that scores persist across refresh:

```bash
# 1. Note current scores
psql $DATABASE_URL -c "SELECT source_url, enhanced_feedback_score FROM source_document_scores LIMIT 5;"

# 2. Refresh data
python fed_content_importer.py --crawl

# 3. Check scores still exist
psql $DATABASE_URL -c "SELECT source_url, enhanced_feedback_score FROM source_document_scores LIMIT 5;"

# ✅ Scores should be identical!
```

## What Files Changed?

### New Files
- `URL_SCORING.md` - Complete documentation
- `UPGRADE_URL_SCORING.md` - This guide
- `schema_update_url_scoring.sql` - Schema migration
- `migrations/migrate_to_url_scores.py` - Data migration script

### Modified Files
- `supabase_setup.sql` - Added source_document_scores table
- `database.py` - Added calculate_source_document_scores(), updated search
- `rag_system.py` - Updated rerank_documents() to use URL scores
- `streamlit_app.py` - Updated UI to show URL score deletion

## Configuration

### Enable/Disable URL Scoring

URL-level scoring is **enabled by default**. To use legacy chunk-level:

```python
# In database.py or your code
results = db.search_similar_documents(
    query_embedding,
    use_url_scores=False  # Use legacy chunk-level (not recommended)
)
```

### Adjust Feedback Weight

Control how much learned scores affect ranking:

```bash
# In .env file
FEEDBACK_WEIGHT=0.3  # Default (30% weight to learned scores)

# Higher = more learning influence
FEEDBACK_WEIGHT=0.5  # 50% weight to learned scores

# Lower = more similarity influence
FEEDBACK_WEIGHT=0.1  # 10% weight to learned scores
```

## Rollback (If Needed)

If you need to rollback:

```sql
-- Remove URL-level scoring table
DROP TABLE IF EXISTS source_document_scores;

-- System will fallback to chunk-level scoring
```

**Note:** You'll need to change code defaults:
```python
# In database.py search_similar_documents()
use_url_scores: bool = False  # Change default back to False
```

## Troubleshooting

### "Table source_document_scores does not exist"
**Solution:** Run schema update first:
```bash
psql $DATABASE_URL -f schema_update_url_scoring.sql
```

### "No URL-based documents found"
**Cause:** Documents don't have source_url populated

**Solution:**
1. Check your documents: `SELECT COUNT(*) FROM documents WHERE source_url IS NOT NULL;`
2. If zero, your documents need source_url field populated
3. Re-import with fed_content_importer.py

### Scores seem random/wrong
**Cause:** Not enough feedback data

**Solution:**
1. Submit more feedback (need 3-5 ratings per URL minimum)
2. Run score recalculation:
```python
from rag_system import RAGSystem
from database import Database

rag = RAGSystem(Database())
rag.rerank_documents(use_enhanced_scores=True)
```

### Migration script fails
**Check:**
1. Schema update completed: `SELECT * FROM source_document_scores LIMIT 1;`
2. Database permissions: Can you INSERT/UPDATE?
3. Documents have source_url: `SELECT source_url FROM documents WHERE source_url IS NOT NULL LIMIT 1;`

## Verification Checklist

After upgrade, verify:

- [ ] Schema update applied successfully
- [ ] Migration script ran without errors
- [ ] URL scores exist in database
- [ ] Search results include URL-level scores
- [ ] Data refresh preserves scores
- [ ] Feedback updates URL scores
- [ ] Delete all data clears URL scores

## Performance Notes

### Query Performance
URL-level scoring may be **slightly faster** than chunk-level because:
- Fewer joins (no document_scores join needed per chunk)
- Single score lookup per URL (not per chunk)
- Better index usage

### Storage
Minimal storage increase:
- ~1KB per unique URL (vs per chunk)
- For 1000 URLs: ~1MB total
- Much less than chunk-level scores

## Support

Questions? Issues?
1. Check `URL_SCORING.md` for detailed documentation
2. Review error messages from migration script
3. Check database logs for SQL errors
4. Open GitHub issue with error details

## Next Steps

After upgrading:

1. ✅ **Test thoroughly** - Run queries, check scores
2. ✅ **Monitor performance** - Watch query times, score accuracy
3. ✅ **Submit feedback** - Build up URL-level scores
4. ✅ **Refresh data** - Verify scores persist
5. ✅ **Review analytics** - Check top/bottom scoring URLs

---

**Congratulations!** Your RAG system now preserves learning across data refreshes. 🎉
