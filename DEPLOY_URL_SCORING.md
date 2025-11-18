# Deploying URL-Level Scoring to Streamlit Cloud

Step-by-step guide to upgrade your deployed Streamlit app to use URL-level scoring.

## Prerequisites

- Access to your Supabase dashboard
- Access to your Streamlit Cloud dashboard
- Git repository connected to Streamlit Cloud

## Step 1: Update Supabase Database Schema

### Option A: Via Supabase SQL Editor (Recommended)

1. **Open Supabase Dashboard**
   - Go to https://supabase.com/dashboard
   - Select your project

2. **Open SQL Editor**
   - Click "SQL Editor" in left sidebar
   - Click "New query"

3. **Run Schema Update**
   - Copy the contents of `schema_update_url_scoring.sql`
   - Paste into the SQL Editor
   - Click "Run" or press `Ctrl/Cmd + Enter`

4. **Verify Success**
   You should see output:
   ```
   ✅ URL-level scoring schema update complete!

   Next steps:
   1. Run migration script: python migrate_to_url_scores.py
   2. System will automatically use URL-level scoring
   3. Scores will now persist across data refreshes
   ```

5. **Confirm Table Created**
   - Go to "Table Editor" in left sidebar
   - Look for `source_document_scores` table
   - Should have columns: id, source_url, source_type, feedback_score, etc.

### Option B: Via psql (Advanced)

If you prefer command line:

```bash
# Get your Supabase connection string from dashboard
# Project Settings → Database → Connection String → URI

psql "postgresql://postgres:[PASSWORD]@[HOST]:[PORT]/postgres" \
  -f schema_update_url_scoring.sql
```

---

## Step 2: Migrate Existing Data

You have **3 options** to run the migration:

### Option A: Run Locally with Supabase Connection (Easiest)

1. **Set Supabase credentials locally**
   ```bash
   # In your .env file
   DATABASE_MODE=supabase
   SUPABASE_URL=postgresql://postgres:[PASSWORD]@[HOST]:[PORT]/postgres
   ```

2. **Run migration script**
   ```bash
   python migrate_to_url_scores.py
   ```

3. **Verify output**
   ```
   ✅ Migrated X URL-level scores
   ```

### Option B: Add Migration to Streamlit App UI

Add a one-time migration button to your Streamlit app:

```python
# Add to streamlit_app.py in an admin section

if st.button("🔄 Run URL Scoring Migration (One-Time)"):
    try:
        from migrate_to_url_scores import migrate_to_url_scores

        with st.spinner("Migrating to URL-level scoring..."):
            success = migrate_to_url_scores()

        if success:
            st.success("✅ Migration completed!")
        else:
            st.error("❌ Migration failed - check logs")
    except Exception as e:
        st.error(f"Migration error: {e}")
```

Then:
1. Deploy the updated app
2. Click the migration button once
3. Remove the button after migration completes

### Option C: Skip Migration (Fresh Start)

If you don't have much existing feedback data:
- Skip the migration
- URL scores will build up from new feedback going forward
- Old chunk-level scores will remain but won't be used

---

## Step 3: Deploy Code to Streamlit Cloud

### Push Changes to Git

```bash
# Make sure all changes are committed
git add .
git commit -m "Add URL-level scoring to preserve learning across refreshes"
git push origin main
```

### Trigger Streamlit Deployment

**Automatic deployment:**
- Streamlit Cloud watches your repo
- Should auto-deploy after push
- Check your Streamlit Cloud dashboard

**Manual deployment:**
1. Go to https://share.streamlit.io/
2. Find your app
3. Click "⋮" menu → "Reboot app"

### Monitor Deployment

Watch the logs in Streamlit Cloud:
```
[...] Collecting packages...
[...] Building app...
✅ App is live!
```

---

## Step 4: Verify It Works

### Test 1: Check Database

In Supabase SQL Editor:
```sql
-- Verify table exists
SELECT COUNT(*) FROM source_document_scores;

-- Check sample data (if you ran migration)
SELECT * FROM source_document_scores LIMIT 5;
```

### Test 2: Submit Test Feedback

1. Go to your deployed Streamlit app
2. Ask a question
3. Rate the response (1-5 stars)
4. Check Supabase:
   ```sql
   SELECT * FROM source_document_scores ORDER BY last_updated DESC LIMIT 1;
   ```
   - Should see a new/updated URL score

### Test 3: Verify Search Uses URL Scores

Add temporary debugging to your app:

```python
# In streamlit_app.py, after search
if results:
    with st.expander("🔍 Debug: URL Scoring"):
        for i, result in enumerate(results[:3]):
            st.write(f"Result {i+1}:")
            st.write(f"  - Source URL: {result.get('source_url', 'N/A')}")
            st.write(f"  - Feedback Score: {result.get('feedback_score', 0):.3f}")
            st.write(f"  - Enhanced Score: {result.get('enhanced_feedback_score', 0):.3f}")
```

Run a query and check that results show URL-level scores.

### Test 4: Verify Persistence Across Refresh

**Critical test:**

1. **Note current scores**
   ```sql
   SELECT source_url, enhanced_feedback_score
   FROM source_document_scores
   ORDER BY source_url
   LIMIT 5;
   ```
   Save this output.

2. **Refresh source data**
   - Go to your app's "Source Content Management" page
   - Click "🔄 Refresh Now"
   - Wait for completion

3. **Check scores again**
   ```sql
   SELECT source_url, enhanced_feedback_score
   FROM source_document_scores
   ORDER BY source_url
   LIMIT 5;
   ```

4. **✅ Scores should be IDENTICAL!**
   - If same → URL scoring works! 🎉
   - If gone → Something went wrong, check below

---

## Troubleshooting

### Issue: "Table source_document_scores does not exist"

**Cause:** Schema update didn't run

**Fix:**
1. Re-run `schema_update_url_scoring.sql` in Supabase SQL Editor
2. Check for SQL errors in output
3. Verify you're connected to correct database

### Issue: "Migration found 0 URLs"

**Cause:** No feedback data yet, or documents don't have source_url

**Fix:**
1. Check if you have feedback:
   ```sql
   SELECT COUNT(*) FROM feedback;
   ```
2. Check if documents have source_url:
   ```sql
   SELECT COUNT(*) FROM documents WHERE source_url IS NOT NULL;
   ```
3. If no feedback: Skip migration, scores will build from new feedback
4. If no source_url: Re-import data with `fed_content_importer.py`

### Issue: Streamlit app crashes after deployment

**Check:**
1. Streamlit Cloud logs for Python errors
2. Missing dependencies in requirements.txt
3. Database connection (check SUPABASE_URL in secrets)

**Fix:**
```bash
# Check if database.py imports are working
# The new methods should be backward compatible
```

### Issue: Scores disappear after data refresh

**Cause:** Not using URL-level scoring

**Check:**
1. Verify `use_url_scores=True` in `search_similar_documents()` calls
2. Check that `calculate_source_document_scores()` is being called
3. Run this in Supabase:
   ```sql
   SELECT COUNT(*) FROM source_document_scores;
   -- Should be > 0 if you have feedback
   ```

---

## Rollback Plan

If something goes wrong:

### Quick Rollback

```bash
# Revert code changes
git revert HEAD
git push origin main

# Streamlit will auto-deploy previous version
```

### Database Rollback

```sql
-- Remove URL scoring table
DROP TABLE IF EXISTS source_document_scores;

-- System will fallback to chunk-level (old behavior)
```

**Note:** You'll lose URL-level scores but keep all feedback data.

---

## Post-Deployment Checklist

After successful deployment:

- [ ] Schema update applied to Supabase
- [ ] Migration script ran successfully (or skipped intentionally)
- [ ] Code deployed to Streamlit Cloud
- [ ] App loads without errors
- [ ] Can submit feedback and see URL scores update
- [ ] Data refresh preserves URL scores
- [ ] Search results include URL-level scores
- [ ] "Delete All Data" clears URL scores

---

## Performance Monitoring

### Query Performance

Before and after comparison:

```sql
-- Check query execution time
EXPLAIN ANALYZE
SELECT d.*, sds.enhanced_feedback_score
FROM documents d
LEFT JOIN source_document_scores sds ON d.source_url = sds.source_url
LIMIT 10;
```

Should be similar or faster than chunk-level joins.

### Storage Usage

Check storage increase:

```sql
-- URL scores storage
SELECT pg_size_pretty(pg_total_relation_size('source_document_scores'));

-- Should be minimal (< 1MB for typical use)
```

---

## Best Practices

### 1. Backup Before Migration

```bash
# Backup Supabase database
# Go to Supabase Dashboard → Database → Backups
# Or use pg_dump if you have access
```

### 2. Test in Staging First

If you have a staging environment:
1. Apply changes to staging Supabase first
2. Test thoroughly
3. Then apply to production

### 3. Monitor After Deployment

For first 24 hours:
- Watch Streamlit logs for errors
- Check Supabase metrics for performance issues
- Submit test queries and verify results
- Monitor user feedback

### 4. Communicate to Users

If you have active users, let them know:
- "We've upgraded the system to better remember what works"
- "Your feedback now improves results permanently"
- "No action needed - system will work even better over time"

---

## Need Help?

1. Check error messages in Streamlit Cloud logs
2. Review Supabase logs for SQL errors
3. Verify environment variables are set correctly
4. Open GitHub issue with:
   - Error messages
   - Steps to reproduce
   - Streamlit/Supabase versions

---

## Success Indicators

You know it worked when:

✅ No errors in Streamlit logs
✅ `source_document_scores` table exists in Supabase
✅ URL scores visible in search results
✅ Feedback updates URL scores immediately
✅ **Data refresh preserves learned scores** ← This is the key test!

---

**You're done!** Your production system now has persistent learning across data refreshes. 🚀
