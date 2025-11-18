# Deployment Guide

This guide covers deployment options for the Federal Reserve RAG system, with detailed instructions for PostgreSQL setup and application hosting.

## Table of Contents

1. [Deployment Architecture](#deployment-architecture)
2. [PostgreSQL Deployment Options](#postgresql-deployment-options)
3. [Application Deployment Options](#application-deployment-options)
4. [Quick Deploy Guides](#quick-deploy-guides)
5. [Environment Variables & Secrets](#environment-variables--secrets)
6. [Troubleshooting](#troubleshooting)

---

## Deployment Architecture

The system has two main components that can be deployed separately or together:

```
┌─────────────────────────────────────────────────────────┐
│                   Streamlit Application                 │
│  - streamlit_app.py                                     │
│  - rag_system.py, database.py, embeddings.py            │
│  - pii_redactor.py, feedback_analyzer.py                │
├─────────────────────────────────────────────────────────┤
│                    PostgreSQL Database                  │
│  - PostgreSQL 14+ with pgvector extension               │
│  - Stores: documents, embeddings, queries, feedback     │
└─────────────────────────────────────────────────────────┘
```

**Requirements:**
- PostgreSQL 14+ with pgvector extension
- Python 3.11+
- Anthropic API key
- 2GB+ RAM recommended
- 5GB+ disk space for embeddings

---

## PostgreSQL Deployment Options

PostgreSQL is the most critical component. Here are your options:

### Option 1: Managed PostgreSQL Services (⭐ Recommended)

#### A. **Supabase** (Free tier available, pgvector included) ⭐ **Easiest Setup**

**Pros:**
- ✅ Free tier with 500MB database
- ✅ pgvector pre-installed
- ✅ Automatic backups
- ✅ Easy setup (5 minutes)
- ✅ Web UI for database management
- ✅ No command line required for schema setup

**Setup:**

1. **Create Supabase Project**
   - Go to [supabase.com](https://supabase.com) and sign up/login
   - Click **"New Project"**
   - Choose organization, name, database password, and region
   - Click **"Create new project"**
   - Wait 2-3 minutes for provisioning

2. **Get Connection String**
   - Go to **Settings** → **Database** in Supabase dashboard
   - Scroll to **Connection string** section
   - Select **Transaction** tab (port 6543, **NOT** Session mode)
   - Copy the connection string

   Example format:
   ```
   postgresql://postgres.PROJECT_ID:YOUR_PASSWORD@aws-0-region.pooler.supabase.com:6543/postgres
   ```

3. **Run Database Schema in Web UI**
   - In Supabase dashboard, go to **SQL Editor**
   - Click **"New query"**
   - Open `supabase_setup.sql` from your project directory
   - Copy **all contents** (146 lines) and paste into SQL Editor
   - Click **Run** (or `Cmd/Ctrl + Enter`)
   - You should see: `Success. No rows returned`

4. **Verify Tables Created**

   Run this in SQL Editor:
   ```sql
   SELECT table_name FROM information_schema.tables
   WHERE table_schema = 'public' ORDER BY table_name;
   ```

   You should see 7 tables: `document_review_flags`, `document_scores`, `documents`, `feedback`, `queries`, `responses`, `source_refresh_log`

5. **Update .env:**

   ```bash
   # Database Configuration
   DATABASE_MODE=supabase
   SUPABASE_URL=postgresql://postgres.abcd1234:YOUR_PASSWORD@aws-0-region.pooler.supabase.com:6543/postgres
   ```

6. **Test Connection:**

   ```bash
   python3 test_db_connection.py
   ```

   You should see: `✓ Successfully connected to Supabase database!`

**Cost:** Free tier (500MB) → $25/month for Pro (8GB database)

**Note:** The system automatically uses the correct connection pooling mode (Transaction pooler on port 6543) which is required for pgvector operations.

---

#### B. **Neon** (Serverless PostgreSQL, Free tier)

**Pros:**
- ✅ Generous free tier (3GB storage)
- ✅ Auto-scaling
- ✅ Modern UI
- ✅ Branch databases for testing

**Setup:**

1. Create account at [neon.tech](https://neon.tech)
2. Create new project
3. Install pgvector:
   ```sql
   CREATE EXTENSION IF NOT EXISTS vector;
   ```
4. Get connection string from dashboard
5. Update `.env`:

```bash
DATABASE_URL=postgresql://[user]:[password]@[endpoint].neon.tech/neondb?sslmode=require
```

6. Run schema files (same as Supabase)

**Cost:** Free tier → $19/month for Launch plan

---

#### C. **Railway** (Simple deployment, PostgreSQL included)

**Pros:**
- ✅ Simple one-click PostgreSQL
- ✅ $5 free credit monthly
- ✅ Can deploy app + database together

**Setup:**

1. Sign up at [railway.app](https://railway.app)
2. Create new project → Add PostgreSQL
3. Install pgvector plugin:
   - Connect via Railway's psql web terminal
   - Run: `CREATE EXTENSION IF NOT EXISTS vector;`
4. Copy `DATABASE_URL` from Variables tab
5. Update `.env`
6. Run schema files

**Cost:** $5 free credit/month → Pay as you go (~$5-10/month for small apps)

---

#### D. **AWS RDS PostgreSQL**

**Pros:**
- ✅ Enterprise-grade
- ✅ High availability options
- ✅ Automatic backups
- ✅ Scalable

**Cons:**
- ⚠️ More complex setup
- ⚠️ Higher cost (~$15+/month minimum)
- ⚠️ Requires AWS knowledge

**Setup:**

1. Create RDS instance:
   - Engine: PostgreSQL 14+
   - Instance type: db.t3.micro (free tier) or db.t3.small
   - Storage: 20GB SSD (gp3)
   - Enable public access (or use VPC)
   - Security group: Allow port 5432

2. Connect and install pgvector:
```bash
psql -h your-instance.abc123.us-east-1.rds.amazonaws.com -U postgres -d postgres
```
```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

3. Connection string:
```bash
DATABASE_URL=postgresql://postgres:password@your-instance.abc123.us-east-1.rds.amazonaws.com:5432/postgres
```

**Cost:** Free tier (12 months) → $15-50/month

---

#### E. **Google Cloud SQL** or **Azure Database for PostgreSQL**

Similar to AWS RDS but with Google/Microsoft ecosystem integration.

**Setup:** Similar to AWS RDS above.

---

### Option 2: Self-Hosted PostgreSQL

#### A. **Docker Container** (Development/Testing)

**Pros:**
- ✅ Quick local setup
- ✅ Isolated environment
- ✅ Easy to reset

**docker-compose.yml:**

```yaml
version: '3.8'

services:
  postgres:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: mypassword
      POSTGRES_DB: fed_rag
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./schema_complete.sql:/docker-entrypoint-initdb.d/schema.sql

volumes:
  postgres_data:
```

**Usage:**

```bash
# Start database
docker-compose up -d

# Connection string
DATABASE_URL=postgresql://postgres:mypassword@localhost:5432/fed_rag

# Stop database
docker-compose down
```

---

#### B. **Local PostgreSQL Installation**

**macOS:**
```bash
# Install PostgreSQL 16
brew install postgresql@16

# Start service
brew services start postgresql@16

# Install pgvector
git clone https://github.com/pgvector/pgvector.git
cd pgvector
make
make install

# Create database
createdb fed_rag
psql fed_rag -c "CREATE EXTENSION vector;"
```

**Ubuntu/Debian:**
```bash
# Install PostgreSQL
sudo apt update
sudo apt install postgresql postgresql-contrib

# Install pgvector
sudo apt install postgresql-server-dev-14
git clone https://github.com/pgvector/pgvector.git
cd pgvector
make
sudo make install

# Create database
sudo -u postgres createdb fed_rag
sudo -u postgres psql fed_rag -c "CREATE EXTENSION vector;"
```

**Connection string:**
```bash
DATABASE_URL=postgresql://postgres@localhost:5432/fed_rag
```

---

## Application Deployment Options

Once PostgreSQL is set up, deploy the Streamlit application:

### Option 1: Streamlit Community Cloud (⭐ Easiest)

**Pros:**
- ✅ Free for public apps
- ✅ Automatic deployments from GitHub
- ✅ Built-in secrets management
- ✅ Zero DevOps required

**Setup:**

1. **Push code to GitHub** (if not already)
   ```bash
   git add .
   git commit -m "Prepare for deployment"
   git push origin main
   ```

2. **Deploy on Streamlit Cloud:**
   - Go to [share.streamlit.io](https://share.streamlit.io)
   - Sign in with GitHub
   - Click "New app"
   - Select your repository
   - Main file: `streamlit_app.py`
   - Click "Deploy"

3. **Add secrets** (Settings → Secrets):
   ```toml
   # .streamlit/secrets.toml format
   ANTHROPIC_API_KEY = "sk-ant-..."
   DATABASE_URL = "postgresql://user:pass@host:5432/db"
   ENABLE_PII_REDACTION = "true"
   ```

4. **App will be live at:** `https://[your-app-name].streamlit.app`

**Cost:** Free for public apps

---

### Option 2: Railway (App + Database Together)

**Pros:**
- ✅ Deploy app and database together
- ✅ Automatic HTTPS
- ✅ Custom domains
- ✅ Easy rollbacks

**Setup:**

1. **Prepare code:**

   Create `railway.json`:
   ```json
   {
     "$schema": "https://railway.app/railway.schema.json",
     "build": {
       "builder": "NIXPACKS"
     },
     "deploy": {
       "startCommand": "streamlit run streamlit_app.py --server.port $PORT --server.address 0.0.0.0",
       "healthcheckPath": "/"
     }
   }
   ```

   Create `nixpacks.toml`:
   ```toml
   [phases.setup]
   nixPkgs = ["python311", "postgresql"]

   [phases.install]
   cmds = [
     "pip install -r requirements.txt",
     "python3 -m spacy download en_core_web_sm"
   ]
   ```

2. **Deploy:**
   - Connect GitHub repo to Railway
   - Add PostgreSQL service
   - Set environment variables
   - Deploy

**Cost:** $5 free credit/month → ~$10-15/month

---

### Option 3: Docker + Cloud Run / Fly.io / Render

**Setup:**

Create `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    graphviz \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download spaCy model
RUN python3 -m spacy download en_core_web_sm

# Copy application code
COPY . .

# Expose port
EXPOSE 8501

# Health check
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

# Run Streamlit
CMD ["streamlit", "run", "streamlit_app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

Create `.dockerignore`:
```
venv/
__pycache__/
*.pyc
.env
.git/
.claude/
about_the_fed_pages/
faq_pages/
*.png
```

**Deploy to Google Cloud Run:**
```bash
# Build and push
gcloud builds submit --tag gcr.io/[PROJECT-ID]/fed-rag

# Deploy
gcloud run deploy fed-rag \
  --image gcr.io/[PROJECT-ID]/fed-rag \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars "ANTHROPIC_API_KEY=[KEY],DATABASE_URL=[DB_URL]"
```

**Deploy to Fly.io:**
```bash
# Install flyctl
curl -L https://fly.io/install.sh | sh

# Launch app
fly launch

# Set secrets
fly secrets set ANTHROPIC_API_KEY=[KEY]
fly secrets set DATABASE_URL=[DB_URL]

# Deploy
fly deploy
```

---

### Option 4: Traditional VPS (DigitalOcean, Linode, AWS EC2)

**Setup on Ubuntu 22.04:**

```bash
# 1. Install dependencies
sudo apt update
sudo apt install python3.11 python3.11-venv postgresql-client graphviz nginx

# 2. Clone repository
git clone [your-repo-url]
cd claude

# 3. Setup Python environment
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 -m spacy download en_core_web_sm

# 4. Setup environment variables
cp .env.example .env
nano .env  # Edit with your values

# 5. Create systemd service
sudo nano /etc/systemd/system/fed-rag.service
```

**/etc/systemd/system/fed-rag.service:**
```ini
[Unit]
Description=Federal Reserve RAG Streamlit App
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/claude
Environment="PATH=/home/ubuntu/claude/venv/bin"
ExecStart=/home/ubuntu/claude/venv/bin/streamlit run streamlit_app.py --server.port 8501 --server.address 127.0.0.1
Restart=always

[Install]
WantedBy=multi-user.target
```

**Setup Nginx reverse proxy:**

```bash
sudo nano /etc/nginx/sites-available/fed-rag
```

**/etc/nginx/sites-available/fed-rag:**
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

**Enable and start:**
```bash
# Enable Nginx site
sudo ln -s /etc/nginx/sites-available/fed-rag /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx

# Start application
sudo systemctl enable fed-rag
sudo systemctl start fed-rag
sudo systemctl status fed-rag
```

**Setup SSL with Let's Encrypt:**
```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

---

## Quick Deploy Guides

### Recommended: Streamlit Cloud + Supabase (Free)

**Total time: ~15 minutes**

1. **Setup Supabase** (5 min)
   - Create account at supabase.com
   - Create new project
   - Copy connection string from Settings → Database
   - Run schema files via Supabase SQL Editor or psql

2. **Setup Streamlit Cloud** (5 min)
   - Push code to GitHub
   - Deploy at share.streamlit.io
   - Add secrets (API key, DATABASE_URL)

3. **Import content** (5 min)
   - Run locally once: `python3 fed_content_importer.py`
   - Or add import step to deployment script

✅ **Result:** Free, fully managed deployment

---

### Budget: Railway (App + DB)

**Total time: ~20 minutes**

1. **Deploy on Railway**
   - Sign up at railway.app
   - Create new project
   - Add PostgreSQL service (with pgvector)
   - Connect GitHub repository
   - Set environment variables
   - Deploy

2. **Run schema migrations**
   - Use Railway's psql web terminal
   - Run all schema files

✅ **Result:** $5 free credit/month, then ~$10-15/month

---

### Production: AWS RDS + Cloud Run

**Total time: ~1 hour**

1. **Setup AWS RDS PostgreSQL** (30 min)
2. **Build and deploy Docker image to Cloud Run** (20 min)
3. **Configure secrets and environment** (10 min)

✅ **Result:** Enterprise-grade, scalable deployment (~$30-50/month)

---

## Environment Variables & Secrets

### Required Variables

```bash
# Anthropic API (Required)
ANTHROPIC_API_KEY=sk-ant-...

# Database (Required)
DATABASE_URL=postgresql://user:pass@host:5432/dbname

# PII Redaction (Optional, default: true)
ENABLE_PII_REDACTION=true
```

### Managing Secrets by Platform

**Streamlit Cloud:**
- Settings → Secrets → Add in TOML format

**Railway:**
- Variables tab → Add key-value pairs

**Cloud Run:**
```bash
gcloud run services update fed-rag \
  --update-secrets=ANTHROPIC_API_KEY=anthropic-key:latest
```

**Docker:**
- Use `.env` file (not in version control)
- Or pass via `-e` flag: `docker run -e ANTHROPIC_API_KEY=...`

**VPS:**
- Add to systemd service file
- Or use `.env` file with proper permissions (chmod 600)

---

## Troubleshooting

### PostgreSQL Connection Issues

**Error: "could not translate host name to address"**
```bash
# Check if DATABASE_URL is correct
echo $DATABASE_URL

# Test connection manually
psql $DATABASE_URL -c "SELECT version();"
```

**Error: "pgvector extension not found"**
```bash
# Connect to database
psql $DATABASE_URL

# Check if extension is installed
\dx

# Install if missing
CREATE EXTENSION IF NOT EXISTS vector;
```

**Error: "SSL connection required"**
```bash
# Add sslmode to connection string
DATABASE_URL=postgresql://user:pass@host:5432/db?sslmode=require
```

**Error: "too many connections"**
```python
# In database.py, reduce connection pool size
# Or upgrade database plan for more connections
```

---

### Application Deployment Issues

**Error: "ModuleNotFoundError: No module named 'spacy'"**
```bash
# Ensure requirements.txt includes all dependencies
pip install -r requirements.txt

# Download spaCy model
python3 -m spacy download en_core_web_sm
```

**Error: "Port already in use"**
```bash
# Change Streamlit port
streamlit run streamlit_app.py --server.port 8502
```

**Error: "Anthropic API key not found"**
```bash
# Check environment variable
echo $ANTHROPIC_API_KEY

# For Streamlit Cloud, add to secrets.toml
# For local, add to .env file
```

**Streamlit app shows "Connection error"**
- Check if DATABASE_URL is accessible from deployment environment
- For managed databases, check firewall/IP whitelist
- Test connection from deployment environment

---

### Performance Optimization

**Slow queries:**
```sql
-- Add indexes (already in schema, but verify)
CREATE INDEX IF NOT EXISTS idx_documents_embedding ON documents USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS idx_queries_created_at ON queries(created_at);
```

**High memory usage:**
- Reduce batch size in embeddings.py
- Use smaller spaCy model: `en_core_web_sm` (current) vs `en_core_web_md`
- Increase instance memory if needed

**Slow PII redaction:**
- Disable if not needed: `ENABLE_PII_REDACTION=false`
- Or use lighter spaCy model

---

### Database Migration

**Moving from local to production database:**

```bash
# 1. Export from local database
pg_dump -h localhost -U postgres fed_rag > backup.sql

# 2. Import to production
psql $DATABASE_URL < backup.sql

# Or use pg_dump/pg_restore for binary dump
pg_dump -Fc fed_rag > backup.dump
pg_restore -d $DATABASE_URL backup.dump
```

**Backup production database:**
```bash
# For Supabase: Use built-in backups (Settings → Database → Backups)
# For Railway: Use CLI: railway run pg_dump
# For AWS RDS: Use automated backups (RDS console)
# For manual backup:
pg_dump $DATABASE_URL > backup-$(date +%Y%m%d).sql
```

---

## Monitoring & Maintenance

### Health Checks

**Database:**
```sql
-- Check database size
SELECT pg_size_pretty(pg_database_size('fed_rag'));

-- Check table sizes
SELECT
  schemaname,
  tablename,
  pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- Check vector index
SELECT * FROM pg_indexes WHERE tablename = 'documents';
```

**Application:**
```bash
# Streamlit Cloud: Built-in monitoring
# Railway: Metrics tab
# Cloud Run: Google Cloud Console → Metrics
# VPS: Check service status
sudo systemctl status fed-rag
```

### Logs

**Streamlit Cloud:** App → Logs (bottom right)
**Railway:** Deployments → View logs
**Cloud Run:** Google Cloud Console → Logs
**VPS:**
```bash
sudo journalctl -u fed-rag -f
```

---

## Cost Estimation

### Free Tier Deployment
- **Database:** Supabase Free (500MB) or Neon Free (3GB)
- **App:** Streamlit Community Cloud (Free)
- **Total:** $0/month (plus Anthropic API usage)

### Budget Deployment
- **Database:** Supabase Pro ($25) or Railway ($5-10)
- **App:** Railway ($5-10)
- **Total:** ~$10-35/month (plus Anthropic API)

### Production Deployment
- **Database:** AWS RDS db.t3.small ($30)
- **App:** Cloud Run ($20-50 depending on traffic)
- **Total:** ~$50-80/month (plus Anthropic API)

### Anthropic API Costs
- **Model:** Claude Sonnet 4
- **Input:** $3 per million tokens
- **Output:** $15 per million tokens
- **Estimate:** ~$20-100/month depending on usage (1000-5000 queries/month)

---

## Security Checklist

- [ ] Use strong PostgreSQL passwords
- [ ] Enable SSL for database connections
- [ ] Store secrets in platform secret managers (not in code)
- [ ] Enable PII redaction in production
- [ ] Use HTTPS for application (automatic with most platforms)
- [ ] Whitelist database access by IP (if applicable)
- [ ] Regular database backups
- [ ] Monitor for unusual activity
- [ ] Keep dependencies updated
- [ ] Use environment-specific API keys (dev/prod)

---

## Next Steps

1. Choose deployment option based on:
   - **Budget:** Free tier vs paid
   - **Technical comfort:** Managed vs self-hosted
   - **Scale:** Expected traffic/usage
   - **Region:** Data residency requirements

2. Setup PostgreSQL first (hardest part)

3. Deploy application

4. Import Federal Reserve content

5. Test thoroughly before going live

6. Monitor and optimize

---

**Need help?** Common issues:
- pgvector installation → Use managed service (Supabase/Neon)
- Connection errors → Check DATABASE_URL format and firewall
- Slow performance → Add indexes, check query plans
- API errors → Verify ANTHROPIC_API_KEY is set correctly

**Recommended stack for most users:** Streamlit Cloud + Supabase (Free, easy, reliable)
