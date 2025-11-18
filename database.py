"""
Database connection and operations for RAG system.
"""
import os
import json
import psycopg2
from psycopg2.extras import RealDictCursor, execute_values
from typing import List, Dict, Optional, Any
from dotenv import load_dotenv
import numpy as np
from urllib.parse import urlparse

load_dotenv()


class Database:
    """Database connection and query handler."""

    def __init__(self):
        """Initialize database connection."""
        # Check DATABASE_MODE to determine which database to use
        db_mode = os.getenv('DATABASE_MODE', 'local').lower()

        if db_mode == 'supabase':
            # Use Supabase
            supabase_url = os.getenv('SUPABASE_URL')
            if not supabase_url:
                raise ValueError("SUPABASE_URL not set in .env file")

            # Parse the Supabase URL
            parsed = urlparse(supabase_url)
            self.conn_params = {
                'host': parsed.hostname,
                'port': parsed.port,
                'database': parsed.path[1:],  # Remove leading '/'
                'user': parsed.username,
                'password': parsed.password
            }
            self.db_mode = 'supabase'
        else:
            # Use local PostgreSQL (default)
            self.conn_params = {
                'host': os.getenv('LOCAL_DB_HOST', 'localhost'),
                'port': os.getenv('LOCAL_DB_PORT', '5433'),
                'database': os.getenv('LOCAL_DB_NAME', 'rag_system'),
                'user': os.getenv('LOCAL_DB_USER', 'rag_user'),
                'password': os.getenv('LOCAL_DB_PASSWORD', '')
            }
            self.db_mode = 'local'

        self.conn = None
        self.cursor = None

    def connect(self):
        """Establish database connection."""
        if not self.conn or self.conn.closed:
            # conn_params is now always a dict
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

    def add_query(self, query_text: str, query_embedding: np.ndarray, category: Optional[str] = None,
                  has_pii: bool = False, redaction_count: int = 0,
                  redaction_details: Optional[Dict] = None) -> int:
        """
        Store a query in the database with PII redaction tracking.

        IMPORTANT: Only the redacted query is stored. Original queries with PII
        are NEVER stored in the database for privacy protection.

        Args:
            query_text: Redacted query text (PII already removed if present)
            query_embedding: Query embedding vector
            category: Query category
            has_pii: Whether PII was detected and redacted
            redaction_count: Number of PII items redacted
            redaction_details: Details of redactions (types, not values)

        Returns:
            Query ID
        """
        self.connect()

        query = """
            INSERT INTO queries (query_text, query_embedding, category,
                               has_pii, redaction_count, redaction_details)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id;
        """
        self.cursor.execute(query, (
            query_text,  # Always redacted if PII was present
            query_embedding.tolist(),
            category,
            has_pii,
            redaction_count,
            json.dumps(redaction_details) if redaction_details else None
        ))
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

    def add_feedback(self, response_id: int, rating: int, comment: Optional[str] = None,
                     analysis: Optional[Dict] = None) -> int:
        """Add user feedback for a response with optional comment analysis."""
        self.connect()

        if not (1 <= rating <= 5):
            raise ValueError("Rating must be between 1 and 5")

        if analysis:
            # Convert sentiment_score (float) to sentiment (string) if needed
            sentiment = analysis.get('sentiment')
            if not sentiment and 'sentiment_score' in analysis:
                score = analysis['sentiment_score']
                if score > 0.2:
                    sentiment = 'positive'
                elif score < -0.2:
                    sentiment = 'negative'
                else:
                    sentiment = 'neutral'
            else:
                sentiment = sentiment or 'neutral'

            query = """
                INSERT INTO feedback (response_id, rating, comment, sentiment,
                                    issues, severity, confidence, summary)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id;
            """
            self.cursor.execute(query, (
                response_id, rating, comment,
                sentiment,
                analysis.get('issues', analysis.get('issue_types', [])),
                analysis.get('severity', 'none'),
                analysis.get('confidence', 0.0),
                analysis.get('summary', analysis.get('analysis_summary', ''))
            ))
        else:
            query = """
                INSERT INTO feedback (response_id, rating, comment)
                VALUES (%s, %s, %s)
                RETURNING id;
            """
            self.cursor.execute(query, (response_id, rating, comment))

        feedback_id = self.cursor.fetchone()['id']
        self.conn.commit()

        return feedback_id

    def update_feedback_analysis(self, feedback_id: int, analysis: Dict) -> None:
        """Update feedback with comment analysis results."""
        self.connect()

        # Convert sentiment_score (float) to sentiment (string) if needed
        sentiment = analysis.get('sentiment')
        if not sentiment and 'sentiment_score' in analysis:
            score = analysis['sentiment_score']
            if score > 0.2:
                sentiment = 'positive'
            elif score < -0.2:
                sentiment = 'negative'
            else:
                sentiment = 'neutral'
        else:
            sentiment = sentiment or 'neutral'

        query = """
            UPDATE feedback
            SET sentiment = %s,
                issues = %s,
                severity = %s,
                confidence = %s,
                summary = %s
            WHERE id = %s;
        """
        self.cursor.execute(query, (
            sentiment,
            analysis.get('issues', analysis.get('issue_types', [])),
            analysis.get('severity', 'none'),
            analysis.get('confidence', 0.0),
            analysis.get('summary', analysis.get('analysis_summary', '')),
            feedback_id
        ))
        self.conn.commit()

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
        """Get all feedback for a specific response with analysis."""
        self.connect()

        query = """
            SELECT id, rating, comment, created_at, sentiment,
                   issues, severity, confidence, summary
            FROM feedback
            WHERE response_id = %s
            ORDER BY created_at DESC;
        """
        self.cursor.execute(query, (response_id,))
        return self.cursor.fetchall()

    def calculate_document_feedback_scores(self, use_enhanced_scores: bool = True):
        """Recalculate feedback scores for all documents based on user ratings and comment analysis."""
        self.connect()

        if use_enhanced_scores:
            # Use enhanced scores that combine rating and sentiment analysis
            query = """
                WITH doc_feedback AS (
                    SELECT
                        UNNEST(r.retrieved_doc_ids) as doc_id,
                        AVG(f.rating) as avg_rating,
                        AVG(
                            CASE
                                WHEN f.sentiment IS NOT NULL AND f.confidence > 0.3 THEN
                                    -- Combine rating and sentiment with severity penalties
                                    -- Convert sentiment VARCHAR to numeric score
                                    0.7 * ((f.rating - 3.0) / 2.0) +
                                    0.3 * (CASE f.sentiment
                                        WHEN 'positive' THEN 1.0
                                        WHEN 'negative' THEN -1.0
                                        WHEN 'neutral' THEN 0.0
                                        ELSE 0.0
                                    END) * f.confidence +
                                    CASE f.severity
                                        WHEN 'minor' THEN -0.1
                                        WHEN 'moderate' THEN -0.3
                                        WHEN 'severe' THEN -0.5
                                        ELSE 0.0
                                    END
                                ELSE
                                    (f.rating - 3.0) / 2.0  -- Fallback to rating-based
                            END
                        ) as enhanced_score,
                        COUNT(f.id) as feedback_count
                    FROM responses r
                    JOIN feedback f ON f.response_id = r.id
                    WHERE r.retrieved_doc_ids IS NOT NULL
                    GROUP BY UNNEST(r.retrieved_doc_ids)
                )
                INSERT INTO document_scores (document_id, feedback_score, enhanced_feedback_score, last_updated)
                SELECT doc_id, COALESCE(avg_rating - 3.0) / 2.0, COALESCE(enhanced_score, 0.0), CURRENT_TIMESTAMP
                FROM doc_feedback
                ON CONFLICT (document_id) DO UPDATE
                SET feedback_score = EXCLUDED.feedback_score,
                    enhanced_feedback_score = EXCLUDED.enhanced_feedback_score,
                    last_updated = EXCLUDED.last_updated;
            """
        else:
            # Original rating-only method
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
                INSERT INTO document_scores (document_id, feedback_score, last_updated)
                SELECT doc_id, COALESCE((avg_rating - 3.0) / 2.0, 0.0), CURRENT_TIMESTAMP
                FROM doc_feedback
                ON CONFLICT (document_id) DO UPDATE
                SET feedback_score = EXCLUDED.feedback_score,
                    last_updated = EXCLUDED.last_updated;
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

    def get_category_statistics(self) -> List[Dict]:
        """Get query statistics by category."""
        self.connect()

        query = """
            SELECT
                category,
                COUNT(*) as count
            FROM queries
            WHERE category IS NOT NULL
            GROUP BY category
            ORDER BY count DESC;
        """
        self.cursor.execute(query)
        return self.cursor.fetchall()

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
                COUNT(f.id) as feedback_count,
                COUNT(f.comment) FILTER (WHERE f.comment IS NOT NULL AND f.comment != '') as comments_count,
                array_agg(
                    CASE
                        WHEN f.id IS NOT NULL
                        THEN jsonb_build_object(
                            'rating', f.rating,
                            'comment', COALESCE(f.comment, ''),
                            'created_at', f.created_at,
                            'sentiment', f.sentiment,
                            'severity', f.severity,
                            'issues', f.issues,
                            'has_comment', f.comment IS NOT NULL AND f.comment != ''
                        )
                        ELSE NULL
                    END
                ) FILTER (WHERE f.id IS NOT NULL) as all_feedback
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

    def delete_all_user_data(self) -> Dict[str, int]:
        """
        Delete ALL user data including responses, queries, feedback, and feedback-derived data.
        This also removes document review flags and resets document scores.
        Returns a dictionary with counts of deleted records.

        WARNING: This is a destructive operation and cannot be undone!
        """
        self.connect()

        deleted_counts = {
            'feedback': 0,
            'responses': 0,
            'queries': 0,
            'document_flags': 0,
            'document_scores': 0
        }

        try:
            # Delete in order of foreign key dependencies
            # 1. Delete feedback (references responses)
            self.cursor.execute("DELETE FROM feedback;")
            deleted_counts['feedback'] = self.cursor.rowcount

            # 2. Delete responses (references queries)
            self.cursor.execute("DELETE FROM responses;")
            deleted_counts['responses'] = self.cursor.rowcount

            # 3. Delete queries (no dependencies)
            self.cursor.execute("DELETE FROM queries;")
            deleted_counts['queries'] = self.cursor.rowcount

            # 4. Delete document review flags (feedback-derived)
            self.cursor.execute("DELETE FROM document_review_flags;")
            deleted_counts['document_flags'] = self.cursor.rowcount

            # 5. Reset document scores (remove feedback-based rankings)
            self.cursor.execute("DELETE FROM document_scores;")
            deleted_counts['document_scores'] = self.cursor.rowcount

            self.conn.commit()
            return deleted_counts
        except Exception as e:
            self.conn.rollback()
            print(f"Error deleting all user data: {e}")
            raise

    def get_feedback_needing_review(self) -> List[Dict]:
        """Get all feedback marked as needing review (severe or moderate severity)."""
        self.connect()

        query = """
            SELECT
                f.id,
                f.response_id,
                f.rating,
                f.comment,
                f.issues,
                f.severity,
                f.summary,
                f.created_at,
                r.response_text,
                r.retrieved_doc_ids,
                q.query_text
            FROM feedback f
            JOIN responses r ON f.response_id = r.id
            JOIN queries q ON r.query_id = q.id
            WHERE f.severity IN ('severe', 'moderate')
            ORDER BY f.created_at DESC;
        """
        self.cursor.execute(query)
        return self.cursor.fetchall()

    def flag_document_for_review(self, document_id: int, reason: str,
                                 common_issues: List, severity_dist: Dict,
                                 total_feedbacks: int) -> int:
        """Flag a document for manual review based on feedback patterns."""
        self.connect()

        query = """
            INSERT INTO document_review_flags
            (document_id, reason, common_issues, severity_distribution, total_feedbacks)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (document_id) DO UPDATE
            SET reason = EXCLUDED.reason,
                common_issues = EXCLUDED.common_issues,
                severity_distribution = EXCLUDED.severity_distribution,
                total_feedbacks = EXCLUDED.total_feedbacks,
                flagged_at = CURRENT_TIMESTAMP
            RETURNING id;
        """
        self.cursor.execute(query, (
            document_id, reason,
            json.dumps(common_issues),
            json.dumps(severity_dist),
            total_feedbacks
        ))
        flag_id = self.cursor.fetchone()['id']
        self.conn.commit()
        return flag_id

    def get_documents_needing_review(self, status: str = 'pending') -> List[Dict]:
        """Get documents flagged for review."""
        self.connect()

        query = """
            SELECT
                drf.id,
                drf.document_id,
                drf.flagged_at,
                drf.reason,
                drf.common_issues,
                drf.severity_distribution,
                drf.total_feedbacks,
                drf.status,
                d.content,
                d.metadata
            FROM document_review_flags drf
            JOIN documents d ON drf.document_id = d.id
            WHERE drf.status = %s
            ORDER BY drf.flagged_at DESC;
        """
        self.cursor.execute(query, (status,))
        return self.cursor.fetchall()

    def update_review_flag_status(self, flag_id: int, status: str, notes: Optional[str] = None) -> None:
        """Update the status of a document review flag."""
        self.connect()

        query = """
            UPDATE document_review_flags
            SET status = %s,
                reviewed_at = CURRENT_TIMESTAMP,
                reviewer_notes = %s
            WHERE id = %s;
        """
        self.cursor.execute(query, (status, notes, flag_id))
        self.conn.commit()

    def get_feedback_by_issue_type(self, issue_type: str) -> List[Dict]:
        """Get all feedback containing a specific issue type."""
        self.connect()

        query = """
            SELECT
                f.id,
                f.rating,
                f.comment,
                f.severity,
                f.summary,
                f.created_at,
                r.response_text,
                r.retrieved_doc_ids,
                q.query_text
            FROM feedback f
            JOIN responses r ON f.response_id = r.id
            JOIN queries q ON r.query_id = q.id
            WHERE %s = ANY(f.issues)
            ORDER BY f.created_at DESC;
        """
        self.cursor.execute(query, (issue_type,))
        return self.cursor.fetchall()
