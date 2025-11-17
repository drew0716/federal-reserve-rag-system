# Feedback Analysis System

## Overview

The Federal Reserve RAG system now includes **AI-powered textual feedback analysis** that processes user comments to extract quality signals and enhance document ranking. This goes beyond simple star ratings to understand specific issues, sentiment, and severity.

## How It Works

### 1. Comment Analysis with Claude

When a user submits feedback with a text comment, the system:

1. **Analyzes the comment using Claude Sonnet 4** to extract:
   - **Sentiment Score**: -1.0 (very negative) to +1.0 (very positive)
   - **Issue Types**: Specific problems identified (outdated, incorrect, too_technical, etc.)
   - **Severity**: none, minor, moderate, or severe
   - **Review Flag**: Whether the document needs manual review
   - **Confidence**: How confident the AI is in the analysis (0.0-1.0)
   - **Summary**: One-sentence summary of the feedback

2. **Stores the analysis** in the database alongside the rating

3. **Checks for patterns** across multiple feedback items for the same document

4. **Flags documents for review** if recurring issues are detected

### 2. Enhanced Scoring Formula

The system now uses an **enhanced feedback score** that combines:

```
Enhanced Score = 0.7 × (Rating Score) + 0.3 × (Sentiment × Confidence) + Severity Penalty + Issue Penalties

Where:
- Rating Score: (rating - 3.0) / 2.0  →  Maps 1→-1.0, 3→0.0, 5→+1.0
- Sentiment × Confidence: Weighted sentiment from comment analysis
- Severity Penalty: -0.1 (minor), -0.3 (moderate), -0.5 (severe)
- Issue Penalties: Specific penalties for each issue type
  - incorrect: -0.4
  - outdated: -0.3
  - off_topic: -0.3
  - missing_info: -0.2
  - poor_citation: -0.15
  - too_technical: -0.1
  - too_simple: -0.1
  - formatting: -0.05
```

This enhanced score is used in the hybrid ranking formula:

```
Final Ranking = Similarity Score × (Base Score × (1 + 0.3 × Enhanced Feedback Score))
```

### 3. Document Review Flagging

Documents are automatically flagged for review when:

- **2+ users** flag the document as needing review
- **1+ severe issue** is reported
- **3+ moderate issues** are reported
- **50%+ of feedback** mentions the same issue type

Flagged documents appear in the **Analytics Dashboard** with:
- Reason for flagging
- Common issues identified
- Severity distribution
- Total feedback count
- Link to source content

## Database Schema

### New Feedback Columns

```sql
ALTER TABLE feedback
ADD COLUMN sentiment_score FLOAT DEFAULT 0.0,
ADD COLUMN issue_types TEXT[] DEFAULT '{}',
ADD COLUMN severity VARCHAR(20) DEFAULT 'none',
ADD COLUMN needs_review BOOLEAN DEFAULT FALSE,
ADD COLUMN analysis_confidence FLOAT DEFAULT 0.0,
ADD COLUMN analysis_summary TEXT,
ADD COLUMN analyzed_at TIMESTAMP;
```

### New Document Review Flags Table

```sql
CREATE TABLE document_review_flags (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES documents(id),
    flagged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    reason TEXT NOT NULL,
    common_issues JSONB,
    severity_distribution JSONB,
    total_feedbacks INTEGER DEFAULT 0,
    status VARCHAR(20) DEFAULT 'pending',
    reviewed_at TIMESTAMP,
    reviewer_notes TEXT
);
```

## Key Features

### 1. Automatic Issue Detection

The system identifies these issue types:

| Issue Type | Description |
|------------|-------------|
| `outdated` | Content is out of date or references old information |
| `incorrect` | Factual errors or wrong information |
| `too_technical` | Too complex or jargon-heavy |
| `too_simple` | Not detailed enough, lacks depth |
| `missing_info` | Important information is missing |
| `poor_citation` | Citations are unclear, broken, or missing |
| `off_topic` | Response doesn't address the question |
| `formatting` | Poor formatting or structure |

### 2. Severity Classification

- **None**: No significant issues
- **Minor**: Small problems that don't affect core utility
- **Moderate**: Notable issues that impact usefulness
- **Severe**: Critical problems requiring immediate attention

### 3. Analytics Dashboard Insights

The Analytics Dashboard now shows:

- **Analyzed Comments Count**: How many comments have been analyzed
- **Comments Flagged**: Feedback requiring attention
- **Documents Flagged**: Documents needing manual review
- **Common Issues Chart**: Bar chart of most frequent issues
- **Severity Distribution**: Pie chart of issue severity levels
- **Flagged Documents List**: Expandable list with details
- **Enhanced Recent Feedback**: Feedback with sentiment and issue indicators

## Usage

### Applying Database Schema

Run the schema update to add feedback analysis columns:

```bash
psql -U rag_user -p 5433 -d rag_system -f schema_update_feedback_analysis.sql
```

### Submitting Feedback with Analysis

The RAG system automatically analyzes comments when enabled (default):

```python
rag_system = RAGSystem()

# Feedback with comment analysis (default)
feedback_id = rag_system.submit_feedback(
    response_id=123,
    rating=2,
    comment="This information about interest rates seems outdated.",
    analyze_comment=True  # Default
)
```

### Recalculating Document Scores

Update document scores using enhanced feedback:

```python
# Use enhanced scores (rating + comment analysis)
rag_system.rerank_documents(use_enhanced_scores=True)

# Or use rating-only mode
rag_system.rerank_documents(use_enhanced_scores=False)
```

### Getting Feedback Insights

```python
insights = rag_system.get_feedback_insights()

print(f"Feedback needing review: {insights['feedback_needing_review']}")
print(f"Documents needing review: {insights['documents_needing_review']}")
print(f"Issue distribution: {insights['issue_type_distribution']}")
```

## Example Flow

1. **User submits query**: "What is the current federal funds rate?"

2. **System retrieves documents** and generates response

3. **User rates response**: 2 stars with comment "This seems outdated, the rate has changed recently"

4. **Claude analyzes comment**:
   ```json
   {
     "sentiment_score": -0.6,
     "issue_types": ["outdated"],
     "severity": "moderate",
     "needs_review": true,
     "confidence": 0.85,
     "summary": "User reports outdated interest rate information"
   }
   ```

5. **System stores analysis** and checks patterns

6. **If multiple users report same issue**:
   - Document gets flagged for review
   - Appears in Analytics Dashboard
   - Enhanced feedback score is lowered
   - Future searches rank this document lower

7. **Over time**: Better documents rise to the top based on quality signals

## Benefits

### 1. More Accurate Ranking
- Goes beyond star ratings to understand **why** users are dissatisfied
- Identifies specific problems vs. general sentiment
- Weights severe issues more heavily

### 2. Proactive Quality Management
- Automatically flags problematic documents
- Identifies patterns across multiple users
- Prioritizes review based on severity

### 3. Rich Analytics
- Understand common issues in your knowledge base
- Track sentiment trends over time
- Identify areas needing improvement

### 4. Continuous Improvement
- System learns from detailed feedback
- Quality signals compound over time
- Bad content naturally gets deprioritized

## Configuration

### Environment Variables

```bash
# Disable feedback analysis (use rating-only)
ENABLE_FEEDBACK_ANALYSIS=false

# Adjust feedback weight in ranking (default: 0.3 = 30%)
FEEDBACK_WEIGHT=0.3
```

### Feedback Analyzer Settings

In `feedback_analyzer.py`:

```python
# Adjust scoring weights
RATING_WEIGHT = 0.7  # 70% from star rating
SENTIMENT_WEIGHT = 0.3  # 30% from comment sentiment

# Adjust severity penalties
SEVERITY_PENALTIES = {
    'none': 0.0,
    'minor': -0.1,
    'moderate': -0.3,
    'severe': -0.5
}

# Adjust issue type penalties
ISSUE_PENALTIES = {
    'incorrect': -0.4,
    'outdated': -0.3,
    # ... customize as needed
}
```

## Testing

Test the feedback analyzer:

```bash
python3 feedback_analyzer.py
```

This will analyze a sample comment and show the output.

## Performance Considerations

- **Comment analysis adds ~1-2 seconds** per feedback submission (Claude API call)
- Analysis happens **asynchronously** - doesn't block the user
- Results are **cached** in the database
- Only comments with text are analyzed (rating-only feedback is instant)

## Future Enhancements

Potential improvements:

1. **Batch analysis** of unanalyzed comments
2. **Topic modeling** to identify common themes
3. **Automatic document updates** based on feedback patterns
4. **User expertise weighting** (trust power users more)
5. **Temporal analysis** (recent feedback weighted higher)
6. **Multi-language support** for non-English comments

---

**Note**: This feature uses the Claude Sonnet 4 API for comment analysis. Each analyzed comment counts toward your API usage.
