"""
Main RAG System implementation with Claude Sonnet 4 integration.
"""
import os
from typing import List, Dict, Optional, Any
from anthropic import Anthropic
from dotenv import load_dotenv

from database import Database
from embeddings import get_embedding_service

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

        print(f"RAG System initialized with model: {self.model}")

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
        Query the RAG system.

        Args:
            query_text: The user's question.
            top_k: Number of documents to retrieve.
            max_tokens: Maximum tokens for Claude response.

        Returns:
            Dictionary with response text, ID, and metadata.
        """
        print(f"Processing query: {query_text}")

        # Detect query category
        category = self._detect_category(query_text)
        print(f"Query category: {category}")

        # Generate query embedding
        query_embedding = self.embeddings.embed_query(query_text)

        # Store query in database with category
        with self.db as db:
            query_id = db.add_query(query_text, query_embedding, category)

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
            'model': self.model
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

Your answers are based only on official sources from federalreserve.gov. If the information isn't available in the provided context, clearly state this."""

        user_message = f"""Using the context documents below, please answer the following question. Include inline citations with links to the source URLs provided in each document.

Context Documents:
{context}

Question: {query}

Please provide a professional, well-structured response with inline citations linking to the relevant Federal Reserve sources."""

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
        return response_text

    def submit_feedback(self, response_id: int, rating: int, comment: Optional[str] = None) -> int:
        """
        Submit user feedback for a response.

        Args:
            response_id: ID of the response to rate.
            rating: Rating from 1-5.
            comment: Optional text comment.

        Returns:
            Feedback ID.
        """
        with self.db as db:
            feedback_id = db.add_feedback(response_id, rating, comment)

        print(f"Feedback submitted: {rating}/5 stars")
        return feedback_id

    def rerank_documents(self) -> int:
        """
        Recalculate document scores based on feedback.

        Returns:
            Number of documents updated.
        """
        print("Recalculating document scores based on user feedback...")
        with self.db as db:
            updated_count = db.calculate_document_feedback_scores()

        print(f"Updated scores for {updated_count} documents")
        return updated_count

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
