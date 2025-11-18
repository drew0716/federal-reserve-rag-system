# Federal Reserve Public Correspondence Response System

A Retrieval Augmented Generation (RAG) system that provides professional responses to inquiries about Federal Reserve policies, operations, and monetary policy. Built with Claude Sonnet 4, PostgreSQL with pgvector, and Streamlit.

## Overview

This system crawls official Federal Reserve documentation, processes it into a searchable knowledge base, and generates professional, well-cited responses using AI. It includes advanced privacy protection, AI-powered feedback analysis, and continuous improvement based on user ratings and comments.

## 🚀 Quick Links

- **[Pipeline Architecture](PIPELINE_ARCHITECTURE.md)** - System architecture diagrams, data flows, and component details
- **[Deployment Guide](DEPLOYMENT.md)** - Complete guide for deploying to production with PostgreSQL options
- **[Local Model Migration Guide](LOCAL_MODEL_MIGRATION.md)** - Replace Claude Sonnet 4 with local open-source models (Llama, Qwen, Mistral)
- **[PII Redaction Documentation](PII_REDACTION.md)** - Details on privacy protection features
- **[Feedback Analysis Documentation](FEEDBACK_ANALYSIS.md)** - How AI-powered feedback works

> **New to deployment?** Check out [DEPLOYMENT.md](DEPLOYMENT.md) for step-by-step guides to deploy with Streamlit Cloud, Railway, AWS, or Docker. Includes detailed PostgreSQL setup options (managed services like Supabase/Neon or self-hosted).

> **Want to eliminate API costs?** See [LOCAL_MODEL_MIGRATION.md](LOCAL_MODEL_MIGRATION.md) for complete instructions on replacing Claude Sonnet 4 with local models like Llama 3.1, Qwen 2.5, or Mistral. Includes code changes, performance optimization, and quality comparison.

## Features

### Core Capabilities
- **📝 Professional Response Generation**: Claude Sonnet 4 generates correspondence-style responses with inline citations
- **🔍 Intelligent Document Retrieval**: Vector similarity search with feedback-based hybrid ranking
- **📚 Federal Reserve Content**: Automatically crawls and indexes federalreserve.gov content
- **📋 One-Click Copy**: Copy responses with st-copy integration

### Privacy & Security
- **🔒 PII Redaction**: Automatic detection and redaction of personally identifiable information before processing
  - Pattern-based: Emails, phones, SSNs, credit cards, IP addresses, account numbers
  - AI-based (spaCy NER): Person names, locations, organizations
  - Context-aware: Preserves Federal Reserve entities while protecting user privacy
  - **Data minimization**: Original queries with PII are NEVER stored

### AI-Powered Feedback System
- **⭐ Enhanced Feedback Analysis**: Claude-powered sentiment analysis of user comments
  - Extracts sentiment (positive/neutral/negative) with confidence scores
  - Identifies specific issues (outdated info, incorrect info, too technical, missing citations, etc.)
  - Assigns severity levels (minor, moderate, severe)
  - Generates actionable summaries
- **📊 Smart Document Ranking**: Combines ratings (70%) + sentiment analysis (30%) + issue penalties
- **🚨 Automatic Quality Flagging**: Documents with recurring issues are flagged for review
- **📈 Continuous Learning**: System improves over time from both ratings and detailed feedback

### User Interface
- **🏷️ Automatic Query Categorization**: AI-powered topic detection for better analytics
- **📊 Analytics Dashboard**: Track performance metrics, response quality, and categorized query topics
- **💬 Dialog-Based Views**: Clean list interfaces with modal dialogs for detailed content
- **🗑️ Data Management**: Clean up old responses and feedback with advanced filtering
- **ℹ️ System Documentation**: Built-in "How It Works" page with interactive diagrams

## Prerequisites

- **Python 3.9+** (tested with Python 3.11.9)
- **PostgreSQL 18** with pgvector extension (Note: Homebrew installs on port 5433 by default)
- **Anthropic API Key** with Claude access
- **macOS, Linux, or Windows** (instructions provided for macOS)
- **Graphviz** (for generating architecture diagrams)

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

**Key packages** (automatically installed from `requirements.txt`):
```
anthropic>=0.18.0          # Claude Sonnet 4 API
psycopg2-binary>=2.9.9     # PostgreSQL adapter
pgvector>=0.2.0            # Vector similarity search
python-dotenv>=1.0.0       # Environment management
sentence-transformers>=2.2.0  # Text embeddings
streamlit>=1.28.0          # Web UI framework
st-copy>=1.1.0             # One-click copy functionality
spacy>=3.7.0               # PII detection with NER
diagrams>=0.23.0           # Architecture diagram generation
pandas>=2.0.0              # Data analysis
plotly>=5.17.0             # Interactive charts
```

### 4. Install spaCy Language Model

```bash
python3 -m spacy download en_core_web_sm
```

This downloads the English language model needed for PII detection.

### 5. Install Graphviz (for diagrams)

**macOS:**
```bash
brew install graphviz
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt-get install graphviz
```

**Linux (Fedora/RHEL):**
```bash
sudo yum install graphviz
```

### 6. Install and Set Up PostgreSQL

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

### 7. Create Database and User

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

### 8. Set Up Database Schema

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
# Run all schema files in order
psql -U rag_user -p 5433 -d rag_system -f schema.sql
psql -U rag_user -p 5433 -d rag_system -f schema_update_sources.sql
psql -U rag_user -p 5433 -d rag_system -f schema_update_categories.sql
psql -U rag_user -p 5433 -d rag_system -f schema_update_feedback_analysis.sql
psql -U rag_user -p 5433 -d rag_system -f schema_update_pii_no_storage.sql
```

**Note:** You may be prompted for the password you set earlier. Use `PGPASSWORD='your_secure_password'` prefix if needed.

### 9. Configure Environment Variables

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

# PII Redaction (enabled by default)
ENABLE_PII_REDACTION=true

# Reranking Configuration
FEEDBACK_WEIGHT=0.3
```

### 10. Import Federal Reserve Content

The system needs to crawl and import Federal Reserve content before it can answer questions.

```bash
# Option 1: Crawl fresh content from federalreserve.gov (recommended for first time)
python3 fed_content_importer.py --crawl

# Option 2: Import existing pre-crawled content (if you have cached files)
python3 fed_content_importer.py --import-only
```

**What this does:**
- Crawls 272 "About the Fed" pages + 87 FAQ pages
- Chunks content into 500-character segments with 50-character overlap
- Generates vector embeddings for semantic search
- Stores ~2,625 document chunks in PostgreSQL

**Expected output:**
```
============================================================
CRAWLING & IMPORTING FEDERAL RESERVE CONTENT
============================================================

📥 Crawling About the Fed content...
   Fetched 272 pages
   Created 2,100+ chunks
   Generating embeddings...
   Storing in database...
   ✓ Inserted 2,100+ new document chunks

📥 Crawling FAQ content...
   Fetched 87 pages
   Created 525+ chunks
   ✓ Inserted 525+ new document chunks

============================================================
IMPORT COMPLETE
Total: 2,625+ documents
============================================================
```

### 11. Generate Architecture Diagrams

```bash
python3 generate_pipeline_diagram.py
```

This creates three diagrams that are displayed in the "How It Works" page:
- `rag_architecture.png` - System architecture
- `rag_query_flow.png` - Query flow pipeline with PII redaction and feedback analysis
- `rag_content_pipeline.png` - Content processing pipeline

---

> **💡 Deploying to Production?** This guide covers local development setup. For production deployment (Streamlit Cloud, Railway, AWS, Docker, etc.), see the **[Deployment Guide](DEPLOYMENT.md)** which includes detailed PostgreSQL hosting options and platform-specific instructions.

---

## Running the Application

### Start the Streamlit Interface

```bash
streamlit run streamlit_app.py
```

The application will open in your browser at `http://localhost:8501`

## Quick Start for Returning Users

If you've already completed the installation and just want to start the application again:

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

### 3. Start PostgreSQL (if not running)

```bash
# Check if running
pg_isready -p 5433

# Start if needed (macOS)
brew services start postgresql@18
```

### 4. Start the Application

```bash
streamlit run streamlit_app.py
```

### 5. Stop the Application

- Press `Ctrl+C` in the terminal to stop Streamlit
- Optionally deactivate the virtual environment: `deactivate`
- PostgreSQL can keep running or stop it: `brew services stop postgresql@18`

## Using the Application

### 1. Submit Inquiry Page

- Enter questions about Federal Reserve policies, monetary policy, or operations
- **PII is automatically redacted** before processing (e.g., names, emails, phone numbers)
- Click "Submit Inquiry" to generate a response
- Responses include inline citations with links to source documents
- **One-click copy** button to copy the entire response
- View the **category** tag showing the query topic
- Rate responses (1-5 stars) and optionally provide comments for detailed feedback
- AI analyzes your comments to extract sentiment, issues, and severity

### 2. Review Responses Page

- Review previous unrated responses
- Navigate through responses and submit ratings with optional comments
- Skip responses you don't want to rate
- AI-powered comment analysis runs automatically when you submit feedback

### 3. Analytics Dashboard

- **Overall Metrics**: Total queries, average ratings, response count
- **Rating Distribution**: Visual chart showing 1-5 star breakdown
- **Queries Over Time**: Track system usage patterns
- **Query Categories**: Automatically categorized topics (Interest Rates & Monetary Policy, Banking System, Currency & Coin, etc.)
- **Feedback Analysis Insights**:
  - Analyzed comments count
  - Comments flagged for review
  - Documents flagged for quality issues
  - Common issues identified (bar chart)
  - Severity distribution (pie chart)
- **Recent Feedback**: List view with dialog popups showing full details
  - Rating, sentiment, issues, and severity for each comment
  - Full query and response text
- **Most Common Queries**: Track frequently asked questions

### 4. Source Content Management

- View statistics about loaded Federal Reserve content
- See refresh history with status tracking
- Manually refresh content from federalreserve.gov
- Browse sample source documents

### 5. How It Works Page

- **Privacy Protection**: Learn about PII redaction with spaCy
- **Document Retrieval**: Understand vector similarity search and hybrid ranking
- **AI-Powered Feedback Analysis**: See how Claude analyzes comments
- **Enhanced Scoring Formula**: Ratings + sentiment + issue penalties
- **Interactive Diagrams**: System architecture, query flow, and content processing
- **Technical Details**: Deep dive into the RAG technology

### 6. Data Management Page

- **List View with Dialogs**: Browse responses in a clean list, click to view full details
- **Bulk Actions**:
  - Delete responses older than X days
  - Remove responses below a rating threshold
- **Individual Management**: Select and delete specific responses
- **Feedback Display**: See all ratings and analyzed comments for each response
  - Sentiment scores and labels
  - Identified issues
  - Severity indicators

## System Architecture

> **📊 For detailed pipeline documentation:** See [PIPELINE_ARCHITECTURE.md](PIPELINE_ARCHITECTURE.md) for comprehensive explanations of all diagrams, data flows, component details, and performance considerations.

### High-Level Components

```
┌─────────────────────────────────────────────────────────┐
│                   Streamlit Web UI                      │
│  (Submit, Review, Analytics, Management, How It Works)  │
└─────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│                    RAG System Core                       │
│  • PII Redactor (spaCy)    • Response Generation        │
│  • Query Processing        • Feedback Analyzer (Claude) │
│  • Document Retrieval      • Category Detection         │
└─────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┴───────────────────┐
        ▼                                       ▼
┌──────────────────┐                  ┌─────────────────┐
│  Claude Sonnet 4 │                  │   PostgreSQL    │
│   (Anthropic)    │                  │  + pgvector     │
│                  │                  │                 │
│  • Categories    │                  │  • Documents    │
│  • Responses     │                  │  • Queries      │
│  • Sentiment     │                  │  • Responses    │
│  • Issues        │                  │  • Feedback     │
└──────────────────┘                  │  • Scores       │
                                      │  • Flags        │
                                      └─────────────────┘
```

### Query Flow (15 Steps)

1. **User submits question** via Streamlit UI
2. **PII Detection & Redaction** (spaCy NER) - Removes sensitive information locally
3. **Store redacted query only** - Original with PII is never stored
4. **Claude detects query category** (e.g., Interest Rates, Banking, Currency)
5. **Question → Vector embedding** (384-dim using MiniLM-L6-v2)
6. **Vector similarity search** in PostgreSQL with pgvector
7. **Hybrid ranking**: `Similarity × (Base Score × (1 + 0.3 × Enhanced Feedback Score))`
8. **Top 10 documents retrieved** with source URLs
9. **Claude generates response** with inline citations (2000 token limit)
10. **Response stored** in database with category and metadata
11. **User views response** with category tag and one-click copy
12. **User rates response** (1-5 stars) with optional comment
13. **AI analyzes comment** (Claude extracts sentiment, issues, severity)
14. **Enhanced feedback score calculated** (rating + sentiment + penalties)
15. **Document patterns checked** - Auto-flag documents with recurring issues

### Database Schema

**Core Tables:**
- `documents` - Chunked content with 384-dim vector embeddings
- `queries` - Redacted user questions with embeddings and categories (**PII never stored**)
- `responses` - Generated responses with metadata
- `feedback` - User ratings, comments, and AI analysis
  - `sentiment_score` - Float from -1.0 to +1.0
  - `issue_types` - Array of detected issues
  - `severity` - Enum: none, minor, moderate, severe
  - `analysis_summary` - AI-generated summary
- `document_scores` - Enhanced reranking scores based on feedback
- `document_review_flags` - Auto-flagged documents needing attention

**Source Management:**
- `source_refresh_log` - Track content refresh history
- Metadata fields: `source_url`, `source_title`, `source_type`

**PII Tracking:**
- `has_pii` - Boolean flag in queries table
- `redaction_count` - Number of items redacted
- `redaction_details` - JSON metadata (types only, **not actual PII values**)

## Privacy & Security

### PII Redaction

The system uses a **privacy-first design** with local PII detection:

**What Gets Redacted:**
- 📧 Email addresses
- 📞 Phone numbers
- 🆔 Social Security Numbers
- 💳 Credit card numbers
- 🌐 IP addresses
- 🏦 Account numbers
- 👤 Person names (via spaCy NER)
- 📍 Locations (via spaCy NER)
- 🏢 Organizations (via spaCy NER)

**What's NOT Redacted:**
- Federal Reserve Board, FRB, Board of Governors
- Federal Reserve Bank (all regional banks)
- FOMC, Federal Open Market Committee
- Federal Reserve System
- Federal Reserve officials (e.g., Jerome Powell)

**Privacy Guarantees:**
- ✅ Local processing with spaCy (no external API for redaction)
- ✅ Redacted BEFORE Claude API call
- ✅ Redacted BEFORE database storage
- ✅ Original queries with PII are **NEVER stored**
- ✅ Redaction metadata excludes actual PII values
- ✅ GDPR Article 25 compliant (Privacy by Design)

See `PII_REDACTION.md` for detailed documentation.

### AI-Powered Feedback Analysis

When you provide a comment with your rating, Claude Sonnet 4 analyzes it to extract:

**Sentiment Analysis:**
- Score from -1.0 (very negative) to +1.0 (very positive)
- Confidence level (0.0 to 1.0)
- Label: Positive, Neutral, or Negative

**Issue Detection:**
- `outdated_info` - Information is no longer current
- `incorrect_info` - Factually inaccurate content
- `too_technical` - Overly complex for general audience
- `too_simple` - Insufficient detail
- `missing_citations` - Lacks source references
- `irrelevant` - Off-topic or not helpful
- `none` - No issues identified

**Severity Assessment:**
- `none` - No problems
- `minor` - Small issues, doesn't affect usefulness
- `moderate` - Notable problems, reduces quality
- `severe` - Major issues, content needs review/replacement

**Enhanced Scoring Formula:**
```
Base Score = (Average Rating - 3.0) / 2.0

Sentiment Contribution = Sentiment Score × Confidence × 0.3

Severity Penalty:
  - severe: -0.3
  - moderate: -0.15
  - minor: -0.05

Issue Penalties:
  - incorrect_info: -0.20
  - outdated_info: -0.15
  - missing_citations: -0.08
  - too_technical: -0.10
  - irrelevant: -0.12

Enhanced Score =
  (0.7 × Base Score) +
  (0.3 × Sentiment Contribution) +
  Severity Penalty +
  Sum of Issue Penalties
```

**Document Flagging:**
When multiple users report similar issues, documents are automatically flagged for review.

See `FEEDBACK_ANALYSIS.md` for detailed documentation.

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

### spaCy Model Not Found

```bash
# Download the English model
python3 -m spacy download en_core_web_sm

# Verify installation
python3 -c "import spacy; nlp = spacy.load('en_core_web_sm'); print('✓ Model loaded')"
```

### Module Not Found Errors

```bash
# Make sure virtual environment is activated
source venv/bin/activate

# Reinstall all dependencies
pip install -r requirements.txt
```

### Crawled Content Missing

If you see "Directory not found" errors:

```bash
# Run the crawler to download fresh content
python3 fed_content_importer.py --crawl
```

The cached content directories (`about_the_fed_pages/`, `faq_pages/`) are excluded from git and regenerated by the crawler.

### Anthropic API Errors

```bash
# Verify API key is set
echo $ANTHROPIC_API_KEY

# Check .env file
cat .env | grep ANTHROPIC

# Test API connection
python3 -c "from anthropic import Anthropic; c = Anthropic(); print('✓ API key valid')"
```

## Development

### Project Structure

```
.
├── streamlit_app.py                    # Main Streamlit UI
├── rag_system.py                       # RAG core logic
├── database.py                         # Database operations
├── embeddings.py                       # Embedding service
├── pii_redactor.py                     # PII detection and redaction
├── feedback_analyzer.py                # AI-powered comment analysis
├── fed_content_importer.py             # Content importer
├── crawl_about_fed.py                  # Web crawler
├── generate_pipeline_diagram.py        # Architecture diagram generator
├── schema.sql                          # Base database schema
├── schema_update_sources.sql           # Source management schema
├── schema_update_categories.sql        # Query categorization schema
├── schema_update_feedback_analysis.sql # Feedback analysis schema
├── schema_update_pii_no_storage.sql    # PII data minimization schema
├── requirements.txt                    # Python dependencies
├── .env.example                        # Environment template
├── .gitignore                          # Git exclusions
├── README.md                           # This file
├── PII_REDACTION.md                    # PII redaction documentation
├── FEEDBACK_ANALYSIS.md                # Feedback analysis documentation
├── rag_architecture.png                # System architecture diagram
├── rag_query_flow.png                  # Query flow diagram
├── rag_content_pipeline.png            # Content processing diagram
├── about_the_fed_pages/                # Crawled Fed content (generated)
└── faq_pages/                          # Crawled FAQ content (generated)
```

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
# In streamlit_app.py, line 129
max_tokens = 2000  # Current setting (increase or decrease as needed)
```

**Disable PII redaction:**
```bash
# Edit .env (not recommended)
ENABLE_PII_REDACTION=false
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
  TRUNCATE documents, queries, responses, feedback, document_scores,
           source_refresh_log, document_review_flags CASCADE;
"
```

### Recalculate Document Scores

If you want to recalculate all document scores based on current feedback:

```python
from rag_system import RAGSystem

rag = RAGSystem()
updated = rag.rerank_documents(use_enhanced_scores=True)
print(f"Updated {updated} documents")
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
- **st-copy** - One-click copy functionality
- **spaCy** - Natural language processing and NER
- **sentence-transformers** - Embedding models
- **diagrams** - Architecture diagram generation
- **Federal Reserve** - Source content

## License & Disclaimer

This project is provided as-is for educational and learning purposes. There are no license restrictions on use.

**Important**: This project is **not affiliated with, endorsed by, or connected to the Federal Reserve Board or any Federal Reserve Bank**. This is an independent learning project created to explore and demonstrate Retrieval Augmented Generation (RAG) systems using publicly available Federal Reserve content.

The content used by this system is sourced from publicly accessible pages on federalreserve.gov. This tool should be used for educational purposes only and does not represent official Federal Reserve communications or policy.

## Support

For issues and questions:
- Create a GitHub issue
- Check the "How It Works" page in the application
- Review `PII_REDACTION.md` and `FEEDBACK_ANALYSIS.md` for detailed feature documentation
- Review troubleshooting section above

---

**Built with Claude Sonnet 4** | Last Updated: January 2025
