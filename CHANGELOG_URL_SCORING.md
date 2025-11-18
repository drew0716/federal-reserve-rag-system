# Changelog: URL-Level Scoring Update

## Summary

Upgraded the feedback-based ranking system from chunk-level to URL-level scoring, ensuring learned rankings **persist across content refreshes**. This prevents the system from forgetting what works when documents are updated.

## What Changed

### 🔄 Core Enhancement: Persistent Learning

**Before:**
- Feedback scores stored per document chunk
- CASCADE delete when documents refreshed
- ❌ All learning lost on every refresh
- System started from scratch each time

**After:**
- Feedback scores stored per source URL
- Independent of document lifecycle
- ✅ Learning preserved across refreshes
- System gets smarter over time, never forgets

---

## Files Modified

### Schema & Database

1. **`supabase_setup.sql`**
   - Added `source_document_scores` table
   - Marked `document_scores` as deprecated
   - Added indexes for URL-based queries
   - Added documentation comments

2. **`schema_update_url_scoring.sql`** *(New)*
   - Standalone schema update file
   - Safe to run on existing databases
   - Includes migration instructions

### Core Application Logic

3. **`database.py`**
   - Added `calculate_source_document_scores()` method
   - Updated `search_similar_documents()` to use URL scores by default
   - Updated `delete_all_user_data()` to clear URL scores
   - Fixed duplicate URL handling in GROUP BY clauses

4. **`rag_system.py`**
   - Updated `submit_feedback()` to trigger URL score recalculation
   - Updated `rerank_documents()` to update both legacy and URL scores
   - Added verbose logging for debugging

5. **`streamlit_app.py`**
   - Fixed manual refresh to use direct import instead of subprocess
   - Added URL score recalculation after refresh
   - Updated "How It Works" page to explain URL-level scoring
   - Updated Data Management delete confirmation to show URL scores

### Documentation

6. **`README.md`**
   - Updated Features section - highlighted persistent learning
   - Updated Query Flow - mentioned URL-level ranking
   - Updated Database Schema - added source_document_scores table
   - Updated Content Management - explained score persistence
   - Added URL_SCORING.md to Quick Links
   - Updated installation to include new schema file

7. **`URL_SCORING.md`** *(New)*
   - Complete technical documentation
   - How it works, benefits, API reference
   - Troubleshooting guide
   - Best practices

8. **`UPGRADE_URL_SCORING.md`** *(New)*
   - Step-by-step upgrade guide
   - For existing installations
   - Includes verification steps

9. **`DEPLOY_URL_SCORING.md`** *(New)*
   - Deployment guide for Streamlit Cloud + Supabase
   - Troubleshooting for production
   - Verification checklist

10. **`DEPLOYMENT_CHECKLIST.md`** *(New)*
    - Quick reference for deployment
    - 15-minute deployment steps

### Migration & Utilities

11. **`migrate_to_url_scores.py`** *(New)*
    - Converts existing chunk scores to URL scores
    - One-time migration script
    - Includes verification

12. **`populate_url_scores_fixed.sql`** *(New)*
    - Manual SQL for populating URL scores
    - Handles duplicate URL issue

13. **`debug_feedback_flow.sql`** *(New)*
    - Diagnostic queries
    - Check sync status
    - Troubleshoot score updates

14. **`verify_schema.sql`** *(New)*
    - Verify schema update worked
    - Check table structure
    - Sample data validation

---

## Key Improvements

### 1. Persistent Learning ⭐
- Scores survive document refreshes
- Learning accumulates over time
- No need to retrain after updates

### 2. Better Data Model
- URL is natural unit for source documents
- Matches user mental model (rate articles, not chunks)
- Simpler, more intuitive

### 3. Robust to Changes
- Chunking strategy can evolve
- Documents can be re-chunked without losing scores
- More resilient architecture

### 4. Industry Best Practice
- Standard approach for production RAG systems
- Separates content management from learning
- Scales better with frequent updates

---

## Backward Compatibility

### Maintained
- ✅ Old `document_scores` table kept for compatibility
- ✅ Existing feedback data preserved
- ✅ No breaking changes to APIs
- ✅ Smooth migration path

### Default Behavior
- URL-level scoring enabled by default (`use_url_scores=True`)
- Can still use legacy chunk-level if needed
- Both scoring methods coexist

---

## Migration Path

### For New Installations
1. Run `supabase_setup.sql` (includes URL scoring table)
2. System automatically uses URL-level scoring
3. No additional steps needed

### For Existing Installations

**Local PostgreSQL:**
```bash
# 1. Update schema
psql -U rag_user -p 5433 -d rag_system -f schema_update_url_scoring.sql

# 2. Migrate existing data (optional)
python migrate_to_url_scores.py

# 3. Done!
```

**Supabase:**
```bash
# 1. Run in SQL Editor: schema_update_url_scoring.sql
# 2. Optionally run: populate_url_scores_fixed.sql
# 3. Done!
```

See `UPGRADE_URL_SCORING.md` for detailed instructions.

---

## Breaking Changes

**None.** This is a fully backward-compatible upgrade.

The system defaults to URL-level scoring but can fall back to chunk-level if needed:
```python
# Use URL scoring (default)
results = db.search_similar_documents(query_embedding, use_url_scores=True)

# Use legacy chunk scoring
results = db.search_similar_documents(query_embedding, use_url_scores=False)
```

---

## Performance Impact

### Storage
- **Minimal increase**: ~1KB per unique URL
- For 1000 URLs: ~1MB total
- Much less than chunk-level scores

### Query Performance
- **Slightly faster**: Fewer joins needed
- Single score lookup per URL vs per chunk
- Better index utilization

### Update Performance
- **Same**: Recalculation runs after each feedback
- Aggregates by URL instead of chunk
- Similar execution time

---

## Testing

### Verified On
- ✅ Local PostgreSQL 18
- ✅ Supabase (cloud PostgreSQL)
- ✅ Fresh installations
- ✅ Existing installations with migration

### Test Cases
- ✅ Schema creation
- ✅ Score calculation from feedback
- ✅ Search with URL-level scores
- ✅ Content refresh preserves scores
- ✅ Delete all data clears URL scores
- ✅ Migration from chunk to URL scores

---

## Future Enhancements

Potential improvements to consider:

1. **Time Decay**
   - Reduce weight of old feedback over time
   - Adapt to changing content quality

2. **Confidence Intervals**
   - Show uncertainty for low-feedback URLs
   - Require minimum feedback count

3. **Per-Section Scoring**
   - Score different sections within URLs
   - More granular than URL, less than chunk

4. **Auto Quality Detection**
   - Detect quality issues in new sources
   - Bootstrap scores before getting feedback

---

## Documentation Index

- **Technical Details**: `URL_SCORING.md`
- **Upgrade Guide**: `UPGRADE_URL_SCORING.md`
- **Deployment**: `DEPLOY_URL_SCORING.md`
- **Quick Start**: `DEPLOYMENT_CHECKLIST.md`
- **Migration Script**: `migrate_to_url_scores.py`
- **Diagnostics**: `debug_feedback_flow.sql`, `verify_schema.sql`

---

## Version

- **Date**: November 18, 2025
- **Version**: URL Scoring v1.0
- **Compatibility**: PostgreSQL 14+, pgvector 0.2.0+

---

**Questions?** See `URL_SCORING.md` for comprehensive documentation or `TROUBLESHOOTING` section in `UPGRADE_URL_SCORING.md`.
