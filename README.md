# Federal Reserve Public Correspondence Response System

A Retrieval Augmented Generation (RAG) system that provides professional responses to inquiries about Federal Reserve policies, operations, and monetary policy. Built with Claude Sonnet 4, PostgreSQL with pgvector, and Streamlit.

## Overview

This system crawls official Federal Reserve documentation, processes it into a searchable knowledge base, and generates professional, well-cited responses using AI. It includes a feedback system that continuously improves response quality based on user ratings.

## Features

- **📝 Professional Response Generation**: Claude Sonnet 4 generates correspondence-style responses with inline citations
- **🔍 Intelligent Document Retrieval**: Vector similarity search with feedback-based reranking
- **📚 Federal Reserve Content**: Automatically crawls and indexes federalreserve.gov content
- **⭐ User Feedback System**: Ratings improve future retrieval results
- **📊 Analytics Dashboard**: Track performance metrics, response quality, and auto-categorized query topics
- **🏷️ Automatic Query Categorization**: AI-powered topic detection for better analytics
- **🗑️ Data Management**: Clean up old responses and feedback
- **ℹ️ System Documentation**: Built-in "How It Works" page explaining RAG technology

## Prerequisites

- **Python 3.9+** (tested with Python 3.11.9)
- **PostgreSQL 18** with pgvector extension (Note: Homebrew installs on port 5433 by default)
- **Anthropic API Key** with Claude access
- **macOS, Linux, or Windows** (instructions provided for macOS)

## Installation

### 1. Clone the Repository

```bash
git clone <your-repo-url>
cd <your-repo-name>
```

### 2. Set Up Python Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

**Required packages** (already in `requirements.txt`):
```
anthropic>=0.18.0
psycopg2-binary>=2.9.9
pgvector>=0.2.0
python-dotenv>=1.0.0
numpy>=1.24.0
sentence-transformers>=2.2.0
streamlit>=1.28.0
pandas>=2.0.0
plotly>=5.17.0
aiohttp>=3.8.0
beautifulsoup4>=4.12.0
```

### 4. Install and Set Up PostgreSQL

#### macOS (Homebrew)

```bash
# Install PostgreSQL 18
brew install postgresql@18

# Start PostgreSQL service
brew services start postgresql@18

# Verify it's running (should be on port 5433)
pg_isready -p 5433
```

#### Install pgvector Extension

```bash
# Clone pgvector repository
git clone https://github.com/pgvector/pgvector.git
cd pgvector

# Build and install
make
make install  # May require sudo

# Return to project directory
cd ..
```

### 5. Create Database and User

```bash
# Connect to PostgreSQL
psql -U postgres -p 5433

# In PostgreSQL shell, run:
```

```sql
-- Create database
CREATE DATABASE rag_system;

-- Create user
CREATE USER rag_user WITH PASSWORD 'your_secure_password';

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE rag_system TO rag_user;

-- Exit
\q
```

### 6. Set Up Database Schema

```bash
# Connect to the new database
psql -U postgres -p 5433 -d rag_system

# Enable pgvector extension
```

```sql
CREATE EXTENSION IF NOT EXISTS vector;
\q
```

```bash
# Run schema setup
psql -U rag_user -p 5433 -d rag_system -f schema.sql
psql -U rag_user -p 5433 -d rag_system -f schema_update_sources.sql
psql -U rag_user -p 5433 -d rag_system -f schema_update_categories.sql
```

**Note:** You may be prompted for the password you set earlier.

### 7. Configure Environment Variables

Copy the example environment file and edit it:

```bash
cp .env.example .env
```

Edit `.env` with your settings:

```bash
# Anthropic API Key (REQUIRED - get from https://console.anthropic.com/)
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# PostgreSQL Configuration
DB_HOST=localhost
DB_PORT=5433
DB_NAME=rag_system
DB_USER=rag_user
DB_PASSWORD=your_secure_password

# Model Configuration
CLAUDE_MODEL=claude-sonnet-4-20250514
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2

# Reranking Configuration
FEEDBACK_WEIGHT=0.3
```

### 8. Import Federal Reserve Content

The system needs to crawl and import Federal Reserve content before it can answer questions.

```bash
# Option 1: Import existing pre-crawled content (faster, ~2-3 minutes)
python3 fed_content_importer.py --import-only

# Option 2: Crawl fresh content from federalreserve.gov (slower, ~10-15 minutes)
python3 fed_content_importer.py --crawl
```

**What this does:**
- Reads 272 "About the Fed" pages + 87 FAQ pages
- Chunks content into 500-character segments with 50-character overlap
- Generates vector embeddings for semantic search
- Stores ~2,625 document chunks in PostgreSQL

**Expected output:**
```
============================================================
IMPORTING EXISTING FEDERAL RESERVE CONTENT
============================================================

📥 Importing About the Fed content...
   Created 2,100+ chunks from 272 files
   Generating embeddings...
   Storing in database...
   ✓ Inserted 2,100+ new document chunks

📥 Importing FAQ content...
   Created 525+ chunks from 87 files
   ✓ Inserted 525+ new document chunks

============================================================
IMPORT COMPLETE
Total: 2,625+ documents
============================================================
```

## Running the Application

### Start the Streamlit Interface

```bash
streamlit run streamlit_app.py
```

The application will open in your browser at `http://localhost:8501`

## Quick Start for Returning Users

If you've already completed the installation and just want to start the application again (e.g., after a restart), follow these steps:

### 1. Navigate to Project Directory

```bash
cd /path/to/federal-reserve-rag-system
```

### 2. Activate Virtual Environment

```bash
# macOS/Linux
source venv/bin/activate

# Windows
venv\Scripts\activate
```

You should see `(venv)` appear in your terminal prompt.

### 3. Start PostgreSQL (if not running)

**Check if PostgreSQL is running:**
```bash
pg_isready -p 5433
```

**If you see an error, start PostgreSQL:**

**macOS (Homebrew):**
```bash
brew services start postgresql@18
```

**Linux (systemd):**
```bash
sudo systemctl start postgresql
```

**Verify it's running:**
```bash
pg_isready -p 5433
# Should output: /tmp:5433 - accepting connections
```

### 4. Start the Application

```bash
streamlit run streamlit_app.py
```

The application will automatically open at `http://localhost:8501`

### 5. Stop the Application

When you're done:
- Press `Ctrl+C` in the terminal to stop Streamlit
- Optionally deactivate the virtual environment: `deactivate`
- PostgreSQL can keep running in the background, or stop it:
  ```bash
  brew services stop postgresql@18  # macOS
  sudo systemctl stop postgresql    # Linux
  ```

### Common Issues

**"Command not found: streamlit"**
- You forgot to activate the virtual environment (Step 2)

**"Connection refused" or database errors**
- PostgreSQL isn't running (Step 3)
- Check `.env` has correct DB credentials

**"Module not found" errors**
- Virtual environment not activated, or dependencies not installed
- Run: `source venv/bin/activate && pip install -r requirements.txt`

## Using the Application

### 1. Submit Inquiry Page

- Enter questions about Federal Reserve policies, monetary policy, or operations
- Click "Submit Inquiry" to generate a response
- Responses include inline citations with links to source documents
- Rate responses to improve future results

### 2. Review Responses Page

- Review previous unrated responses
- Navigate through responses and submit ratings
- Skip responses you don't want to rate

### 3. Analytics Dashboard

- View system-wide statistics (total queries, average ratings)
- See rating distribution charts
- Track queries over time
- **View query categories** - Automatically categorized topics (Interest Rates, Banking, Currency, etc.)
- Review recent feedback

### 4. Source Content Management

- View statistics about loaded Federal Reserve content
- See refresh history
- Manually refresh content from federalreserve.gov
- Browse sample source documents

### 5. How It Works Page

- Learn about RAG technology
- Understand the retrieval and ranking system
- See how feedback improves results
- View technical details

### 6. Data Management Page

- Delete responses older than X days
- Remove low-rated responses
- Filter and delete individual responses
- Clean up outdated data

## System Architecture

### Components

```
┌─────────────────────────────────────────────────────────┐
│                   Streamlit Web UI                      │
│  (Query, Review, Analytics, Management, How It Works)   │
└─────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│                    RAG System Core                       │
│  • Query Processing    • Response Generation            │
│  • Document Retrieval  • Feedback Collection            │
└─────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┴───────────────────┐
        ▼                                       ▼
┌──────────────────┐                  ┌─────────────────┐
│  Claude Sonnet   │                  │   PostgreSQL    │
│  4 (Anthropic)   │                  │  + pgvector     │
│                  │                  │                 │
│  • Text Gen      │                  │  • Documents    │
│  • Citation      │                  │  • Queries      │
└──────────────────┘                  │  • Responses    │
                                      │  • Feedback     │
                                      │  • Scores       │
                                      └─────────────────┘
```

### Query Flow

1. **User submits question** via Streamlit UI
2. **Claude detects query category** (e.g., Interest Rates, Banking, Currency)
3. **Question → Vector embedding** (384-dim using MiniLM-L6-v2)
4. **Vector similarity search** in PostgreSQL
5. **Hybrid ranking**: Similarity × (Base Score × (1 + 0.3 × Feedback Score))
6. **Top 10 documents retrieved** with source URLs
7. **Claude generates response** with inline citations
8. **Response stored** in database with category
9. **User rates response** (1-5 stars)
10. **Feedback updates document scores** for future queries

### Database Schema

**Core Tables:**
- `documents` - Chunked content with vector embeddings
- `queries` - User questions with embeddings and auto-detected categories
- `responses` - Generated responses with metadata
- `feedback` - User ratings and comments
- `document_scores` - Reranking scores based on feedback

**Source Management:**
- `source_refresh_log` - Track content refresh history
- Metadata fields: `source_url`, `source_title`, `source_type`

## Content Management

### Crawling Fresh Content

The web crawler (`crawl_about_fed.py`) includes quality filters:

**Excluded Content:**
- Board meeting archives
- Financial reports and statements
- Biography pages
- Navigation and calendar pages
- Administrative content

**Included Content:**
- About the Fed explanatory pages
- Policy FAQs
- Educational resources
- Operational descriptions

### Refreshing Content

```bash
# Re-crawl Federal Reserve website and update database
python3 fed_content_importer.py --crawl
```

Or use the **Source Content** page in the Streamlit UI.

## Feedback and Continuous Improvement

### How Feedback Works

When you rate a response:
1. Rating is associated with all documents used in that response
2. System calculates average rating for each document
3. Ratings are converted to feedback scores:
   - 5 stars → +1.0 (boost ranking)
   - 3 stars → 0.0 (neutral)
   - 1 star → -1.0 (lower ranking)
4. Document scores update immediately
5. Future searches use updated scores

### Scoring Formula

```
Final Score = Similarity Score × (Base Score × (1 + Feedback Weight × Feedback Score))

Where:
- Similarity Score: Cosine similarity (0-1)
- Base Score: 1.0 (default)
- Feedback Score: -1.0 to +1.0 (from ratings)
- Feedback Weight: 0.3 (30% influence)
```

## Troubleshooting

### PostgreSQL Connection Issues

```bash
# Check if PostgreSQL is running
pg_isready -p 5433

# Check if port is correct
lsof -i :5433

# Restart PostgreSQL
brew services restart postgresql@18
```

### pgvector Extension Not Found

```bash
# Verify extension is installed
psql -U postgres -p 5433 -c "SELECT * FROM pg_available_extensions WHERE name = 'vector';"

# If not found, reinstall pgvector
cd pgvector
make clean
make
sudo make install
```

### Import Fails with "Directory not found"

Make sure you have the content directories:
```bash
ls about_the_fed_pages/  # Should show 272 files
ls faq_pages/            # Should show 87 files
```

If missing, run the crawler:
```bash
python3 crawl_about_fed.py
```

### Slow Queries

```sql
-- Check if indexes exist
\d documents

-- Rebuild vector index if needed
DROP INDEX IF EXISTS idx_documents_embedding;
CREATE INDEX idx_documents_embedding ON documents
  USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 100);
```

### Anthropic API Errors

```bash
# Verify API key is set
echo $ANTHROPIC_API_KEY

# Test API connection
python3 -c "from anthropic import Anthropic; print(Anthropic().models.list())"
```

## Development

### Project Structure

```
.
├── streamlit_app.py           # Main Streamlit UI
├── rag_system.py              # RAG core logic
├── database.py                # Database operations
├── embeddings.py              # Embedding service
├── fed_content_importer.py    # Content importer
├── crawl_about_fed.py         # Web crawler
├── schema.sql                 # Database schema
├── schema_update_sources.sql  # Source management schema
├── requirements.txt           # Python dependencies
├── .env.example              # Environment template
├── about_the_fed_pages/      # Crawled Fed content (272 files)
├── faq_pages/                # Crawled FAQ content (87 files)
└── README.md                 # This file
```

### Adding New Content Sources

1. Update `crawl_about_fed.py` with new URL patterns
2. Run crawler: `python3 crawl_about_fed.py`
3. Import content: `python3 fed_content_importer.py --import-only`

### Customizing the System

**Change embedding model:**
```bash
# Edit .env
EMBEDDING_MODEL=sentence-transformers/all-mpnet-base-v2

# Note: Must match vector dimension in schema (384 for MiniLM, 768 for mpnet)
```

**Adjust feedback influence:**
```bash
# Edit .env - increase to 0.5 for 50% influence
FEEDBACK_WEIGHT=0.5
```

**Change response length:**
```python
# In streamlit_app.py, line 101
max_tokens = 500  # Increase for longer responses
```

## Maintenance

### Backup Database

```bash
pg_dump -U rag_user -p 5433 rag_system > rag_system_backup.sql
```

### Restore Database

```bash
psql -U rag_user -p 5433 rag_system < rag_system_backup.sql
```

### Clear All Data (Start Fresh)

```bash
psql -U rag_user -p 5433 -d rag_system -c "
  TRUNCATE documents, queries, responses, feedback, document_scores, source_refresh_log CASCADE;
"
```

## Performance Tuning

### For Large Datasets (10,000+ documents)

```sql
-- Use HNSW index instead of IVFFlat (PostgreSQL 16+)
CREATE INDEX idx_documents_embedding ON documents
  USING hnsw (embedding vector_cosine_ops);

-- Increase shared_buffers in postgresql.conf
shared_buffers = 256MB
```

### Optimize Vector Search

```sql
-- Increase IVFFlat lists for better accuracy (slower search)
DROP INDEX idx_documents_embedding;
CREATE INDEX idx_documents_embedding ON documents
  USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 200);

-- Or decrease for faster search (less accurate)
WITH (lists = 50);
```

## Credits

- **Anthropic** - Claude Sonnet 4 API
- **pgvector** - PostgreSQL vector similarity search
- **Streamlit** - Web interface framework
- **sentence-transformers** - Embedding models
- **Federal Reserve** - Source content

## License & Disclaimer

This project is provided as-is for educational and learning purposes. There are no license restrictions on use.

**Important**: This project is **not affiliated with, endorsed by, or connected to the Federal Reserve Board or any Federal Reserve Bank**. This is an independent learning project created to explore and demonstrate Retrieval Augmented Generation (RAG) systems using publicly available Federal Reserve content.

The content used by this system is sourced from publicly accessible pages on federalreserve.gov. This tool should be used for educational purposes only and does not represent official Federal Reserve communications or policy.

## Support

For issues and questions:
- Create a GitHub issue
- Check the "How It Works" page in the application
- Review troubleshooting section above

---
