"""
Database connection and operations for RAG system.
"""
import os
import psycopg2
from psycopg2.extras import RealDictCursor, execute_values
from typing import List, Dict, Optional, Any
from dotenv import load_dotenv
import numpy as np

load_dotenv()


class Database:
    """Database connection and query handler."""

    def __init__(self):
        """Initialize database connection."""
        self.conn_params = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': os.getenv('DB_PORT', '5432'),
            'database': os.getenv('DB_NAME', 'rag_system'),
            'user': os.getenv('DB_USER', 'rag_user'),
            'password': os.getenv('DB_PASSWORD', '')
        }
        self.conn = None
        self.cursor = None

    def connect(self):
        """Establish database connection."""
        if not self.conn or self.conn.closed:
            self.conn = psycopg2.connect(**self.conn_params)
            self.cursor = self.conn.cursor(cursor_factory=RealDictCursor)

    def close(self):
        """Close database connection."""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        if exc_type is None:
            self.conn.commit()
        else:
            self.conn.rollback()
        self.close()

    def add_document(self, content: str, embedding: np.ndarray, metadata: Optional[Dict] = None) -> int:
        """Add a document to the database."""
        self.connect()
        query = """
            INSERT INTO documents (content, embedding, metadata)
            VALUES (%s, %s, %s)
            RETURNING id;
        """
        self.cursor.execute(query, (content, embedding.tolist(), psycopg2.extras.Json(metadata or {})))
        doc_id = self.cursor.fetchone()['id']

        # Initialize document score
        score_query = """
            INSERT INTO document_scores (document_id, base_score, feedback_score)
            VALUES (%s, 1.0, 0.0)
            ON CONFLICT (document_id) DO NOTHING;
        """
        self.cursor.execute(score_query, (doc_id,))
        self.conn.commit()

        return doc_id

    def add_documents_batch(self, documents: List[Dict[str, Any]]) -> List[int]:
        """Add multiple documents in batch."""
        self.connect()

        doc_ids = []
        for doc in documents:
            doc_id = self.add_document(
                content=doc['content'],
                embedding=doc['embedding'],
                metadata=doc.get('metadata')
            )
            doc_ids.append(doc_id)

        return doc_ids

    def search_similar_documents(self, query_embedding: np.ndarray, top_k: int = 5) -> List[Dict]:
        """Search for similar documents using vector similarity with reranking scores."""
        self.connect()

        query = """
            SELECT
                d.id,
                d.content,
                d.metadata,
                d.created_at,
                COALESCE(ds.base_score, 1.0) as base_score,
                COALESCE(ds.feedback_score, 0.0) as feedback_score,
                (COALESCE(ds.base_score, 1.0) * (1 + %s * COALESCE(ds.feedback_score, 0.0))) as final_score,
                (1 - (d.embedding <=> %s::vector)) as similarity
            FROM documents d
            LEFT JOIN document_scores ds ON d.id = ds.document_id
            ORDER BY (1 - (d.embedding <=> %s::vector)) * (COALESCE(ds.base_score, 1.0) * (1 + %s * COALESCE(ds.feedback_score, 0.0))) DESC
            LIMIT %s;
        """

        feedback_weight = float(os.getenv('FEEDBACK_WEIGHT', '0.3'))
        embedding_list = query_embedding.tolist()

        self.cursor.execute(query, (feedback_weight, embedding_list, embedding_list, feedback_weight, top_k))
        return self.cursor.fetchall()

    def add_query(self, query_text: str, query_embedding: np.ndarray) -> int:
        """Store a query in the database."""
        self.connect()

        query = """
            INSERT INTO queries (query_text, query_embedding)
            VALUES (%s, %s)
            RETURNING id;
        """
        self.cursor.execute(query, (query_text, query_embedding.tolist()))
        query_id = self.cursor.fetchone()['id']
        self.conn.commit()

        return query_id

    def add_response(self, query_id: int, response_text: str,
                     retrieved_doc_ids: List[int], model_version: str) -> int:
        """Store a response in the database."""
        self.connect()

        query = """
            INSERT INTO responses (query_id, response_text, retrieved_doc_ids, model_version)
            VALUES (%s, %s, %s, %s)
            RETURNING id;
        """
        self.cursor.execute(query, (query_id, response_text, retrieved_doc_ids, model_version))
        response_id = self.cursor.fetchone()['id']
        self.conn.commit()

        return response_id

    def add_feedback(self, response_id: int, rating: int, comment: Optional[str] = None) -> int:
        """Add user feedback for a response."""
        self.connect()

        if not (1 <= rating <= 5):
            raise ValueError("Rating must be between 1 and 5")

        query = """
            INSERT INTO feedback (response_id, rating, comment)
            VALUES (%s, %s, %s)
            RETURNING id;
        """
        self.cursor.execute(query, (response_id, rating, comment))
        feedback_id = self.cursor.fetchone()['id']
        self.conn.commit()

        return feedback_id

    def get_response(self, response_id: int) -> Optional[Dict]:
        """Get a response by ID with query information."""
        self.connect()

        query = """
            SELECT
                r.id,
                r.response_text,
                r.model_version,
                r.retrieved_doc_ids,
                r.created_at,
                q.query_text,
                q.id as query_id
            FROM responses r
            JOIN queries q ON r.query_id = q.id
            WHERE r.id = %s;
        """
        self.cursor.execute(query, (response_id,))
        return self.cursor.fetchone()

    def get_feedback_for_response(self, response_id: int) -> List[Dict]:
        """Get all feedback for a specific response."""
        self.connect()

        query = """
            SELECT id, rating, comment, created_at
            FROM feedback
            WHERE response_id = %s
            ORDER BY created_at DESC;
        """
        self.cursor.execute(query, (response_id,))
        return self.cursor.fetchall()

    def calculate_document_feedback_scores(self):
        """Recalculate feedback scores for all documents based on user ratings."""
        self.connect()

        # Calculate average rating for each document across all responses that used it
        query = """
            WITH doc_feedback AS (
                SELECT
                    UNNEST(r.retrieved_doc_ids) as doc_id,
                    AVG(f.rating) as avg_rating,
                    COUNT(f.id) as feedback_count
                FROM responses r
                JOIN feedback f ON f.response_id = r.id
                WHERE r.retrieved_doc_ids IS NOT NULL
                GROUP BY UNNEST(r.retrieved_doc_ids)
            )
            UPDATE document_scores ds
            SET
                feedback_score = COALESCE(
                    (df.avg_rating - 3.0) / 2.0,  -- Normalize: 5->1.0, 3->0.0, 1->-1.0
                    0.0
                ),
                last_updated = CURRENT_TIMESTAMP
            FROM doc_feedback df
            WHERE ds.document_id = df.doc_id;
        """
        self.cursor.execute(query)
        updated_count = self.cursor.rowcount
        self.conn.commit()

        return updated_count

    def get_analytics(self) -> Dict:
        """Get system analytics and performance metrics."""
        self.connect()

        analytics = {}

        # Total counts
        self.cursor.execute("SELECT COUNT(*) as count FROM documents;")
        analytics['total_documents'] = self.cursor.fetchone()['count']

        self.cursor.execute("SELECT COUNT(*) as count FROM queries;")
        analytics['total_queries'] = self.cursor.fetchone()['count']

        self.cursor.execute("SELECT COUNT(*) as count FROM responses;")
        analytics['total_responses'] = self.cursor.fetchone()['count']

        self.cursor.execute("SELECT COUNT(*) as count FROM feedback;")
        analytics['total_feedback'] = self.cursor.fetchone()['count']

        # Average rating
        self.cursor.execute("SELECT AVG(rating) as avg_rating FROM feedback;")
        result = self.cursor.fetchone()
        analytics['average_rating'] = float(result['avg_rating']) if result['avg_rating'] else 0.0

        # Recent feedback (last 7 days)
        self.cursor.execute("""
            SELECT AVG(rating) as avg_rating, COUNT(*) as count
            FROM feedback
            WHERE created_at > CURRENT_TIMESTAMP - INTERVAL '7 days';
        """)
        recent = self.cursor.fetchone()
        analytics['recent_avg_rating'] = float(recent['avg_rating']) if recent['avg_rating'] else 0.0
        analytics['recent_feedback_count'] = recent['count']

        # Top rated documents
        self.cursor.execute("""
            SELECT
                document_id,
                base_score,
                feedback_score,
                (base_score * (1 + %s * feedback_score)) as final_score
            FROM document_scores
            ORDER BY final_score DESC
            LIMIT 10;
        """, (float(os.getenv('FEEDBACK_WEIGHT', '0.3')),))
        analytics['top_documents'] = self.cursor.fetchall()

        return analytics

    def get_all_responses(self, limit: int = 100, offset: int = 0,
                          min_rating: Optional[int] = None,
                          max_rating: Optional[int] = None,
                          date_from: Optional[str] = None,
                          date_to: Optional[str] = None) -> List[Dict]:
        """Get all responses with optional filters."""
        self.connect()

        conditions = []
        params = []

        if min_rating is not None:
            conditions.append("f.rating >= %s")
            params.append(min_rating)

        if max_rating is not None:
            conditions.append("f.rating <= %s")
            params.append(max_rating)

        if date_from:
            conditions.append("r.created_at >= %s::timestamp")
            params.append(date_from)

        if date_to:
            conditions.append("r.created_at <= %s::timestamp")
            params.append(date_to)

        where_clause = " AND " + " AND ".join(conditions) if conditions else ""

        query = f"""
            SELECT
                r.id,
                r.response_text,
                r.model_version,
                r.created_at,
                q.query_text,
                q.id as query_id,
                COALESCE(AVG(f.rating), 0) as avg_rating,
                COUNT(f.id) as feedback_count
            FROM responses r
            JOIN queries q ON r.query_id = q.id
            LEFT JOIN feedback f ON f.response_id = r.id
            {where_clause}
            GROUP BY r.id, q.id, q.query_text
            ORDER BY r.created_at DESC
            LIMIT %s OFFSET %s;
        """

        params.extend([limit, offset])
        self.cursor.execute(query, params)
        return self.cursor.fetchall()

    def delete_response(self, response_id: int) -> bool:
        """Delete a response and its associated feedback."""
        self.connect()

        try:
            # Delete feedback first (foreign key constraint)
            self.cursor.execute("DELETE FROM feedback WHERE response_id = %s;", (response_id,))

            # Delete the response
            self.cursor.execute("DELETE FROM responses WHERE id = %s;", (response_id,))

            self.conn.commit()
            return True
        except Exception as e:
            self.conn.rollback()
            print(f"Error deleting response {response_id}: {e}")
            return False

    def delete_responses_batch(self, response_ids: List[int]) -> int:
        """Delete multiple responses and their feedback."""
        self.connect()

        try:
            # Delete feedback first
            self.cursor.execute(
                "DELETE FROM feedback WHERE response_id = ANY(%s);",
                (response_ids,)
            )

            # Delete responses
            self.cursor.execute(
                "DELETE FROM responses WHERE id = ANY(%s);",
                (response_ids,)
            )

            deleted_count = self.cursor.rowcount
            self.conn.commit()
            return deleted_count
        except Exception as e:
            self.conn.rollback()
            print(f"Error batch deleting responses: {e}")
            return 0

    def delete_old_responses(self, days: int) -> int:
        """Delete responses older than specified days."""
        self.connect()

        try:
            # First delete feedback for old responses
            self.cursor.execute("""
                DELETE FROM feedback
                WHERE response_id IN (
                    SELECT id FROM responses
                    WHERE created_at < CURRENT_TIMESTAMP - INTERVAL '%s days'
                );
            """, (days,))

            # Then delete old responses
            self.cursor.execute("""
                DELETE FROM responses
                WHERE created_at < CURRENT_TIMESTAMP - INTERVAL '%s days';
            """, (days,))

            deleted_count = self.cursor.rowcount
            self.conn.commit()
            return deleted_count
        except Exception as e:
            self.conn.rollback()
            print(f"Error deleting old responses: {e}")
            return 0
