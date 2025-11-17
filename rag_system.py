"""
Main RAG System implementation with Claude Sonnet 4 integration.
"""
import os
from typing import List, Dict, Optional, Any
from anthropic import Anthropic
from dotenv import load_dotenv

from database import Database
from embeddings import get_embedding_service
from feedback_analyzer import FeedbackAnalyzer
from pii_redactor import get_pii_redactor

load_dotenv()


class RAGSystem:
    """Retrieval Augmented Generation system using Claude Sonnet 4."""

    def __init__(self):
        """Initialize the RAG system."""
        # Initialize Claude client
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable not set")

        self.client = Anthropic(api_key=api_key)
        self.model = os.getenv('CLAUDE_MODEL', 'claude-sonnet-4-20250514')

        # Initialize embedding service
        self.embeddings = get_embedding_service()

        # Initialize database
        self.db = Database()

        # Initialize feedback analyzer
        self.feedback_analyzer = FeedbackAnalyzer()

        # Initialize PII redactor
        self.pii_redactor = get_pii_redactor()
        self.enable_pii_redaction = os.getenv('ENABLE_PII_REDACTION', 'true').lower() == 'true'

        print(f"RAG System initialized with model: {self.model}")
        print(f"PII Redaction: {'Enabled' if self.enable_pii_redaction else 'Disabled'}")

    def add_documents(self, documents: List[Dict[str, Any]]) -> List[int]:
        """
        Add documents to the knowledge base.

        Args:
            documents: List of documents with 'content' and optional 'metadata'.
                      Example: [{"content": "text", "metadata": {"source": "file.txt"}}]

        Returns:
            List of document IDs.
        """
        # Extract content for embedding
        contents = [doc['content'] for doc in documents]

        # Generate embeddings
        print(f"Generating embeddings for {len(documents)} documents...")
        embeddings = self.embeddings.embed_documents(contents)

        # Prepare documents with embeddings
        docs_with_embeddings = []
        for i, doc in enumerate(documents):
            docs_with_embeddings.append({
                'content': doc['content'],
                'embedding': embeddings[i],
                'metadata': doc.get('metadata', {})
            })

        # Store in database
        with self.db as db:
            doc_ids = db.add_documents_batch(docs_with_embeddings)

        print(f"Added {len(doc_ids)} documents to knowledge base")
        return doc_ids

    def query(self, query_text: str, top_k: int = 5, max_tokens: int = 2000) -> Dict[str, Any]:
        """
        Query the RAG system with PII redaction.

        Args:
            query_text: The user's question.
            top_k: Number of documents to retrieve.
            max_tokens: Maximum tokens for Claude response.

        Returns:
            Dictionary with response text, ID, metadata, and redaction info.
        """
        original_query = query_text
        redaction_result = None

        # Step 1: Redact PII from query
        if self.enable_pii_redaction:
            redaction_result = self.pii_redactor.redact(query_text)
            query_text = redaction_result['redacted_text']

            if redaction_result['has_pii']:
                print(f"⚠️  PII Detected: {self.pii_redactor.get_redaction_summary(redaction_result)}")
                print(f"Original query: {original_query}")
                print(f"Redacted query: {query_text}")
            else:
                print(f"Processing query: {query_text}")
        else:
            print(f"Processing query: {query_text}")

        # Detect query category (using redacted query)
        category = self._detect_category(query_text)
        print(f"Query category: {category}")

        # Generate query embedding (using redacted query)
        query_embedding = self.embeddings.embed_query(query_text)

        # Store query in database with redaction tracking
        # IMPORTANT: Only redacted query is stored. Original is NEVER stored.
        # Redaction details do NOT include actual PII values.
        with self.db as db:
            query_id = db.add_query(
                query_text=query_text,  # Redacted version only
                query_embedding=query_embedding,
                category=category,
                has_pii=redaction_result['has_pii'] if redaction_result else False,
                redaction_count=redaction_result['redaction_count'] if redaction_result else 0,
                redaction_details=self.pii_redactor.get_safe_redaction_details(redaction_result) if redaction_result else None
            )

            # Search for similar documents
            similar_docs = db.search_similar_documents(query_embedding, top_k=top_k)

        print(f"Retrieved {len(similar_docs)} relevant documents")

        # Build context from retrieved documents
        context = self._build_context(similar_docs)

        # Generate response with Claude
        response_text = self._generate_response(query_text, context, max_tokens)

        # Store response
        retrieved_doc_ids = [doc['id'] for doc in similar_docs]
        with self.db as db:
            response_id = db.add_response(
                query_id=query_id,
                response_text=response_text,
                retrieved_doc_ids=retrieved_doc_ids,
                model_version=self.model
            )

        return {
            'id': response_id,
            'text': response_text,
            'query_id': query_id,
            'retrieved_documents': similar_docs,
            'model': self.model,
            'category': category,  # Query category
            'redacted_query': query_text,  # The redacted query sent to Claude
            'has_pii': redaction_result['has_pii'] if redaction_result else False,
            'redaction_summary': self.pii_redactor.get_redaction_summary(redaction_result) if redaction_result else None
        }

    def _build_context(self, documents: List[Dict]) -> str:
        """Build context string from retrieved documents with source URLs."""
        if not documents:
            return "No relevant documents found."

        context_parts = []
        for i, doc in enumerate(documents, 1):
            # Extract source information
            source_url = doc.get('metadata', {}).get('source_url', '') if isinstance(doc.get('metadata'), dict) else ''
            source_title = doc.get('metadata', {}).get('source_title', '') if isinstance(doc.get('metadata'), dict) else ''

            # Build document header with source info
            header = f"Document {i}"
            if source_title:
                header += f" - {source_title}"
            if source_url:
                header += f"\nSource URL: {source_url}"

            context_parts.append(
                f"{header}\n{doc['content']}\n"
            )

        return "\n---\n".join(context_parts)

    def _detect_category(self, query_text: str) -> str:
        """Detect the category of a query using Claude."""
        category_prompt = """Classify this Federal Reserve related question into ONE of these categories:

- Interest Rates & Monetary Policy
- Banking System & Supervision
- Currency & Coin
- Employment & Economy
- Financial Stability
- Payment Systems
- Consumer Protection
- Federal Reserve Structure
- Complaints & Reporting
- Other

Question: {query}

Respond with ONLY the category name, nothing else."""

        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=50,
                messages=[
                    {"role": "user", "content": category_prompt.format(query=query_text)}
                ]
            )
            category = message.content[0].text.strip()
            return category
        except Exception as e:
            print(f"Error detecting category: {e}")
            return "Other"

    def _convert_headings_to_bold(self, text: str) -> str:
        """Convert markdown headings (h1-h6) to bold text for uniform font size."""
        import re

        # Replace headings with bold text
        # Match h1-h6 (# Header, ## Header, etc.) at the start of lines
        lines = text.split('\n')
        converted_lines = []

        for line in lines:
            # Check if line starts with markdown heading (1-6 #'s followed by space)
            match = re.match(r'^(#{1,6})\s+(.+)$', line)
            if match:
                # Convert to bold instead
                heading_text = match.group(2)
                converted_lines.append(f"**{heading_text}**")
            else:
                converted_lines.append(line)

        return '\n'.join(converted_lines)

    def _generate_response(self, query: str, context: str, max_tokens: int) -> str:
        """Generate response using Claude."""
        # Build prompt
        system_prompt = """You are a Federal Reserve information assistant providing formal, professional responses based on official Federal Reserve resources.

Format your responses in a clear, professional style similar to public correspondence:
- Start with a direct answer to the question
- Provide supporting details with inline citations
- Use markdown format for citations: [text](URL)
- Include specific URLs from the Source URL fields in your citations
- End with a summary or key takeaway if appropriate
- Do NOT use heading tags (h1-h6), use bold text instead for emphasis

Your answers are based only on official sources from federalreserve.gov. If the information isn't available in the provided context, clearly state this."""

        user_message = f"""Using the context documents below, please answer the following question. Include inline citations with links to the source URLs provided in each document.

Context Documents:
{context}

Question: {query}

Please provide a professional, well-structured response with inline citations linking to the relevant Federal Reserve sources. Use bold text for emphasis instead of headings to maintain uniform font size."""

        # Call Claude API
        print("Generating response with Claude...")
        message = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[
                {"role": "user", "content": user_message}
            ]
        )

        # Extract text from response
        response_text = message.content[0].text

        # Convert any headings to bold for uniform font size
        response_text = self._convert_headings_to_bold(response_text)

        return response_text

    def submit_feedback(self, response_id: int, rating: int, comment: Optional[str] = None,
                       analyze_comment: bool = True) -> int:
        """
        Submit user feedback for a response with optional comment analysis.

        Args:
            response_id: ID of the response to rate.
            rating: Rating from 1-5.
            comment: Optional text comment.
            analyze_comment: Whether to analyze the comment with AI (default True).

        Returns:
            Feedback ID.
        """
        analysis = None

        # Analyze comment if provided and analysis is enabled
        if comment and analyze_comment:
            try:
                # Get response and query text for context
                with self.db as db:
                    response_data = db.get_response(response_id)

                if response_data:
                    print("Analyzing feedback comment...")
                    analysis = self.feedback_analyzer.analyze_comment(
                        comment=comment,
                        rating=rating,
                        query_text=response_data['query_text'],
                        response_text=response_data['response_text']
                    )
                    print(f"  Sentiment: {analysis['sentiment_score']:.2f}, "
                          f"Severity: {analysis['severity']}, "
                          f"Issues: {', '.join(analysis['issue_types'][:3]) if analysis['issue_types'] else 'none'}")
            except Exception as e:
                print(f"Warning: Comment analysis failed: {e}")
                analysis = None

        # Store feedback with analysis
        with self.db as db:
            feedback_id = db.add_feedback(response_id, rating, comment, analysis)

        print(f"Feedback submitted: {rating}/5 stars")

        # Check if document should be flagged for review
        if analysis and analysis.get('needs_review'):
            self._check_document_review_flags(response_id)

        return feedback_id

    def _check_document_review_flags(self, response_id: int) -> None:
        """Check if documents from this response should be flagged for review."""
        try:
            with self.db as db:
                response_data = db.get_response(response_id)
                if not response_data or not response_data.get('retrieved_doc_ids'):
                    return

                # Get feedback for each document used in the response
                for doc_id in response_data['retrieved_doc_ids']:
                    # Get all feedback for responses that used this document
                    db.cursor.execute("""
                        SELECT f.*, r.retrieved_doc_ids
                        FROM feedback f
                        JOIN responses r ON f.response_id = r.id
                        WHERE %s = ANY(r.retrieved_doc_ids)
                        AND f.analyzed_at IS NOT NULL;
                    """, (doc_id,))
                    feedbacks = db.cursor.fetchall()

                    if feedbacks:
                        # Analyze patterns
                        patterns = self.feedback_analyzer.analyze_document_feedback_patterns(
                            [{'analysis': {
                                'issue_types': fb.get('issue_types', []),
                                'needs_review': fb.get('needs_review', False),
                                'severity': fb.get('severity', 'none')
                            }} for fb in feedbacks]
                        )

                        # Flag if needed
                        if patterns['needs_review']:
                            db.flag_document_for_review(
                                document_id=doc_id,
                                reason=patterns['review_reason'],
                                common_issues=patterns['common_issues'],
                                severity_dist=patterns['severity_distribution'],
                                total_feedbacks=patterns['total_feedbacks']
                            )
                            print(f"  ⚠️  Document {doc_id} flagged for review: {patterns['review_reason']}")
        except Exception as e:
            print(f"Warning: Could not check review flags: {e}")

    def rerank_documents(self, use_enhanced_scores: bool = True) -> int:
        """
        Recalculate document scores based on feedback and comment analysis.

        Args:
            use_enhanced_scores: Use enhanced scores that include comment analysis (default True).

        Returns:
            Number of documents updated.
        """
        mode = "enhanced (rating + comment analysis)" if use_enhanced_scores else "rating-only"
        print(f"Recalculating document scores using {mode} mode...")
        with self.db as db:
            updated_count = db.calculate_document_feedback_scores(use_enhanced_scores)

        print(f"Updated scores for {updated_count} documents")
        return updated_count

    def get_feedback_insights(self) -> Dict:
        """
        Get insights from feedback analysis.

        Returns:
            Dictionary containing feedback statistics and insights.
        """
        with self.db as db:
            # Get feedback needing review
            needs_review = db.get_feedback_needing_review()

            # Get documents needing review
            docs_needing_review = db.get_documents_needing_review('pending')

            # Count issues by type
            db.cursor.execute("""
                SELECT
                    UNNEST(issue_types) as issue,
                    COUNT(*) as count
                FROM feedback
                WHERE issue_types IS NOT NULL AND array_length(issue_types, 1) > 0
                GROUP BY UNNEST(issue_types)
                ORDER BY count DESC;
            """)
            issue_counts = db.cursor.fetchall()

            # Severity distribution
            db.cursor.execute("""
                SELECT severity, COUNT(*) as count
                FROM feedback
                WHERE severity IS NOT NULL
                GROUP BY severity
                ORDER BY count DESC;
            """)
            severity_dist = db.cursor.fetchall()

            return {
                'feedback_needing_review': len(needs_review),
                'documents_needing_review': len(docs_needing_review),
                'issue_type_distribution': issue_counts,
                'severity_distribution': severity_dist,
                'feedback_samples': needs_review[:5]  # Top 5 samples
            }

    def get_response(self, response_id: int) -> Optional[Dict]:
        """
        Get a specific response by ID.

        Args:
            response_id: Response ID.

        Returns:
            Response data or None if not found.
        """
        with self.db as db:
            return db.get_response(response_id)

    def get_analytics(self) -> Dict:
        """
        Get system analytics.

        Returns:
            Dictionary with analytics data.
        """
        with self.db as db:
            return db.get_analytics()
