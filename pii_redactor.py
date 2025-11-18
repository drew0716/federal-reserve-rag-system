"""
PII Redaction Module
Redacts personally identifiable information (PII) from user queries before processing.
Uses Microsoft Presidio with GLiNER for local, privacy-preserving redaction.
"""

import re
from typing import Dict, List, Optional

# Try to import Presidio components
try:
    from presidio_analyzer import AnalyzerEngine, RecognizerRegistry
    from presidio_analyzer.nlp_engine import NlpEngineProvider
    from presidio_anonymizer import AnonymizerEngine
    from presidio_anonymizer.entities import OperatorConfig
    PRESIDIO_AVAILABLE = True
except ImportError:
    PRESIDIO_AVAILABLE = False
    AnalyzerEngine = None
    RecognizerRegistry = None
    NlpEngineProvider = None
    AnonymizerEngine = None
    OperatorConfig = None

# Try to import GLiNER recognizer
try:
    from presidio_analyzer.predefined_recognizers import GLiNERRecognizer
    GLINER_AVAILABLE = True
except ImportError:
    GLINER_AVAILABLE = False
    GLiNERRecognizer = None


class PIIRedactor:
    """Redacts PII from text using Microsoft Presidio with GLiNER and regex patterns."""

    def __init__(self):
        """Initialize the PII redactor with Presidio + GLiNER."""
        self.presidio_available = False
        self.gliner_available = False
        self.analyzer = None
        self.anonymizer = None

        # Initialize Presidio if available
        if PRESIDIO_AVAILABLE:
            try:
                self._initialize_presidio()
            except Exception as e:
                print(f"⚠️  Warning: Could not initialize Presidio: {e}")
                print(f"   PII redaction will use regex patterns only.")
                self.presidio_available = False
        else:
            print(f"⚠️  Warning: Presidio library not installed.")
            print(f"   PII redaction will use regex patterns only (no NER).")
            print(f"   To enable full PII redaction, install: pip install 'presidio-analyzer[gliner]' presidio-anonymizer")

        # Compile regex patterns for fallback and additional PII types
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

        # Entity type mappings for Presidio
        self.entity_replacements = {
            'PERSON': '[REDACTED_NAME]',
            'EMAIL_ADDRESS': '[REDACTED_EMAIL]',
            'PHONE_NUMBER': '[REDACTED_PHONE]',
            'US_SSN': '[REDACTED_SSN]',
            'CREDIT_CARD': '[REDACTED_CARD]',
            'IP_ADDRESS': '[REDACTED_IP]',
            'LOCATION': '[REDACTED_LOCATION]',
            'GPE': '[REDACTED_LOCATION]',
            'US_DRIVER_LICENSE': '[REDACTED_ID]',
            'US_PASSPORT': '[REDACTED_ID]',
            'DATE_TIME': '[REDACTED_DATE]',
            'NRP': '[REDACTED_LOCATION]',  # Nationalities/religious/political groups
            'ORGANIZATION': '[REDACTED_ORG]',
            'MEDICAL_LICENSE': '[REDACTED_ID]',
            'URL': '[REDACTED_URL]',
            'US_BANK_NUMBER': '[REDACTED_ACCOUNT]',
            'CRYPTO': '[REDACTED_CRYPTO]',
            'IBAN_CODE': '[REDACTED_ACCOUNT]',
        }

    def _initialize_presidio(self):
        """Initialize Presidio Analyzer and Anonymizer with spaCy."""
        try:
            # Create NLP engine configuration for spaCy
            configuration = {
                "nlp_engine_name": "spacy",
                "models": [{"lang_code": "en", "model_name": "en_core_web_sm"}],
            }

            # Try to create NLP engine (spaCy for NER)
            try:
                nlp_engine = NlpEngineProvider(nlp_configuration=configuration).create_engine()
                print(f"✅ spaCy NLP engine loaded successfully")
            except Exception as e:
                print(f"⚠️  Note: Could not load spaCy model: {e}")
                print(f"   Attempting to use Presidio without spaCy NLP...")
                nlp_engine = None

            # Create recognizer registry
            registry = RecognizerRegistry()

            # Use Presidio's built-in recognizers (fast and effective)
            # GLiNER is optional and can be enabled via environment variable
            import os
            use_gliner = os.getenv('USE_GLINER', 'false').lower() == 'true'

            if use_gliner and GLINER_AVAILABLE and GLiNERRecognizer:
                try:
                    print(f"⏳ Loading GLiNER model (this may take a minute on first run)...")
                    # GLiNER model for PII detection
                    gliner_model = "urchade/gliner_multi_pii-v1"

                    # Map GLiNER labels to Presidio entity types
                    entity_mapping = {
                        "person": "PERSON",
                        "name": "PERSON",
                        "email": "EMAIL_ADDRESS",
                        "phone number": "PHONE_NUMBER",
                        "phone": "PHONE_NUMBER",
                        "address": "LOCATION",
                        "ssn": "US_SSN",
                        "social security number": "US_SSN",
                        "credit card number": "CREDIT_CARD",
                        "credit card": "CREDIT_CARD",
                        "ip address": "IP_ADDRESS",
                        "organization": "ORGANIZATION",
                        "location": "LOCATION",
                        "date": "DATE_TIME",
                        "url": "URL",
                        "passport number": "US_PASSPORT",
                        "passport": "US_PASSPORT",
                        "driver license": "US_DRIVER_LICENSE",
                        "license": "US_DRIVER_LICENSE",
                        "bank account": "US_BANK_NUMBER",
                        "account number": "US_BANK_NUMBER",
                        "medical license": "MEDICAL_LICENSE",
                    }

                    gliner_recognizer = GLiNERRecognizer(
                        model_name=gliner_model,
                        entity_mapping=entity_mapping,
                        flat_ner=False,
                        multi_label=True,
                        map_location="cpu",
                    )

                    registry.add_recognizer(gliner_recognizer)
                    self.gliner_available = True
                    print(f"✅ GLiNER PII model loaded successfully")

                except Exception as e:
                    print(f"⚠️  Note: Could not load GLiNER model: {e}")
                    print(f"   Using Presidio's built-in recognizers with spaCy NER...")
                    registry.load_predefined_recognizers(nlp_engine=nlp_engine)
            else:
                # Use built-in recognizers with spaCy (default - effective NER)
                if use_gliner:
                    print(f"⚠️  GLiNER requested but not available, using Presidio built-in recognizers with spaCy...")
                else:
                    print(f"ℹ️  Using Presidio's built-in recognizers with spaCy NER (set USE_GLINER=true to enable GLiNER)")
                registry.load_predefined_recognizers(nlp_engine=nlp_engine)

            # Create analyzer engine
            self.analyzer = AnalyzerEngine(
                registry=registry,
                nlp_engine=nlp_engine,
                supported_languages=["en"]
            )

            # Create anonymizer engine
            self.anonymizer = AnonymizerEngine()

            self.presidio_available = True
            print(f"✅ Presidio PII detection initialized")

        except Exception as e:
            print(f"⚠️  Warning: Failed to initialize Presidio: {e}")
            self.presidio_available = False
            self.analyzer = None
            self.anonymizer = None

    def redact(self, text: str, aggressive: bool = False) -> Dict:
        """
        Redact PII from text using Presidio + GLiNER and regex patterns.

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
                'has_pii': False,
                'redaction_count': 0
            }

        original_text = text
        redacted_text = text
        redactions = []

        # Step 1: Presidio-based detection (if available)
        if self.presidio_available and self.analyzer:
            try:
                # Analyze for PII
                analyzer_results = self.analyzer.analyze(
                    text=text,
                    language='en',
                    score_threshold=0.5  # Confidence threshold
                )

                # Filter out Federal Reserve related entities
                filtered_results = []
                for result in analyzer_results:
                    entity_text = text[result.start:result.end]

                    # Skip Federal Reserve terms
                    if self._is_federal_reserve_term(entity_text):
                        continue

                    # Skip financial terms for ORGANIZATION entities
                    if result.entity_type == 'ORGANIZATION' and self._is_financial_term(entity_text):
                        continue

                    # Skip locations that are part of Federal Reserve Bank names
                    if result.entity_type in ['LOCATION', 'GPE']:
                        start_context = max(0, result.start - 30)
                        end_context = min(len(text), result.end + 30)
                        context = text[start_context:end_context].lower()
                        if 'federal reserve bank of' in context:
                            continue

                    filtered_results.append(result)

                # Anonymize using Presidio (replaces with our custom labels)
                if filtered_results:
                    # Create operators config for custom replacements
                    operators = {}
                    for entity_type, replacement in self.entity_replacements.items():
                        operators[entity_type] = OperatorConfig("replace", {"new_value": replacement})

                    anonymized = self.anonymizer.anonymize(
                        text=text,
                        analyzer_results=filtered_results,
                        operators=operators
                    )

                    redacted_text = anonymized.text

                    # Build redactions list
                    for item in anonymized.items:
                        redactions.append({
                            'type': f'presidio_{item.entity_type.lower()}',
                            'value': item.text if hasattr(item, 'text') else original_text[item.start:item.end],
                            'start': item.start,
                            'end': item.end,
                            'replacement': item.text if hasattr(item, 'text') else self.entity_replacements.get(item.entity_type, '[REDACTED]')
                        })

            except Exception as e:
                print(f"⚠️  Warning: Presidio analysis failed: {e}")
                print(f"   Falling back to regex-only detection...")

        # Step 2: Regex-based redaction (fallback + additional patterns)
        # Apply to current redacted_text to catch anything Presidio missed
        for pii_type, config in self.patterns.items():
            matches = list(config['pattern'].finditer(redacted_text))
            for match in reversed(matches):  # Reverse to maintain indices
                matched_text = match.group()

                # Check if this area was already redacted
                if matched_text.startswith('[REDACTED'):
                    continue

                redactions.append({
                    'type': f'regex_{pii_type}',
                    'value': matched_text,
                    'start': match.start(),
                    'end': match.end(),
                    'replacement': config['replacement']
                })
                redacted_text = (
                    redacted_text[:match.start()] +
                    config['replacement'] +
                    redacted_text[match.end():]
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
            # Clean up type names for display
            clean_type = rtype.replace('presidio_', '').replace('regex_', '').replace('_', ' ').title()
            redaction_types[clean_type] = redaction_types.get(clean_type, 0) + 1

        summary_parts = []
        for rtype, count in redaction_types.items():
            summary_parts.append(f"{count} {rtype}{'s' if count > 1 else ''}")

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
    print("PII REDACTION TESTS (Presidio + GLiNER)")
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
