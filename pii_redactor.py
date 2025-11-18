"""
PII Redaction Module
Redacts personally identifiable information (PII) from user queries before processing.
Uses spaCy NER and regex patterns for local, privacy-preserving redaction.
"""

import re
from typing import Dict, List, Tuple
import spacy
from spacy.matcher import Matcher


class PIIRedactor:
    """Redacts PII from text using spaCy NER and regex patterns."""

    def __init__(self, model_name: str = "en_core_web_sm"):
        """
        Initialize the PII redactor.

        Args:
            model_name: spaCy model to use (default: en_core_web_sm)
        """
        try:
            self.nlp = spacy.load(model_name)
        except OSError as e:
            error_msg = f"""
            spaCy model '{model_name}' not found.

            For Streamlit Cloud deployment:
            - The model should be installed automatically from requirements.txt
            - Ensure this line is in requirements.txt:
              https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.7.1/en_core_web_sm-3.7.1-py3-none-any.whl

            For local development:
            - Run: python3 -m spacy download {model_name}
            """
            print(error_msg)
            raise RuntimeError(error_msg) from e

        # Entity types to redact
        self.entity_types = {
            'PERSON': '[REDACTED_NAME]',
            'ORG': '[REDACTED_ORG]',
            'GPE': '[REDACTED_LOCATION]',
            'LOC': '[REDACTED_LOCATION]',
            'FAC': '[REDACTED_LOCATION]',
            'DATE': '[REDACTED_DATE]',
        }

        # Compile regex patterns for additional PII types
        self.patterns = {
            'email': {
                'pattern': re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
                'replacement': '[REDACTED_EMAIL]'
            },
            'phone': {
                'pattern': re.compile(r'\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b'),
                'replacement': '[REDACTED_PHONE]'
            },
            'ssn': {
                'pattern': re.compile(r'\b\d{3}-\d{2}-\d{4}\b'),
                'replacement': '[REDACTED_SSN]'
            },
            'credit_card': {
                'pattern': re.compile(r'\b(?:\d{4}[-\s]?){3}\d{4}\b'),
                'replacement': '[REDACTED_CARD]'
            },
            'ip_address': {
                'pattern': re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b'),
                'replacement': '[REDACTED_IP]'
            },
            'account_number': {
                'pattern': re.compile(r'\b(?:account|acct)[\s#:]+\d{6,}\b', re.IGNORECASE),
                'replacement': '[REDACTED_ACCOUNT]'
            },
        }

    def redact(self, text: str, aggressive: bool = False) -> Dict:
        """
        Redact PII from text.

        Args:
            text: Input text to redact
            aggressive: If True, redact more entity types (default: False)

        Returns:
            Dictionary containing:
            - redacted_text: Text with PII redacted
            - original_text: Original text (for reference)
            - redactions: List of redaction details
            - has_pii: Boolean indicating if PII was found
        """
        if not text or not text.strip():
            return {
                'redacted_text': text,
                'original_text': text,
                'redactions': [],
                'has_pii': False
            }

        original_text = text
        redacted_text = text
        redactions = []

        # Step 1: Regex-based redaction (emails, phones, SSN, etc.)
        for pii_type, config in self.patterns.items():
            matches = list(config['pattern'].finditer(redacted_text))
            for match in reversed(matches):  # Reverse to maintain indices
                redacted_value = match.group()
                redactions.append({
                    'type': pii_type,
                    'value': redacted_value,
                    'start': match.start(),
                    'end': match.end(),
                    'replacement': config['replacement']
                })
                redacted_text = (
                    redacted_text[:match.start()] +
                    config['replacement'] +
                    redacted_text[match.end():]
                )

        # Step 2: spaCy NER-based redaction
        doc = self.nlp(redacted_text)
        entities_to_redact = []

        for ent in doc.ents:
            if ent.label_ in self.entity_types:
                # Skip if it's a Federal Reserve related term
                if self._is_federal_reserve_term(ent.text):
                    continue

                # Skip if it's part of a Federal Reserve Bank name
                # Check context around the entity
                start_context = max(0, ent.start_char - 30)
                end_context = min(len(redacted_text), ent.end_char + 30)
                context = redacted_text[start_context:end_context].lower()
                if 'federal reserve bank of' in context and ent.label_ == 'GPE':
                    # This is likely a location that's part of a Federal Reserve Bank name
                    continue

                # Skip common financial terms
                if self._is_financial_term(ent.text):
                    continue

                entities_to_redact.append(ent)

        # Sort entities by start position (reverse order for replacement)
        entities_to_redact.sort(key=lambda e: e.start_char, reverse=True)

        for ent in entities_to_redact:
            replacement = self.entity_types[ent.label_]
            redactions.append({
                'type': f'named_entity_{ent.label_}',
                'value': ent.text,
                'start': ent.start_char,
                'end': ent.end_char,
                'replacement': replacement
            })
            redacted_text = (
                redacted_text[:ent.start_char] +
                replacement +
                redacted_text[ent.end_char:]
            )

        has_pii = len(redactions) > 0

        return {
            'redacted_text': redacted_text,
            'original_text': original_text,
            'redactions': redactions,
            'has_pii': has_pii,
            'redaction_count': len(redactions)
        }

    def _is_federal_reserve_term(self, text: str) -> bool:
        """Check if text is a Federal Reserve related term that shouldn't be redacted."""
        text_lower = text.lower().strip()

        # Remove common articles at the start
        for article in ['the ', 'a ', 'an ', 'contact the ', 'contact ']:
            if text_lower.startswith(article):
                text_lower = text_lower[len(article):]
                break

        # Exact match terms
        fed_terms = {
            'federal reserve', 'fed', 'fomc', 'federal open market committee',
            'jerome powell', 'chair powell', 'federal reserve board',
            'federal reserve bank', 'frb', 'board of governors',
            'washington', 'united states', 'federal reserve system',
            'the fed', 'the board', 'the federal reserve'
        }

        # Check exact matches
        if text_lower in fed_terms:
            return True

        # Check if it starts with Federal Reserve Bank (e.g., "Federal Reserve Bank of New York")
        if text_lower.startswith('federal reserve bank of'):
            return True

        # Check if it starts with regional names + Federal Reserve Bank (e.g., "Chicago Federal Reserve Bank")
        if text_lower.endswith('federal reserve bank'):
            return True

        # Check if it contains "reserve bank" (e.g., "New York Federal Reserve Bank")
        if 'federal reserve bank' in text_lower:
            return True

        return False

    def _is_financial_term(self, text: str) -> bool:
        """Check if text is a common financial term that shouldn't be redacted."""
        financial_terms = {
            'bank', 'banks', 'banking', 'monetary policy', 'interest rate',
            'inflation', 'recession', 'economy', 'market', 'treasury',
            'dollar', 'currency', 'today', 'yesterday', 'tomorrow',
            'january', 'february', 'march', 'april', 'may', 'june',
            'july', 'august', 'september', 'october', 'november', 'december'
        }
        return text.lower() in financial_terms

    def get_redaction_summary(self, redaction_result: Dict) -> str:
        """
        Get a human-readable summary of redactions.

        Args:
            redaction_result: Result from redact() method

        Returns:
            Summary string
        """
        if not redaction_result['has_pii']:
            return "No PII detected"

        redaction_types = {}
        for r in redaction_result['redactions']:
            rtype = r['type']
            redaction_types[rtype] = redaction_types.get(rtype, 0) + 1

        summary_parts = []
        for rtype, count in redaction_types.items():
            clean_type = rtype.replace('named_entity_', '').replace('_', ' ').title()
            summary_parts.append(f"{count} {clean_type}{'s' if count > 1 else ''}")

        return "Redacted: " + ", ".join(summary_parts)

    def get_safe_redaction_details(self, redaction_result: Dict) -> List[Dict]:
        """
        Get redaction details WITHOUT PII values (safe for database storage).

        Args:
            redaction_result: Result from redact() method

        Returns:
            List of redaction details without 'value' field
        """
        if not redaction_result or not redaction_result.get('redactions'):
            return []

        safe_redactions = []
        for r in redaction_result['redactions']:
            # Remove the 'value' field which contains actual PII
            safe_redactions.append({
                'type': r['type'],
                'start': r['start'],
                'end': r['end'],
                'replacement': r['replacement']
                # 'value' is intentionally omitted for privacy
            })

        return safe_redactions


# Singleton instance
_redactor_instance = None


def get_pii_redactor() -> PIIRedactor:
    """Get or create singleton PII redactor instance."""
    global _redactor_instance
    if _redactor_instance is None:
        _redactor_instance = PIIRedactor()
    return _redactor_instance


if __name__ == "__main__":
    # Test the redactor
    redactor = PIIRedactor()

    test_cases = [
        "My name is John Smith and my email is john.smith@example.com",
        "Please call me at 555-123-4567 or email contact@company.org",
        "My SSN is 123-45-6789 and I live in San Francisco",
        "What is the current federal funds rate?",
        "How does the Federal Reserve control inflation?",
        "I opened account #123456789 at Bank of America in New York",
        "Contact Jane Doe at jane@email.com or 202-456-1111"
    ]

    print("=" * 70)
    print("PII REDACTION TESTS")
    print("=" * 70)

    for i, test in enumerate(test_cases, 1):
        print(f"\n{i}. Original: {test}")
        result = redactor.redact(test)
        print(f"   Redacted: {result['redacted_text']}")
        print(f"   Summary:  {redactor.get_redaction_summary(result)}")

        if result['has_pii']:
            print(f"   Details:  {len(result['redactions'])} redaction(s)")
            for r in result['redactions']:
                print(f"             - {r['type']}: '{r['value']}' → '{r['replacement']}'")
