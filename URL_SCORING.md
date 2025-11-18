# URL-Level Scoring System

## Overview

The RAG system now uses **URL-level scoring** instead of chunk-level scoring. This improvement preserves learned rankings across data refreshes, ensuring the system doesn't "forget" what it has learned when source data is updated.

## Why URL-Level Scoring?

### The Problem with Chunk-Level Scoring

Previously, the system scored individual document chunks:
- Each chunk had its own feedback score
- When source data refreshed, documents were deleted and recreated
- **All learned rankings were lost** due to CASCADE deletes
- The system had to start learning from scratch after each refresh

### The Solution: URL-Level Scoring

Now, the system scores entire source documents (URLs):
- Scores are aggregated at the URL level
- URL scores **persist across data refreshes**
- When documents are refreshed, they inherit scores from their source URL
- Learning is preserved, improving results over time

## How It Works

### 1. Feedback Collection
When users rate responses:
```python
# User provides feedback on a response
db.add_feedback(response_id, rating=4, comment="Very helpful")
```

### 2. Score Calculation
Feedback is aggregated by source URL:
```python
# Recalculates scores at the URL level
db.calculate_source_document_scores(use_enhanced_scores=True)
```

This creates entries in `source_document_scores` table:
```sql
source_url                          | feedback_score | enhanced_score | feedback_count
------------------------------------|----------------|----------------|---------------
https://federalreserve.gov/about   | 0.35          | 0.42          | 12
https://federalreserve.gov/faq/1   | -0.15         | -0.20         | 3
```

### 3. Document Retrieval
When searching, URL-level scores are applied to all chunks from that URL:
```python
# Search applies URL-level scores automatically
results = db.search_similar_documents(query_embedding, top_k=5)
# Each chunk inherits the score from its source URL
```

### 4. Data Refresh
When refreshing source data:
```bash
python fed_content_importer.py --crawl
```

**Old behavior (chunk-level):**
- ❌ Documents deleted → Scores CASCADE deleted
- ❌ All learning lost

**New behavior (URL-level):**
- ✅ Documents deleted → URL scores remain
- ✅ New chunks inherit scores from their source URL
- ✅ Learning preserved!

## Database Schema

### New Table: source_document_scores
```sql
CREATE TABLE source_document_scores (
    id SERIAL PRIMARY KEY,
    source_url TEXT NOT NULL UNIQUE,
    source_type VARCHAR(50),
    feedback_score FLOAT DEFAULT 0.0,
    enhanced_feedback_score FLOAT DEFAULT 0.0,
    feedback_count INTEGER DEFAULT 0,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Legacy Table: document_scores (Deprecated)
The old `document_scores` table is kept for backward compatibility but is no longer the primary scoring method.

## Migration

### For Existing Systems

If you have existing chunk-level scores, migrate them to URL-level:

```bash
python migrate_to_url_scores.py
```

This script:
1. Aggregates existing chunk-level scores by URL
2. Creates URL-level scores
3. Preserves all feedback data
4. Shows verification results

### For New Systems

New systems automatically use URL-level scoring. No migration needed.

## Usage

### Enable URL-Level Scoring (Default)
```python
# URL-level scoring is enabled by default
results = db.search_similar_documents(query_embedding, use_url_scores=True)
```

### Use Legacy Chunk-Level Scoring
```python
# Only use if you have a specific reason
results = db.search_similar_documents(query_embedding, use_url_scores=False)
```

### Update Scores After New Feedback
```python
rag = RAGSystem(db)

# This now updates both chunk-level (legacy) and URL-level scores
rag.rerank_documents(use_enhanced_scores=True)
```

## Benefits

### 1. **Persistent Learning**
- Scores survive data refreshes
- System gets smarter over time
- No need to retrain after updates

### 2. **Simplified Model**
- Feedback applies to whole articles
- More intuitive (users rate articles, not chunks)
- Reduces score fragmentation

### 3. **Robust to Changes**
- Chunking strategy can change without losing scores
- Document updates preserve learning
- More resilient architecture

### 4. **Better for Source Content**
- Perfect for external sources (Federal Reserve docs)
- Matches how users think about document quality
- Natural fit for content refresh workflows

## Score Calculation

### Basic Feedback Score
```
feedback_score = (avg_rating - 3.0) / 2.0
```
- Rating of 5 → score of +1.0 (boost)
- Rating of 3 → score of 0.0 (neutral)
- Rating of 1 → score of -1.0 (penalty)

### Enhanced Feedback Score
Combines rating + sentiment analysis + severity penalties:
```
enhanced_score =
    0.7 * rating_score +
    0.3 * sentiment_score * confidence +
    severity_penalty
```

Where:
- `sentiment_score`: positive (+1.0), neutral (0.0), negative (-1.0)
- `confidence`: sentiment analysis confidence (0.0 to 1.0)
- `severity_penalty`: minor (-0.1), moderate (-0.3), severe (-0.5)

### Final Ranking Score
Applied during search:
```
final_score = similarity * (1 + feedback_weight * enhanced_score)
```

Default `feedback_weight` is 0.3 (configurable via `FEEDBACK_WEIGHT` env var)

## API Reference

### Database Methods

#### `calculate_source_document_scores(use_enhanced_scores=True)`
Recalculates URL-level scores from all feedback.

**Parameters:**
- `use_enhanced_scores` (bool): Use enhanced scoring with sentiment analysis

**Returns:**
- int: Number of URLs updated

#### `search_similar_documents(query_embedding, top_k=5, use_url_scores=True)`
Search with URL-level reranking.

**Parameters:**
- `query_embedding` (np.ndarray): Query vector
- `top_k` (int): Number of results
- `use_url_scores` (bool): Use URL-level scores (default: True)

**Returns:**
- List[Dict]: Ranked documents with scores

## Monitoring

### Check URL Scores
```sql
SELECT
    source_url,
    source_type,
    enhanced_feedback_score,
    feedback_count,
    last_updated
FROM source_document_scores
ORDER BY enhanced_feedback_score DESC
LIMIT 10;
```

### Compare Chunk vs URL Scores
```sql
SELECT
    d.source_url,
    COUNT(ds.id) as chunk_count,
    AVG(ds.feedback_score) as avg_chunk_score,
    sds.enhanced_feedback_score as url_score
FROM documents d
LEFT JOIN document_scores ds ON d.id = ds.document_id
LEFT JOIN source_document_scores sds ON d.source_url = sds.source_url
GROUP BY d.source_url, sds.enhanced_feedback_score
HAVING COUNT(ds.id) > 0;
```

## Troubleshooting

### Scores not persisting after refresh?
- Verify `source_document_scores` table exists
- Check that documents have `source_url` populated
- Run migration script if upgrading from chunk-level

### URL scores seem wrong?
- Check `feedback_count` - need multiple ratings for accuracy
- Verify `calculate_source_document_scores()` is being called after feedback
- Review raw feedback data for that URL

### Migration failed?
- Ensure schema is updated first (`supabase_setup.sql`)
- Check database permissions
- Verify documents have `source_url` field

## Best Practices

1. **Run migration once** when upgrading to URL-level scoring
2. **Recalculate scores** after each feedback submission
3. **Monitor URL scores** to identify high/low quality sources
4. **Use enhanced scores** for better accuracy with comment analysis
5. **Keep feedback_weight moderate** (0.2-0.4 range) to balance similarity and learning

## Future Enhancements

Potential improvements to consider:
- Time decay for old feedback
- Confidence intervals for scores with low feedback counts
- Per-section scoring within URLs
- Automatic quality detection for new sources
