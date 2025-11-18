# URL-Level Scoring Deployment Checklist

Quick reference for deploying to Streamlit Cloud with Supabase.

## 🚀 Quick Deployment Steps

### □ Step 1: Update Supabase Schema (5 minutes)

1. Open https://supabase.com/dashboard
2. Select your project → SQL Editor → New Query
3. Copy/paste contents of `schema_update_url_scoring.sql`
4. Click "Run"
5. Verify: See ✅ success message
6. Confirm: Check "Table Editor" → `source_document_scores` exists

### □ Step 2: Migrate Existing Data (Optional, 2 minutes)

**Choose ONE option:**

**Option A: Run Locally** (if you have existing feedback to preserve)
```bash
# Add to .env:
DATABASE_MODE=supabase
SUPABASE_URL=postgresql://postgres:[PASSWORD]@[HOST]:6543/postgres

# Run migration:
python migrate_to_url_scores.py
```

**Option B: Skip Migration** (if starting fresh)
- New feedback will create URL scores automatically
- Old chunk scores stay but won't be used

### □ Step 3: Deploy to Streamlit (1 minute)

```bash
git add .
git commit -m "Add URL-level scoring"
git push origin main
```

Streamlit Cloud will auto-deploy (or click "Reboot app" in dashboard)

### □ Step 4: Verify (5 minutes)

**Test 1: Check Table**
- Supabase → SQL Editor:
  ```sql
  SELECT COUNT(*) FROM source_document_scores;
  ```

**Test 2: Submit Feedback**
- Ask question in app
- Rate response
- Check Supabase:
  ```sql
  SELECT * FROM source_document_scores ORDER BY last_updated DESC LIMIT 1;
  ```
- Should see new/updated score

**Test 3: Critical Test - Verify Persistence**
1. Note a URL score:
   ```sql
   SELECT source_url, enhanced_feedback_score FROM source_document_scores LIMIT 1;
   ```
2. Refresh source data in app
3. Check score again - should be UNCHANGED ✅

---

## 📋 Pre-Deployment Checklist

- [ ] Access to Supabase dashboard
- [ ] Access to Streamlit Cloud dashboard
- [ ] Git repository is clean (`git status`)
- [ ] All tests passing locally
- [ ] Backup created (optional but recommended)

## 🎯 Success Criteria

✅ No errors in Streamlit Cloud logs
✅ `source_document_scores` table exists
✅ URL scores update when feedback submitted
✅ **Scores persist after data refresh** ← KEY TEST

## 🆘 Quick Troubleshooting

| Problem | Quick Fix |
|---------|-----------|
| "Table doesn't exist" | Re-run `schema_update_url_scoring.sql` in Supabase |
| "Migration found 0 URLs" | Skip migration - scores will build from new feedback |
| App crashes | Check Streamlit logs; verify SUPABASE_URL in secrets |
| Scores disappear | Verify `use_url_scores=True` in database.py |

## 📞 Need Help?

Full instructions: See `DEPLOY_URL_SCORING.md`
Technical details: See `URL_SCORING.md`

---

**Total Time: ~15 minutes** | **Difficulty: Easy** | **Rollback: Simple** (git revert)
