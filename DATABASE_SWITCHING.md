# Database Switching Guide

This guide explains how to easily switch between local PostgreSQL and Supabase databases.

## Quick Start

**To use Local PostgreSQL:**
```bash
# In .env file, set:
DATABASE_MODE=local
```

**To use Supabase:**
```bash
# In .env file, set:
DATABASE_MODE=supabase
```

That's it! The application will automatically connect to the correct database.

---

## Configuration Details

### .env File Structure

```bash
# ============================================================
# DATABASE CONFIGURATION
# ============================================================
# Set to 'local' or 'supabase' to switch databases
DATABASE_MODE=local

# Local PostgreSQL Configuration
LOCAL_DB_HOST=localhost
LOCAL_DB_PORT=5433
LOCAL_DB_NAME=rag_system
LOCAL_DB_USER=rag_user
LOCAL_DB_PASSWORD=your_secure_password

# Supabase Configuration
SUPABASE_URL=postgresql://postgres.PROJECT_ID:PASSWORD@aws-0-region.pooler.supabase.com:6543/postgres
```

---

## Setting Up Each Database

### Local PostgreSQL Setup

**1. Install PostgreSQL:**
```bash
brew install postgresql@18
brew services start postgresql@18
```

**2. Create database and user:**
```bash
createdb -p 5433 rag_system
psql -p 5433 -d rag_system
```

```sql
CREATE USER rag_user WITH PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE rag_system TO rag_user;
CREATE EXTENSION IF NOT EXISTS vector;
```

**3. Run schema files:**
```bash
psql -p 5433 -U rag_user -d rag_system -f schema.sql
psql -p 5433 -U rag_user -d rag_system -f schema_update_sources.sql
psql -p 5433 -U rag_user -d rag_system -f schema_update_categories.sql
psql -p 5433 -U rag_user -d rag_system -f schema_update_feedback_analysis.sql
psql -p 5433 -U rag_user -d rag_system -f schema_update_pii_no_storage.sql
```

**4. Set DATABASE_MODE:**
```bash
# In .env
DATABASE_MODE=local
```

---

### Supabase Setup

**1. Create Supabase project:**
- Go to [supabase.com](https://supabase.com)
- Click "New Project"
- Choose a name, password, and region
- Wait 2-3 minutes for provisioning

**2. Get connection string:**
- Go to **Settings** → **Database**
- Click **Connection string** section
- Select **Transaction** tab (uses port 6543, **NOT** Session mode)
- Copy the connection string

Example format:
```
postgresql://postgres.PROJECT_ID:YOUR_PASSWORD@aws-0-region.pooler.supabase.com:6543/postgres
```

**3. Run schema in Supabase SQL Editor:**

The `supabase_setup.sql` file contains the complete database schema for Supabase.

- Go to **SQL Editor** in Supabase dashboard
- Click **New query**
- Open `supabase_setup.sql` from your project directory
- Copy **all contents** (146 lines)
- Paste into the SQL Editor
- Click **Run** or press `Cmd+Enter` (Mac) / `Ctrl+Enter` (Windows)

**What this creates:**
- `vector` extension for pgvector
- `documents` table with 384-dim embeddings
- `queries` table with PII tracking
- `responses` table
- `feedback` table with sentiment analysis fields
- `document_scores` table for ranking
- `source_refresh_log` table
- `document_review_flags` table
- All necessary indexes

**Expected output:**
```
Success. No rows returned
```

**4. Test the connection:**

Update your `.env` file first:
```bash
# Replace with your actual Supabase URL
SUPABASE_URL=postgresql://postgres.abcd1234:YourPassword@aws-1-us-east-1.pooler.supabase.com:6543/postgres

# Set mode to supabase
DATABASE_MODE=supabase
```

Then test:
```bash
python3 test_db_connection.py
```

**Expected output:**
```
=================================================
DATABASE CONNECTION TEST
=================================================
DATABASE_MODE: supabase
Database Mode: supabase

Connection Parameters:
  Host: aws-1-us-east-1.pooler.supabase.com
  Port: 6543
  Database: postgres
  User: postgres.abcd1234

✓ Successfully connected to Supabase database!

Database info:
  Current database: postgres
  Current user: postgres.abcd1234
  PostgreSQL version: PostgreSQL 15.x...

✓ Connection test passed!
=================================================
```

**5. Verify schema was created:**

Run this query in Supabase SQL Editor to check tables:
```sql
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY table_name;
```

**Expected tables:**
- `document_review_flags`
- `document_scores`
- `documents`
- `feedback`
- `queries`
- `responses`
- `source_refresh_log`

---

## Importing Data

### To Local Database

```bash
# Set mode to local
DATABASE_MODE=local

# Import data
python3 fed_content_importer.py
```

### To Supabase

```bash
# Set mode to supabase
DATABASE_MODE=supabase

# Import data
python3 fed_content_importer.py
```

---

## Switching Between Databases

### Scenario 1: Development on Local, Production on Supabase

**Development:**
```bash
# .env
DATABASE_MODE=local
```

**Production/Deployment:**
```bash
# .env (or environment variables in deployment platform)
DATABASE_MODE=supabase
SUPABASE_URL=your_supabase_connection_string
```

### Scenario 2: Testing with Both Databases

Keep both configurations in `.env` and just change `DATABASE_MODE`:

```bash
# Test with local
DATABASE_MODE=local
streamlit run streamlit_app.py

# Test with Supabase
DATABASE_MODE=supabase
streamlit run streamlit_app.py
```

---

## Verification

### Check which database you're connected to:

```bash
python3 test_db_connection.py
```

This will show:
- Current DATABASE_MODE
- Connection parameters
- Which database it connected to
- Database name and user

---

## Common Workflows

### Workflow 1: Develop Locally, Deploy to Supabase

1. **Develop locally:**
   ```bash
   DATABASE_MODE=local
   streamlit run streamlit_app.py
   ```

2. **When ready to deploy:**
   - Create Supabase project
   - Run `supabase_setup.sql` in Supabase SQL Editor
   - Update `.env` on deployment server:
     ```bash
     DATABASE_MODE=supabase
     SUPABASE_URL=your_supabase_url
     ```
   - Import data to Supabase:
     ```bash
     python3 fed_content_importer.py
     ```

3. **Deploy application** (Streamlit Cloud, Railway, etc.)

### Workflow 2: Mirror Databases (Same Data in Both)

1. **Set up both databases** (local + Supabase)

2. **Import to local:**
   ```bash
   DATABASE_MODE=local
   python3 fed_content_importer.py
   ```

3. **Import to Supabase:**
   ```bash
   DATABASE_MODE=supabase
   python3 fed_content_importer.py
   ```

4. **Switch between them** anytime by changing `DATABASE_MODE`

### Workflow 3: Backup Local to Supabase

1. **Use local for daily work:**
   ```bash
   DATABASE_MODE=local
   ```

2. **Periodically backup to Supabase:**
   ```bash
   # Export from local
   pg_dump -p 5433 -U rag_user rag_system > backup.sql

   # Import to Supabase via SQL Editor
   # (copy contents of backup.sql and run in Supabase)
   ```

---

## Environment-Specific Configuration

### Use Different .env Files

**For development (.env.local):**
```bash
DATABASE_MODE=local
LOCAL_DB_HOST=localhost
LOCAL_DB_PORT=5433
...
```

**For production (.env.production):**
```bash
DATABASE_MODE=supabase
SUPABASE_URL=postgresql://...
```

**Load the appropriate file:**
```bash
# Development
cp .env.local .env

# Production
cp .env.production .env
```

---

## Troubleshooting

### "SUPABASE_URL not set" Error

**Problem:** You set `DATABASE_MODE=supabase` but didn't configure `SUPABASE_URL`

**Solution:**
```bash
# Add to .env
SUPABASE_URL=postgresql://postgres.PROJECT_ID:PASSWORD@aws-0-region.pooler.supabase.com:6543/postgres
```

### Connection Fails

**Check which mode you're in:**
```bash
python3 test_db_connection.py
```

**For local issues:**
- Verify PostgreSQL is running: `brew services list`
- Check port: `pg_isready -p 5433`
- Verify credentials in `.env`

**For Supabase issues:**
- Verify project is not paused in Supabase dashboard
- Check connection string is correct (Transaction mode, port 6543)
- Verify password is correct

### Data Not Syncing Between Databases

**Important:** Local and Supabase databases are **completely separate**. Changing `DATABASE_MODE` doesn't sync data.

**To sync:**
1. Export from one database
2. Import to the other database
3. Or run `fed_content_importer.py` with each mode to import the same source data

---

## Best Practices

1. **Use local for development**
   - Faster
   - No API costs
   - Works offline
   - Easy to reset/test

2. **Use Supabase for production**
   - Accessible from anywhere
   - Automatic backups
   - Scalable
   - No local infrastructure needed

3. **Keep .env.example updated**
   - Document all required variables
   - Don't include actual credentials

4. **Use environment variables in deployment**
   - Don't commit `.env` to git
   - Set `DATABASE_MODE=supabase` and `SUPABASE_URL` in deployment platform

5. **Test with both databases**
   - Verify queries work the same
   - Check performance differences
   - Ensure import scripts work with both

---

## Quick Reference

| Task | Command |
|------|---------|
| **Switch to local** | Set `DATABASE_MODE=local` in `.env` |
| **Switch to Supabase** | Set `DATABASE_MODE=supabase` in `.env` |
| **Check connection** | `python3 test_db_connection.py` |
| **Import data** | `python3 fed_content_importer.py` |
| **Run app** | `streamlit run streamlit_app.py` |

---

## Example .env File

```bash
# Anthropic API
ANTHROPIC_API_KEY=sk-ant-...

# ============================================================
# DATABASE CONFIGURATION - Switch between 'local' and 'supabase'
# ============================================================
DATABASE_MODE=local

# Local PostgreSQL
LOCAL_DB_HOST=localhost
LOCAL_DB_PORT=5433
LOCAL_DB_NAME=rag_system
LOCAL_DB_USER=rag_user
LOCAL_DB_PASSWORD=my_password

# Supabase (get from Supabase dashboard → Transaction mode)
SUPABASE_URL=postgresql://postgres.xyz123:password@aws-1-us-east-1.pooler.supabase.com:6543/postgres

# Model Configuration
CLAUDE_MODEL=claude-sonnet-4-20250514
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
ENABLE_PII_REDACTION=true
```

---

**That's it!** You can now easily switch between local and Supabase databases by changing a single line in your `.env` file.
