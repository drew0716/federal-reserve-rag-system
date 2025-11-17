# PII Redaction System

## Overview

The Federal Reserve RAG system now includes **local PII (Personally Identifiable Information) redaction** that protects user privacy by automatically detecting and redacting sensitive information **before** sending queries to Claude or storing them in the database.

## 🔒 Privacy-First Design

### Key Principles

1. **Local Processing**: All PII detection runs locally using spaCy - nothing is sent to Claude for redaction
2. **Pre-Processing**: Queries are redacted **before** being sent to Claude API or embedded
3. **Transparent**: Users are shown exactly what was redacted
4. **Compliant**: Helps meet privacy regulations (GDPR, CCPA, etc.)

### What Gets Redacted

The system detects and redacts:

#### Pattern-Based (Regex)
- **📧 Email addresses**: `john@example.com` → `[REDACTED_EMAIL]`
- **📞 Phone numbers**: `555-123-4567` → `[REDACTED_PHONE]`
- **🆔 SSN**: `123-45-6789` → `[REDACTED_SSN]`
- **💳 Credit cards**: `4111-1111-1111-1111` → `[REDACTED_CARD]`
- **🌐 IP addresses**: `192.168.1.1` → `[REDACTED_IP]`
- **🏦 Account numbers**: `account #123456789` → `[REDACTED_ACCOUNT]`

#### NER-Based (spaCy)
- **👤 Person names**: `John Smith` → `[REDACTED_NAME]`
- **🏢 Organizations**: (Bank of America excluded for context)
- **📍 Locations**: `San Francisco` → `[REDACTED_LOCATION]`
- **📅 Dates**: (Generic dates, not "today" or month names)

### What's NOT Redacted

To preserve query intent, the system excludes:

- **Federal Reserve entities**:
  - "Federal Reserve", "Federal Reserve Board", "FRB"
  - "Board of Governors"
  - "Federal Reserve Bank" and any regional bank (e.g., "Federal Reserve Bank of New York")
  - "FOMC", "Federal Open Market Committee"
  - "Federal Reserve System"
  - Federal Reserve officials (e.g., "Jerome Powell", "Chair Powell")
- **Financial terms**: "bank", "inflation", "interest rate"
- **Generic time references**: "today", "yesterday", month names
- **Country names**: "United States"

## 🚀 How It Works

### Query Flow

```
1. User types: "My name is John and I live in Boston. What's the current fed rate?"
              ↓
2. PII Redactor (local spaCy):
   - Detects: "John" (PERSON), "Boston" (GPE)
   - Redacts to: "My name is [REDACTED_NAME] and I live in [REDACTED_LOCATION]. What's the current fed rate?"
              ↓
3. Database stores ONLY redacted version:
   - query_text: "My name is [REDACTED_NAME]..." (redacted ONLY)
   - has_pii: TRUE
   - redaction_count: 2
   - redaction_details: [{"type": "named_entity_PERSON", ...}, ...]

   ⚠️  IMPORTANT: Original query with PII is NEVER stored anywhere
              ↓
4. Send to Claude: "My name is [REDACTED_NAME]..." (redacted version)
              ↓
5. User sees:
   - Warning: "🔒 Privacy Protection: Redacted: 1 Location, 1 Person"
   - Redacted query displayed
```

### Database Schema

```sql
-- Columns in queries table for PII tracking
-- query_text: Always contains redacted version if PII was detected
-- has_pii: Flag indicating if PII was found and redacted
-- redaction_count: Number of items redacted
-- redaction_details: JSON array of redaction metadata (types, NOT values)

-- IMPORTANT: Original queries with PII are NEVER stored in the database
-- The original_query_text column has been removed for privacy protection

-- Data minimization constraint
ALTER TABLE queries
ADD CONSTRAINT queries_pii_tracking_check
CHECK (
    (has_pii = FALSE AND redaction_count = 0) OR
    (has_pii = TRUE AND redaction_count > 0)
);
```

## 📊 Features

### 1. Automatic Detection

```python
from pii_redactor import get_pii_redactor

redactor = get_pii_redactor()
result = redactor.redact("Call me at 555-1234")

print(result['redacted_text'])  # "Call me at [REDACTED_PHONE]"
print(result['has_pii'])        # True
print(result['redaction_count']) # 1
```

### 2. User Notification

When PII is detected, users see:
- **Warning banner**: "🔒 Privacy Protection: Redacted: 1 Phone, 1 Email"
- **Redacted query**: Displayed in info box
- **Explanation**: "For your privacy, sensitive information has been redacted before processing."

### 3. Audit Trail

Redaction metadata (NOT the actual PII values) is logged in the database:

```json
{
  "redactions": [
    {
      "type": "email",
      "replacement": "[REDACTED_EMAIL]",
      "start": 15,
      "end": 32
    }
  ]
}
```

**Note**: The `value` field containing actual PII is **NOT** stored in the database. Only redaction metadata (type, position, replacement) is kept for analytics.

### 4. Configurable

Control redaction via environment variables:

```bash
# Disable PII redaction (not recommended)
ENABLE_PII_REDACTION=false

# Adjust spaCy model
# Default: en_core_web_sm (fast, lightweight)
# Options: en_core_web_md, en_core_web_lg (more accurate)
```

## 🧪 Testing

Run the test suite:

```bash
python3 pii_redactor.py
```

Example output:
```
1. Original: My name is John Smith and my email is john.smith@example.com
   Redacted: My name is [REDACTED_NAME] and my email is [REDACTED_EMAIL]
   Summary:  Redacted: 1 Email, 1 Person

2. Original: What is the current federal funds rate?
   Redacted: What is the current federal funds rate?
   Summary:  No PII detected
```

## 🔍 Analytics

View PII redaction statistics in the Analytics Dashboard:

```sql
-- Queries with PII
SELECT COUNT(*) FROM queries WHERE has_pii = TRUE;

-- Most common redaction types
SELECT
  jsonb_array_elements(redaction_details)->>'type' as redaction_type,
  COUNT(*) as count
FROM queries
WHERE has_pii = TRUE
GROUP BY redaction_type
ORDER BY count DESC;
```

## ⚙️ Configuration

### Installation

Already installed! Just run:

```bash
python3 -m spacy download en_core_web_sm
```

### Customization

Edit `pii_redactor.py` to:

1. **Add new patterns**:
```python
self.patterns['custom'] = {
    'pattern': re.compile(r'your_regex_here'),
    'replacement': '[REDACTED_CUSTOM]'
}
```

2. **Adjust entity types**:
```python
self.entity_types = {
    'PERSON': '[REDACTED_NAME]',
    'ORG': '[REDACTED_ORG]',  # Add/remove as needed
}
```

3. **Add whitelists**:
```python
def _is_whitelisted(self, text: str) -> bool:
    whitelist = {'federal reserve', 'fed', 'your_term'}
    return text.lower() in whitelist
```

## 🛡️ Security Best Practices

### 1. Data Minimization ✅

**This system follows the principle of data minimization:**
- Original queries with PII are **NEVER stored** in the database
- Only redacted versions are kept
- Redaction metadata tracks types but NOT actual PII values
- This approach eliminates the risk of PII data breaches

### 2. Analytics Without PII

You can still analyze redaction patterns:

```sql
-- See most common PII types detected
SELECT
  jsonb_array_elements(redaction_details)->>'type' as redaction_type,
  COUNT(*) as count
FROM queries
WHERE has_pii = TRUE
GROUP BY redaction_type
ORDER BY count DESC;
```

### 3. Compliance

This system helps with:
- **GDPR Article 25**: Privacy by design
- **CCPA**: Data minimization
- **HIPAA**: PHI protection (if handling health data)

## 📝 Example Use Cases

### 1. User asks about personal finance

**Input**: "I'm John Doe, SSN 123-45-6789. What interest rate can I get?"

**Redacted**: "I'm [REDACTED_NAME], [REDACTED_SSN]. What interest rate can I get?"

**Result**: Claude never sees the PII. Database stores redacted version.

### 2. User shares contact info

**Input**: "Email me at jane@company.com about rates"

**Redacted**: "Email me at [REDACTED_EMAIL] about rates"

**Result**: Email address not sent to Claude or permanently stored.

### 3. Normal query (no PII)

**Input**: "What is quantitative easing?"

**Redacted**: "What is quantitative easing?" (unchanged)

**Result**: No redaction needed, normal processing.

## 🚨 Limitations

1. **Not 100% Perfect**: NER can miss some names or over-redact
2. **Context Loss**: Redaction may remove useful context (trade-off for privacy)
3. **Local Only**: Works on query text only (not documents or responses)
4. **English Only**: Current spaCy model is English-only

## 🔮 Future Enhancements

- [ ] Multi-language support
- [ ] Custom entity recognition for financial terms
- [ ] Differential privacy for analytics
- [ ] Pseudonymization (replace with fake but consistent values)
- [ ] User consent options (opt-in/opt-out)
- [ ] Real-time PII detection as user types

## 📚 References

- [spaCy NER Documentation](https://spacy.io/usage/linguistic-features#named-entities)
- [GDPR Privacy by Design](https://gdpr-info.eu/art-25-gdpr/)
- [NIST Privacy Framework](https://www.nist.gov/privacy-framework)

---

**Note**: This PII redaction is designed for the Federal Reserve RAG system but can be adapted for any application handling sensitive user data.
