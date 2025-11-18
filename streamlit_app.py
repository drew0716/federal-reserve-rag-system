"""
Streamlit interface for RAG System
Provides query interface, feedback collection, and analytics dashboard
"""
import streamlit as st
import os
from datetime import datetime
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from rag_system import RAGSystem
from database import Database
import subprocess
from pathlib import Path
from st_copy import copy_button

# Load environment variables
load_dotenv()

# Page configuration
st.set_page_config(
    page_title="Federal Reserve Correspondence System",
    page_icon="📝",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Database connection helper
def get_db_connection():
    """Get a new database connection using DATABASE_MODE switcher."""
    from urllib.parse import urlparse

    db_mode = os.getenv('DATABASE_MODE', 'local').lower()

    if db_mode == 'supabase':
        # Use Supabase
        supabase_url = os.getenv('SUPABASE_URL')
        if not supabase_url:
            raise ValueError("SUPABASE_URL not set in .env file")

        # Parse the Supabase URL
        parsed = urlparse(supabase_url)
        return psycopg2.connect(
            host=parsed.hostname,
            port=parsed.port,
            database=parsed.path[1:],  # Remove leading '/'
            user=parsed.username,
            password=parsed.password
        )
    else:
        # Use local PostgreSQL (default)
        return psycopg2.connect(
            host=os.getenv('LOCAL_DB_HOST', 'localhost'),
            port=os.getenv('LOCAL_DB_PORT', '5433'),
            database=os.getenv('LOCAL_DB_NAME', 'rag_system'),
            user=os.getenv('LOCAL_DB_USER', 'rag_user'),
            password=os.getenv('LOCAL_DB_PASSWORD', '')
        )

# Initialize RAG system
@st.cache_resource
def get_rag_system():
    """Initialize RAG system."""
    return RAGSystem()

# Generate diagrams helper
def ensure_diagrams_exist():
    """Generate pipeline diagrams if they don't exist."""
    diagram_files = [
        'rag_architecture.png',
        'rag_query_flow.png',
        'rag_content_pipeline.png'
    ]

    # Check if any diagrams are missing
    missing = [f for f in diagram_files if not Path(f).exists()]

    if missing:
        try:
            # Run the diagram generation script
            subprocess.run(['python3', 'generate_pipeline_diagram.py'],
                         check=True,
                         capture_output=True,
                         timeout=30)
            return True
        except Exception as e:
            st.warning(f"Could not generate diagrams: {e}")
            return False
    return True

# Custom CSS
st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        margin-bottom: 1rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    .response-box {
        background-color: #f8f9fa;
        padding: 1.5rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
        margin: 1rem 0;
    }
    .feedback-box {
        background-color: #fff3cd;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    </style>
""", unsafe_allow_html=True)

def query_page():
    """Main query and response interface."""
    st.markdown('<div class="main-header">📝 Public Correspondence Response System</div>', unsafe_allow_html=True)

    st.markdown("""
    Submit inquiries about Federal Reserve policies, operations, and monetary policy.
    Responses are generated based on official Federal Reserve sources and documentation.
    """)

    # Initialize session state for question
    if 'question_input' not in st.session_state:
        st.session_state.question_input = ""

    # Query input
    query = st.text_area(
        "**Your Question:**",
        height=120,
        value=st.session_state.question_input,
        placeholder="e.g., How does the Federal Reserve influence interest rates?",
        key="query_input",
        help="Enter your question about Federal Reserve policies, monetary policy, or operations"
    )

    # Fixed parameters (tuned for better retrieval)
    top_k = 10  # Retrieve top 10 most relevant documents (more context)
    max_tokens = 2000  # Allow detailed responses

    if st.button("🔍 Submit Inquiry", type="primary", use_container_width=True):
        if not query.strip():
            st.warning("Please enter a question.")
            return

        with st.spinner("Generating response..."):
            try:
                rag = get_rag_system()
                response = rag.query(query, top_k=top_k, max_tokens=max_tokens)

                # Store complete response data in session state
                st.session_state.current_response = {
                    'id': response['id'],
                    'query_id': response['query_id'],
                    'text': response['text'],
                    'query': query,
                    'redacted_query': response.get('redacted_query', query),
                    'has_pii': response.get('has_pii', False),
                    'redaction_summary': response.get('redaction_summary'),
                    'category': response.get('category'),
                    'retrieved_documents': response['retrieved_documents'],
                    'model': response['model']
                }

            except Exception as e:
                st.error(f"Error generating response: {e}")
                return

    # Display response if available (persists across reruns)
    if 'current_response' in st.session_state:
        response = st.session_state.current_response

        # Display redacted query notice if PII was detected
        st.markdown("---")
        if response.get('has_pii'):
            st.warning(f"🔒 **Privacy Protection:** {response.get('redaction_summary')}")
            st.markdown("**Your Question (redacted):**")
            st.info(response.get('redacted_query', response['query']))
            st.caption("_For your privacy, sensitive information has been redacted before processing. The redacted version was sent to Claude._")
        else:
            st.markdown("**Your Question:**")
            st.info(response['query'])

        # Display category tag if available
        if response.get('category'):
            st.markdown(f"**Category:** :blue-background[{response['category']}]")

        # Display response section
        st.markdown("---")

        # Header with copy button
        col1, col2 = st.columns([6, 1])
        with col1:
            st.markdown("**📝 Response**")
        with col2:
            copy_button(response['text'], key=f"copy_{response['id']}")

        # Display the response in a clean container
        st.markdown('<div class="response-box">', unsafe_allow_html=True)
        st.markdown(response['text'])
        st.markdown('</div>', unsafe_allow_html=True)

        # Show retrieved documents
        st.markdown("---")
        with st.expander("📚 View Retrieved Documents"):
            for i, doc in enumerate(response['retrieved_documents'], 1):
                st.markdown(f"#### Document {i}")
                st.markdown(f"**Similarity Score:** {doc['similarity']:.3f}")
                with st.container():
                    st.text(doc['content'][:500] + "..." if len(doc['content']) > 500 else doc['content'])
                if i < len(response['retrieved_documents']):
                    st.divider()

        # Metadata
        with st.expander("ℹ️ Response Metadata"):
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Query ID", response['query_id'])
            with col2:
                st.metric("Response ID", response['id'])
            with col3:
                st.metric("Documents Retrieved", len(response['retrieved_documents']))

        # Rating section (show immediately after response)
        st.markdown("---")
        st.markdown("**📊 Rate this Response**")

        col1, col2 = st.columns([1, 2])
        with col1:
            rating = st.select_slider(
                "Rating",
                options=[1, 2, 3, 4, 5],
                value=3,
                format_func=lambda x: "⭐" * x,
                key=f"rating_{response['id']}"
            )

        with col2:
            comment = st.text_area(
                "Additional feedback (optional)",
                height=100,
                placeholder="What did you think of this response?",
                key=f"comment_{response['id']}"
            )

        if st.button("Submit Rating", type="secondary", key=f"submit_rating_{response['id']}"):
            try:
                # Use RAG system to submit feedback with AI analysis
                with st.spinner("Submitting feedback..."):
                    rag = get_rag_system()
                    feedback_id = rag.submit_feedback(
                        response_id=response['id'],
                        rating=rating,
                        comment=comment if comment else None,
                        analyze_comment=True  # Enable AI analysis
                    )

                st.success(f"✅ Thank you for your feedback! (ID: {feedback_id})")

                # Clear the response after successful feedback
                del st.session_state.current_response
                st.rerun()

            except Exception as e:
                st.error(f"Error submitting feedback: {e}")
                import traceback
                st.code(traceback.format_exc())

def review_page():
    """Review and rate unrated responses."""
    st.markdown('<div class="main-header">📝 Review Unrated Responses</div>', unsafe_allow_html=True)

    st.markdown("""
    Review previous responses that haven't been rated yet.
    Your feedback helps improve the system!
    """)

    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Get unrated responses
        cursor.execute("""
            SELECT
                r.id as response_id,
                q.query_text,
                r.response_text,
                r.created_at,
                r.model_version
            FROM responses r
            JOIN queries q ON r.query_id = q.id
            LEFT JOIN feedback f ON r.id = f.response_id
            WHERE f.id IS NULL
            ORDER BY r.created_at DESC
            LIMIT 50
        """)

        unrated_responses = cursor.fetchall()
        cursor.close()
        conn.close()

        if not unrated_responses:
            st.info("🎉 All responses have been rated! Great job!")
            return

        st.info(f"Found {len(unrated_responses)} unrated responses")

        # Pagination
        if 'review_page' not in st.session_state:
            st.session_state.review_page = 0

        # Reset page if out of range (can happen after rating the last response)
        if st.session_state.review_page >= len(unrated_responses):
            st.session_state.review_page = max(0, len(unrated_responses) - 1)

        current_page = st.session_state.review_page
        response = unrated_responses[current_page]

        # Display response
        st.markdown(f"### Response {current_page + 1} of {len(unrated_responses)}")

        st.markdown(f"**Query:** {response['query_text']}")
        st.markdown(f"**Date:** {response['created_at'].strftime('%m/%d/%Y %I:%M %p')}")
        st.markdown(f"**Model:** {response['model_version']}")

        st.markdown('<div class="response-box">', unsafe_allow_html=True)
        st.markdown("**Response:**")
        st.write(response['response_text'])
        st.markdown('</div>', unsafe_allow_html=True)

        # Rating interface
        st.markdown("---")
        col1, col2 = st.columns([1, 2])

        with col1:
            rating = st.select_slider(
                "Rating",
                options=[1, 2, 3, 4, 5],
                value=3,
                format_func=lambda x: "⭐" * x,
                key=f"rating_{response['response_id']}"
            )

        with col2:
            comment = st.text_area(
                "Feedback (optional)",
                height=100,
                placeholder="What did you think of this response?",
                key=f"comment_{response['response_id']}"
            )

        # Navigation and submit buttons
        col1, col2, col3, col4 = st.columns([1, 1, 1, 1])

        with col1:
            if st.button("⬅️ Previous", disabled=(current_page == 0)):
                st.session_state.review_page = max(0, current_page - 1)
                st.rerun()

        with col2:
            if st.button("➡️ Next", disabled=(current_page >= len(unrated_responses) - 1)):
                st.session_state.review_page = min(len(unrated_responses) - 1, current_page + 1)
                st.rerun()

        with col3:
            if st.button("⏭️ Skip"):
                st.session_state.review_page = min(len(unrated_responses) - 1, current_page + 1)
                st.rerun()

        with col4:
            if st.button("✅ Submit Rating", type="primary"):
                try:
                    # Use RAG system to submit feedback with AI analysis
                    with st.spinner("Submitting feedback..."):
                        rag = get_rag_system()
                        feedback_id = rag.submit_feedback(
                            response_id=response['response_id'],
                            rating=rating,
                            comment=comment if comment else None,
                            analyze_comment=True  # Enable AI analysis
                        )

                    st.success(f"✅ Feedback submitted! (ID: {feedback_id})")
                    # Move to next response
                    if current_page < len(unrated_responses) - 1:
                        st.session_state.review_page = current_page + 1
                    st.rerun()

                except Exception as e:
                    st.error(f"Error submitting feedback: {e}")
                    import traceback
                    st.code(traceback.format_exc())

    except Exception as e:
        st.error(f"Error loading unrated responses: {e}")
        import traceback
        st.code(traceback.format_exc())

@st.dialog("Feedback Details", width="large")
def show_feedback_dialog(fb):
    """Show detailed feedback in a dialog."""
    # Display rating
    st.markdown(f"**Rating:** {'⭐' * fb['rating']} ({fb['rating']}/5)")

    st.markdown(f"**Query:** {fb['query_text']}")

    if fb['comment']:
        st.markdown("**Comment:**")
        st.info(fb['comment'])

    # Show analysis if available (support both old and new column names)
    summary = fb.get('summary') or fb.get('analysis_summary')
    if summary:
        st.markdown(f"**AI Analysis:** {summary}")

        issues = fb.get('issues') or fb.get('issue_types') or []
        if issues:
            issue_list = [i for i in issues if i != 'none']
            if issue_list:
                st.markdown(f"**Issues:** {', '.join(issue_list).replace('_', ' ').title()}")

        # Handle both string sentiment and numeric sentiment_score
        sentiment = fb.get('sentiment')
        if sentiment:
            st.markdown(f"**Sentiment:** {sentiment.title()}")
        elif fb.get('sentiment_score') is not None:
            score = fb['sentiment_score']
            sentiment_label = 'Positive' if score > 0.3 else 'Negative' if score < -0.3 else 'Neutral'
            st.markdown(f"**Sentiment:** {sentiment_label} ({score:.2f})")

    st.markdown("---")
    st.markdown("**Response:**")
    st.markdown(fb['response_text'])

def analytics_page():
    """Analytics and statistics dashboard."""
    st.markdown('<div class="main-header">📊 Analytics Dashboard</div>', unsafe_allow_html=True)

    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Overall metrics
        st.markdown("### 📈 Overall Metrics")

        col1, col2, col3, col4 = st.columns(4)

        # Total queries
        cursor.execute("SELECT COUNT(*) as count FROM queries")
        total_queries = cursor.fetchone()['count']
        col1.metric("Total Queries", total_queries)

        # Total responses
        cursor.execute("SELECT COUNT(*) as count FROM responses")
        total_responses = cursor.fetchone()['count']
        col2.metric("Total Responses", total_responses)

        # Average rating
        cursor.execute("SELECT AVG(rating) as avg_rating FROM feedback")
        avg_rating_result = cursor.fetchone()['avg_rating']
        avg_rating = float(avg_rating_result) if avg_rating_result else 0
        col3.metric("Average Rating", f"{avg_rating:.2f} ⭐")

        # Total feedback
        cursor.execute("SELECT COUNT(*) as count FROM feedback")
        total_feedback = cursor.fetchone()['count']
        col4.metric("Total Feedback", total_feedback)

        st.markdown("---")

        # Charts
        col1, col2 = st.columns(2)

        # Rating distribution
        with col1:
            st.markdown("### ⭐ Rating Distribution")
            cursor.execute("""
                SELECT rating, COUNT(*) as count
                FROM feedback
                GROUP BY rating
                ORDER BY rating
            """)
            rating_data = cursor.fetchall()

            if rating_data:
                df_ratings = pd.DataFrame(rating_data)
                fig = px.bar(
                    df_ratings,
                    x='rating',
                    y='count',
                    labels={'rating': 'Rating', 'count': 'Count'},
                    color='rating',
                    color_continuous_scale='Blues'
                )
                fig.update_layout(showlegend=False, height=400)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No ratings yet")

        # Queries over time
        with col2:
            st.markdown("### 📅 Queries Over Time")
            cursor.execute("""
                SELECT DATE(created_at) as date, COUNT(*) as count
                FROM queries
                GROUP BY DATE(created_at)
                ORDER BY date DESC
                LIMIT 30
            """)
            query_timeline = cursor.fetchall()

            if query_timeline:
                df_timeline = pd.DataFrame(query_timeline)
                df_timeline = df_timeline.sort_values('date')
                fig = px.line(
                    df_timeline,
                    x='date',
                    y='count',
                    labels={'date': 'Date', 'count': 'Queries'},
                    markers=True
                )
                fig.update_layout(height=400)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No query data yet")

        st.markdown("---")

        # Query categories
        st.markdown("### 📂 Query Categories")
        cursor.execute("""
            SELECT
                category,
                COUNT(*) as count
            FROM queries
            WHERE category IS NOT NULL
            GROUP BY category
            ORDER BY count DESC
        """)
        category_data = cursor.fetchall()

        if category_data:
            col1, col2 = st.columns([2, 1])

            with col1:
                df_categories = pd.DataFrame(category_data)
                fig = px.pie(
                    df_categories,
                    values='count',
                    names='category',
                    title='Distribution of Query Topics',
                    hole=0.3
                )
                fig.update_layout(height=400)
                st.plotly_chart(fig, use_container_width=True)

            with col2:
                st.markdown("**Category Breakdown:**")
                for cat in category_data:
                    st.markdown(f"- **{cat['category']}**: {cat['count']} queries")
        else:
            st.info("No categorized queries yet. Submit some inquiries to see category statistics!")

        st.markdown("---")

        # Feedback Insights
        st.markdown("### 🔍 Feedback Analysis Insights")

        col1, col2, col3 = st.columns(3)

        # Count analyzed feedback
        cursor.execute("SELECT COUNT(*) as count FROM feedback WHERE summary IS NOT NULL")
        analyzed_count = cursor.fetchone()['count']
        col1.metric("Analyzed Comments", analyzed_count)

        # Count feedback needing review (severe or moderate severity)
        cursor.execute("SELECT COUNT(*) as count FROM feedback WHERE severity IN ('severe', 'moderate')")
        needs_review_count = cursor.fetchone()['count']
        col2.metric("Comments Flagged", needs_review_count, help="Feedback requiring attention")

        # Count documents flagged for review
        cursor.execute("SELECT COUNT(*) as count FROM document_review_flags WHERE status = 'pending'")
        docs_flagged = cursor.fetchone()['count']
        col3.metric("Documents Flagged", docs_flagged, help="Documents needing manual review")

        if analyzed_count > 0:
            col1, col2 = st.columns(2)

            # Issue type distribution
            with col1:
                st.markdown("**Common Issues Identified:**")
                cursor.execute("""
                    SELECT
                        issue,
                        COUNT(*) as count
                    FROM feedback
                    CROSS JOIN UNNEST(issues) as issue
                    WHERE issues IS NOT NULL
                      AND array_length(issues, 1) > 0
                      AND issue != 'none'
                    GROUP BY issue
                    ORDER BY count DESC
                    LIMIT 8;
                """)
                issue_data = cursor.fetchall()

                if issue_data:
                    df_issues = pd.DataFrame(issue_data)
                    # Format issue names for display
                    df_issues['issue'] = df_issues['issue'].str.replace('_', ' ').str.title()
                    fig = px.bar(
                        df_issues,
                        x='count',
                        y='issue',
                        orientation='h',
                        labels={'count': 'Count', 'issue': 'Issue Type'},
                        color='count',
                        color_continuous_scale='Reds'
                    )
                    fig.update_layout(showlegend=False, height=300)
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No issues identified yet")

            # Severity distribution
            with col2:
                st.markdown("**Issue Severity Distribution:**")
                cursor.execute("""
                    SELECT severity, COUNT(*) as count
                    FROM feedback
                    WHERE severity IS NOT NULL AND severity != 'none'
                    GROUP BY severity
                    ORDER BY
                        CASE severity
                            WHEN 'severe' THEN 1
                            WHEN 'moderate' THEN 2
                            WHEN 'minor' THEN 3
                            ELSE 4
                        END;
                """)
                severity_data = cursor.fetchall()

                if severity_data:
                    df_severity = pd.DataFrame(severity_data)
                    df_severity['severity'] = df_severity['severity'].str.title()

                    # Custom colors for severity
                    colors = {'Severe': '#d62728', 'Moderate': '#ff7f0e', 'Minor': '#2ca02c'}
                    df_severity['color'] = df_severity['severity'].map(colors)

                    fig = px.pie(
                        df_severity,
                        values='count',
                        names='severity',
                        color='severity',
                        color_discrete_map=colors,
                        hole=0.4
                    )
                    fig.update_layout(height=300)
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No severity data yet")

        # Documents needing review
        if docs_flagged > 0:
            st.markdown("**📋 Documents Requiring Review:**")
            cursor.execute("""
                SELECT
                    drf.document_id,
                    drf.reason,
                    drf.total_feedbacks,
                    drf.flagged_at,
                    d.content,
                    d.metadata
                FROM document_review_flags drf
                JOIN documents d ON drf.document_id = d.id
                WHERE drf.status = 'pending'
                ORDER BY drf.flagged_at DESC
                LIMIT 5;
            """)
            flagged_docs = cursor.fetchall()

            for doc in flagged_docs:
                source_title = doc['metadata'].get('source_title', 'Unknown') if doc['metadata'] else 'Unknown'
                source_url = doc['metadata'].get('source_url', '') if doc['metadata'] else ''
                with st.expander(f"⚠️ Document #{doc['document_id']}: {source_title[:60]}..."):
                    st.markdown(f"**Reason:** {doc['reason']}")
                    st.markdown(f"**Total Feedback:** {doc['total_feedbacks']}")
                    st.markdown(f"**Flagged:** {doc['flagged_at'].strftime('%m/%d/%Y %I:%M %p')}")
                    st.markdown(f"**Content Preview:** {doc['content'][:300]}...")
                    if source_url:
                        st.markdown(f"**Source:** [{source_url}]({source_url})")

        st.markdown("---")

        # Recent feedback
        st.markdown("### 💬 Recent Feedback")
        cursor.execute("""
            SELECT
                f.rating,
                f.comment,
                f.created_at,
                f.sentiment,
                f.issues,
                f.severity,
                f.summary,
                q.query_text,
                r.response_text
            FROM feedback f
            JOIN responses r ON f.response_id = r.id
            JOIN queries q ON r.query_id = q.id
            ORDER BY f.created_at DESC
            LIMIT 10
        """)
        recent_feedback = cursor.fetchall()

        if recent_feedback:
            for i, fb in enumerate(recent_feedback):
                # Create title with severity indicator
                severity_emoji = ''
                if fb.get('severity') and fb['severity'] != 'none':
                    severity_emoji = {'minor': '⚡', 'moderate': '⚠️', 'severe': '🚨'}.get(fb['severity'], '') + ' '

                # Display as list item with button
                col1, col2 = st.columns([6, 1])
                with col1:
                    st.markdown(f"{severity_emoji}{'⭐' * fb['rating']} - {fb['created_at'].strftime('%m/%d/%Y %I:%M %p')}")
                    st.caption(f"{fb['query_text'][:100]}...")
                with col2:
                    if st.button("View", key=f"view_fb_{i}"):
                        show_feedback_dialog(fb)

                if i < len(recent_feedback) - 1:
                    st.divider()
        else:
            st.info("No feedback yet")

        # Top queries
        st.markdown("---")
        st.markdown("### 🔝 Most Common Queries")
        cursor.execute("""
            SELECT query_text, COUNT(*) as count
            FROM queries
            GROUP BY query_text
            HAVING COUNT(*) > 1
            ORDER BY count DESC
            LIMIT 10
        """)
        top_queries = cursor.fetchall()

        if top_queries:
            df_top = pd.DataFrame(top_queries)
            st.dataframe(df_top, use_container_width=True, hide_index=True)
        else:
            st.info("No repeated queries yet")

        cursor.close()
        conn.close()

    except Exception as e:
        st.error(f"Error loading analytics: {e}")

def source_management_page():
    """Manage external source content (Federal Reserve, etc.)."""
    st.markdown('<div class="main-header">📚 Source Content Management</div>', unsafe_allow_html=True)

    st.markdown("""
    Manage external content sources like Federal Reserve documents.
    This content is automatically refreshed and used to answer queries.
    """)

    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Source statistics
        st.markdown("### 📊 Content Sources")

        cursor.execute("""
            SELECT
                source_type,
                COUNT(*) as document_count,
                MAX(last_refreshed) as last_refresh,
                COUNT(DISTINCT source_url) as unique_urls
            FROM documents
            WHERE is_external_source = TRUE
            GROUP BY source_type
            ORDER BY source_type
        """)
        sources = cursor.fetchall()

        if sources:
            col1, col2, col3 = st.columns(3)

            total_docs = sum(s['document_count'] for s in sources)
            col1.metric("Total Source Documents", total_docs)
            col2.metric("Source Types", len(sources))

            # Most recent refresh
            most_recent = max((s['last_refresh'] for s in sources if s['last_refresh']), default=None)
            if most_recent:
                col3.metric("Last Refresh", most_recent.strftime('%m/%d/%Y %I:%M %p'))
            else:
                col3.metric("Last Refresh", "Never")

            # Sources table
            st.markdown("---")
            st.markdown("### 📋 Source Breakdown")
            df_sources = pd.DataFrame(sources)
            df_sources['last_refresh'] = df_sources['last_refresh'].apply(
                lambda x: x.strftime('%m/%d/%Y %I:%M %p') if x else 'Never'
            )
            st.dataframe(df_sources, use_container_width=True, hide_index=True)
        else:
            st.info("No external source content loaded yet.")

        # Refresh history
        st.markdown("---")
        st.markdown("### 📅 Refresh History")

        cursor.execute("""
            SELECT
                source_type,
                documents_added,
                documents_deleted,
                refresh_started,
                refresh_completed,
                status,
                error_message
            FROM source_refresh_log
            ORDER BY refresh_started DESC
            LIMIT 20
        """)
        refresh_log = cursor.fetchall()

        if refresh_log:
            for log in refresh_log:
                status_icon = "✅" if log['status'] == 'completed' else "❌" if log['status'] == 'failed' else "⏳"
                with st.expander(f"{status_icon} {log['source_type']} - {log['refresh_started'].strftime('%m/%d/%Y %I:%M %p')}"):
                    col1, col2, col3 = st.columns(3)
                    col1.metric("Added", log['documents_added'])
                    col2.metric("Deleted", log['documents_deleted'])
                    col3.metric("Status", log['status'])

                    if log['error_message']:
                        st.error(f"Error: {log['error_message']}")

                    if log['refresh_completed']:
                        duration = (log['refresh_completed'] - log['refresh_started']).total_seconds()
                        st.info(f"Duration: {duration:.1f} seconds")
        else:
            st.info("No refresh history yet")

        # Manual refresh controls
        st.markdown("---")
        st.markdown("### 🔄 Manual Refresh")

        st.warning("⚠️ Manual refresh will crawl Federal Reserve website and update all content. This may take several minutes.")

        col1, col2 = st.columns([1, 3])

        with col1:
            if st.button("🔄 Refresh Now", type="primary"):
                with st.spinner("Refreshing content... This may take a few minutes."):
                    try:
                        import asyncio
                        from fed_content_importer import FedContentImporter

                        # Create importer and run crawl
                        importer = FedContentImporter()

                        # Run the async crawl function
                        asyncio.run(importer.crawl_and_import())

                        st.success("✅ Refresh completed successfully!")

                        # Also recalculate URL-level scores after refresh
                        from database import Database
                        refresh_db = Database()
                        with refresh_db:
                            refresh_db.calculate_source_document_scores(use_enhanced_scores=True)

                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Refresh failed: {e}")
                        import traceback
                        st.code(traceback.format_exc())

        with col2:
            st.info("""
            **Manual refresh options:**
            - Click "🔄 Refresh Now" button to crawl and update all content
            - This will fetch the latest Federal Reserve content from their website

            **For local development:**
            ```bash
            python fed_content_importer.py --crawl
            ```
            """)

        # Sample documents
        st.markdown("---")
        st.markdown("### 📄 Sample Source Documents")

        cursor.execute("""
            SELECT
                source_type,
                source_title,
                source_url,
                LEFT(content, 200) as preview,
                last_refreshed
            FROM documents
            WHERE is_external_source = TRUE
            ORDER BY last_refreshed DESC
            LIMIT 10
        """)
        samples = cursor.fetchall()

        if samples:
            for doc in samples:
                with st.expander(f"{doc['source_type']}: {doc['source_title']}"):
                    st.markdown(f"**URL:** {doc['source_url']}")
                    st.markdown(f"**Refreshed:** {doc['last_refreshed'].strftime('%m/%d/%Y %I:%M %p')}")
                    st.markdown(f"**Preview:** {doc['preview']}...")
        else:
            st.info("No source documents yet")

        cursor.close()
        conn.close()

    except Exception as e:
        st.error(f"Error loading source management: {e}")

def how_it_works_page():
    """Informational page about the RAG system."""
    st.markdown('<div class="main-header">ℹ️ How It Works</div>', unsafe_allow_html=True)

    st.markdown("""
    Learn how the Public Correspondence Response System works behind the scenes to provide
    accurate, well-sourced responses to your Federal Reserve policy questions.
    """)

    # System Overview
    st.markdown("---")
    st.markdown("## 🎯 System Overview")

    st.markdown("""
    The Public Correspondence Response System uses **Retrieval-Augmented Generation (RAG)** technology
    to provide informed responses based on official Federal Reserve documentation. Rather than relying
    solely on a language model's training data, the system retrieves relevant source documents
    and uses them to generate accurate, well-cited responses.
    """)

    # Architecture Diagrams
    st.markdown("---")
    st.markdown("## 🏗️ System Architecture")

    # Generate diagrams if they don't exist
    if ensure_diagrams_exist():
        # Create tabs for different diagrams
        tab1, tab2, tab3 = st.tabs(["🏗️ System Architecture", "🔄 Query Flow Pipeline", "📥 Content Processing"])

        with tab1:
            st.markdown("""
            This diagram shows the high-level architecture of the Federal Reserve RAG system,
            including:
            - **PII Redactor** (Microsoft Presidio with spaCy NER) for privacy protection
            - **Streamlit UI** with multiple pages
            - **RAG Core Components** including query processing, embedding, retrieval, and response generation
            - **Feedback Analyzer** using Claude for AI-powered sentiment analysis
            - **Claude Sonnet 4** integration for categorization and response generation
            - **PostgreSQL + pgvector** for vector similarity search and data storage
            """)
            if Path('rag_architecture.png').exists():
                st.image('rag_architecture.png', use_container_width=True)
            else:
                st.warning("Architecture diagram not available")

        with tab2:
            st.markdown("""
            This diagram illustrates the complete flow of a user query through the system:

            **Main Query Flow (left to right):**
            1. **Privacy Protection**: PII redaction with Microsoft Presidio (spaCy NER) before storage
            2. **Query Analysis**: Category detection and vector embedding
            3. **Document Retrieval**: Vector search and hybrid ranking with enhanced feedback scores
            4. **Response Generation**: Claude generates cited responses
            5. **AI Feedback Analysis**: Comments analyzed for sentiment, issues, and severity

            The **feedback loop** (shown in blue dashed line) connects back to ranking,
            enabling continuous improvement based on user ratings and AI-analyzed comments.
            """)
            if Path('rag_query_flow.png').exists():
                st.image('rag_query_flow.png', use_container_width=True)
            else:
                st.warning("Query flow diagram not available")

        with tab3:
            st.markdown("""
            This diagram shows how Federal Reserve content is crawled from the website,
            processed into chunks, converted to vector embeddings, and stored in the PostgreSQL database.
            """)
            if Path('rag_content_pipeline.png').exists():
                st.image('rag_content_pipeline.png', use_container_width=True)
            else:
                st.warning("Content pipeline diagram not available")

    # Data Sources
    st.markdown("---")
    st.markdown("## 📚 Data Sources")

    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown("""
        **Primary Source:** [FederalReserve.gov](https://www.federalreserve.gov)

        The system crawls and indexes content from:
        - **About the Fed** pages - Structure, history, and organizational information
        - **FAQs** - Frequently asked questions about monetary policy, banking, and Federal Reserve operations

        **Content Quality Controls:**
        - Excludes administrative content (meeting archives, board bios, annual reports)
        - Filters out navigation pages and date listings
        - Focuses on educational and policy-related content
        - Validates content substance before indexing
        """)

    with col2:
        try:
            db = Database()
            with db:
                db.cursor.execute("SELECT COUNT(*) as count FROM documents;")
                doc_count = db.cursor.fetchone()['count']

                db.cursor.execute("""
                    SELECT MAX(created_at) as last_update
                    FROM documents
                    WHERE metadata->>'source_url' LIKE '%federalreserve.gov%';
                """)
                last_update = db.cursor.fetchone()['last_update']

            st.metric("Total Documents", f"{doc_count:,}")
            if last_update:
                st.metric("Last Updated", last_update.strftime('%m/%d/%Y'))
        except:
            st.info("Database statistics unavailable")

    # Privacy Protection
    st.markdown("---")
    st.markdown("## 🔒 Privacy Protection (PII Redaction)")

    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown("""
        **Automatic PII Detection and Redaction:**

        Before your question is processed or stored, the system uses **Microsoft Presidio**
        with **spaCy NER** to automatically detect and redact:

        **Pattern-Based Detection (Regex):**
        - 📧 Email addresses → `[REDACTED_EMAIL]`
        - 📞 Phone numbers → `[REDACTED_PHONE]`
        - 🆔 Social Security Numbers → `[REDACTED_SSN]`
        - 💳 Credit card numbers → `[REDACTED_CARD]`
        - 🌐 IP addresses → `[REDACTED_IP]`
        - 🏦 Account numbers → `[REDACTED_ACCOUNT]`

        **AI-Based Detection (Presidio + spaCy NER):**
        - 👤 Person names → `[REDACTED_NAME]`
        - 📍 Locations → `[REDACTED_LOCATION]`
        - 🏢 Organizations → `[REDACTED_ORG]` (except Federal Reserve entities)
        - 📅 Dates → `[REDACTED_DATE]`
        - 🆔 IDs (driver licenses, passports) → `[REDACTED_ID]`
        - 🔗 URLs → `[REDACTED_URL]`

        **Important:** Original queries with PII are **NEVER stored** in the database. Only redacted versions are kept.
        """)

    with col2:
        st.info("""
        **Privacy by Design:**

        ✅ Local processing (Presidio + spaCy)
        ✅ Redacted before Claude API
        ✅ Redacted before database
        ✅ No PII in embeddings
        ✅ Transparent to users
        ✅ Industry-standard framework

        **Example:**

        "My name is John Smith"

        becomes

        "My name is [REDACTED_NAME]"
        """)

    # How Retrieval Works
    st.markdown("---")
    st.markdown("## 🔍 How Document Retrieval Works")

    st.markdown("""
    When you submit a question, the system:

    1. **Detects and redacts PII** - Removes sensitive information locally using Microsoft Presidio with spaCy NER
    2. **Detects query category** - Uses Claude to classify the topic (e.g., "Monetary Policy")
    3. **Converts your question to a vector embedding** - A numerical representation that captures semantic meaning
    4. **Searches the document database** - Uses vector similarity to find the most relevant content
    5. **Ranks results using a hybrid scoring system:**
    """)

    st.code("""
Final Score = Similarity Score × (Base Score × (1 + Feedback Weight × Enhanced Feedback Score))

Where:
- Similarity Score: How well the document matches your question (0-1)
- Base Score: Default quality score (1.0 for all documents)
- Enhanced Feedback Score: Combines ratings + AI sentiment analysis (-1.0 to +1.0)
- Feedback Weight: How much feedback influences ranking (0.3 = 30%)
    """, language="python")

    st.markdown("""
    6. **Retrieves top 10 most relevant documents** - Provides comprehensive context
    7. **Generates response** - Claude processes the retrieved documents and your question
    """)

    # Feedback System
    st.markdown("---")
    st.markdown("## 📊 AI-Powered Feedback Analysis")

    st.markdown("""
    The system uses **Claude Sonnet 4** to analyze feedback comments and extract quality signals
    that go beyond simple star ratings.
    """)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        **When you provide feedback, the system:**

        1. **Analyzes your comment with AI** (if provided):
           - Extracts sentiment: Positive, Neutral, or Negative
           - Identifies issues: outdated_info, incorrect_info, too_technical, missing_citations, etc.
           - Assigns severity: minor, moderate, or severe
           - Generates a summary of your feedback

        2. **Calculates Enhanced Feedback Score:**
           - Combines star rating (70%) + sentiment analysis (30%)
           - Applies penalties for severe issues
           - Adjusts based on confidence level

        3. **Flags documents for review** when:
           - Multiple users report similar issues
           - Severe problems are detected
           - Consistently low ratings with negative comments

        4. **Updates document rankings** - Better documents rank higher in future searches
        """)

    with col2:
        st.markdown("""
        **Enhanced Feedback Score Formula:**
        """)
        st.code("""
# Base score from ratings
rating_score = (avg_rating - 3.0) / 2.0

# Sentiment contribution (if comments exist)
sentiment_contribution =
    sentiment_score × confidence × 0.3

# Severity penalties
severity_penalty:
  - severe: -0.3
  - moderate: -0.15
  - minor: -0.05

# Issue-specific penalties
issue_penalties:
  - outdated_info: -0.15
  - incorrect_info: -0.20
  - too_technical: -0.10
  - missing_citations: -0.08

Enhanced Score =
  (0.7 × rating_score) +
  (0.3 × sentiment_contribution) +
  severity_penalty +
  issue_penalties
        """, language="python")

        st.info("""
        💡 **Continuous Learning:** The system learns from both ratings AND detailed
        feedback to identify specific problems and improve document selection.
        """)

    # Reranking Schedule
    st.markdown("---")
    st.markdown("## 🔄 Score Updates and Refresh Schedule")

    st.markdown("""
    **Document Score Updates:**
    - Feedback scores are recalculated whenever new ratings are submitted
    - Changes take effect immediately for subsequent queries
    - No manual intervention required

    **Content Refresh:**
    - Source content can be refreshed manually from the **Source Content** page
    - Recommended refresh frequency: Monthly, or when major Fed policy updates occur
    - Refresh process crawls federalreserve.gov and updates the document database
    """)

    # Response Generation
    st.markdown("---")
    st.markdown("## 🤖 Response Generation")

    col1, col2 = st.columns([3, 1])

    with col1:
        st.markdown(f"""
        **AI Model:** Claude Sonnet 4 by Anthropic

        The system uses Claude to:
        - Analyze retrieved Federal Reserve documents
        - Synthesize information from multiple sources
        - Generate professional, correspondence-style responses
        - Include inline citations with links to source URLs
        - Maintain factual accuracy based on official sources

        **Response Format:**
        - Direct answer to your question
        - Supporting details with citations
        - Links to original Federal Reserve sources
        - Professional tone suitable for public correspondence
        """)

    with col2:
        st.metric("Max Response Length", "2000 tokens")
        st.metric("Documents Retrieved", "10")
        st.metric("Embedding Model", "MiniLM-L6")

    # Privacy and Data
    st.markdown("---")
    st.markdown("## 🔒 Data Storage and Privacy")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        **What Gets Stored:**
        - Your questions (**with PII redacted**)
        - Generated responses with source citations
        - Star ratings (1-5)
        - Feedback comments and AI analysis results
        - Response metadata (timestamp, model version, retrieved documents)
        - Redaction metadata (types detected, NOT the actual PII values)

        **Data Retention:**
        - Stored indefinitely by default to improve system learning
        - Can be deleted using the **Data Management** page
        - Bulk deletion available by date or rating
        """)

    with col2:
        st.markdown("""
        **Privacy-First Design:**
        - ✅ **PII automatically redacted** before storage
        - ✅ **Original queries with PII are NEVER stored**
        - ✅ All processing done locally in PostgreSQL
        - ✅ No personal identifying information collected
        - ✅ Questions are anonymized - not linked to users
        - ✅ Redaction metadata excludes actual PII values

        **Compliance:**
        - Supports GDPR Article 25 (Privacy by Design)
        - Data minimization principle
        - Safe for handling sensitive inquiries
        """)

    # Technical Details
    st.markdown("---")
    with st.expander("🔧 Technical Details"):
        st.markdown("""
        **Technology Stack:**
        - **Database:** PostgreSQL 18 with pgvector extension
        - **Vector Embeddings:** sentence-transformers (all-MiniLM-L6-v2, 384 dimensions)
        - **AI Model:** Claude Sonnet 4 (claude-sonnet-4-20250514)
        - **Web Crawler:** Python with aiohttp and BeautifulSoup4
        - **Interface:** Streamlit

        **Document Processing:**
        - Chunk size: 500 characters
        - Chunk overlap: 50 characters
        - Vector similarity: Cosine distance (pgvector `<=>` operator)

        **Performance:**
        - Typical query response time: 3-5 seconds
        - Document search: Milliseconds (indexed vector search)
        - Concurrent users: Supports multiple simultaneous queries
        """)

@st.dialog("Response Details", width="large")
def show_response_dialog(response, db):
    """Show detailed response in a dialog."""
    from datetime import datetime

    # Selection checkbox
    is_selected = st.checkbox(
        f"Select response #{response['id']}",
        value=response['id'] in st.session_state.selected_responses,
        key=f"dialog_select_{response['id']}"
    )

    if is_selected:
        st.session_state.selected_responses.add(response['id'])
    else:
        st.session_state.selected_responses.discard(response['id'])

    st.markdown(f"**Query:** {response['query_text']}")
    st.markdown("**Response:**")
    st.markdown(response['response_text'])
    st.markdown(f"**Model:** {response['model_version']}")
    st.markdown(f"**Average Rating:** {response['avg_rating']:.2f} ({response['feedback_count']} ratings)")
    st.markdown(f"**Created:** {response['created_at'].strftime('%m/%d/%Y %I:%M %p')}")

    # Display all feedback if available
    if response.get('all_feedback') and response['all_feedback']:
        st.markdown("---")
        fb_with_comments = sum(1 for fb in response['all_feedback'] if fb and fb.get('has_comment'))
        st.markdown(f"**📝 Feedback ({response.get('feedback_count', 0)} total, {fb_with_comments} with comments):**")

        for i, fb in enumerate(response['all_feedback'], 1):
            if fb:  # fb might be None from the array_agg
                # Format the feedback display
                fb_date = fb.get('created_at', '')
                if fb_date:
                    if isinstance(fb_date, str):
                        fb_date = datetime.fromisoformat(fb_date).strftime('%m/%d/%Y %I:%M %p')
                    else:
                        fb_date = fb_date.strftime('%m/%d/%Y %I:%M %p')

                # Build severity indicator
                severity_emoji = ''
                if fb.get('severity') and fb['severity'] != 'none':
                    severity_map = {'minor': '⚡', 'moderate': '⚠️', 'severe': '🚨'}
                    severity_emoji = severity_map.get(fb['severity'], '')

                # Display rating and date
                st.markdown(f"{severity_emoji} **{i}.** {'⭐' * fb.get('rating', 0)} - {fb_date}")

                # Display comment if present
                if fb.get('has_comment') and fb.get('comment'):
                    st.info(fb.get('comment', ''))
                else:
                    st.caption("_(No comment provided)_")

                # Show analysis if available (support both old and new column names)
                analysis_parts = []
                # Handle both string sentiment and numeric sentiment_score
                sentiment_str = fb.get('sentiment')
                if sentiment_str:
                    analysis_parts.append(f"Sentiment: {sentiment_str.title()}")
                elif fb.get('sentiment_score') is not None:
                    sentiment = fb['sentiment_score']
                    sentiment_label = 'Positive' if sentiment > 0.3 else 'Negative' if sentiment < -0.3 else 'Neutral'
                    analysis_parts.append(f"Sentiment: {sentiment_label} ({sentiment:.2f})")

                issues = fb.get('issues') or fb.get('issue_types') or []
                if issues:
                    issue_list = [issue for issue in issues if issue != 'none']
                    if issue_list:
                        analysis_parts.append(f"Issues: {', '.join(issue_list).replace('_', ' ').title()}")

                if analysis_parts:
                    st.caption(" | ".join(analysis_parts))

    # Delete button
    st.markdown("---")
    if st.button(f"🗑️ Delete Response #{response['id']}", type="secondary", use_container_width=True):
        with db:
            if db.delete_response(response['id']):
                st.success(f"Deleted response #{response['id']}")
                st.rerun()

def data_management_page():
    """Page for managing responses and feedback."""
    st.markdown('<div class="main-header">🗑️ Data Management</div>', unsafe_allow_html=True)

    st.markdown("""
    Review and remove outdated or irrelevant responses and feedback.
    This is useful for cleaning up responses from before content improvements.
    """)

    try:
        db = Database()

        # Summary statistics
        st.markdown("### Current Data")
        col1, col2, col3 = st.columns(3)

        with db:
            db.cursor.execute("SELECT COUNT(*) as count FROM responses;")
            total_responses = db.cursor.fetchone()['count']

            db.cursor.execute("SELECT COUNT(*) as count FROM feedback;")
            total_feedback = db.cursor.fetchone()['count']

            db.cursor.execute("SELECT COUNT(*) as count FROM queries;")
            total_queries = db.cursor.fetchone()['count']

        col1.metric("Total Responses", total_responses)
        col2.metric("Total Feedback", total_feedback)
        col3.metric("Total Queries", total_queries)

        st.markdown("---")

        # Bulk Actions
        st.markdown("### Bulk Actions")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("#### Delete by Date")
            days_old = st.number_input("Delete responses older than (days):", min_value=1, value=30, step=1)

            if st.button("🗑️ Delete Old Responses", type="secondary"):
                with db:
                    deleted = db.delete_old_responses(days_old)
                st.success(f"Deleted {deleted} responses older than {days_old} days")
                st.rerun()

        with col2:
            st.markdown("#### Delete by Rating")
            max_rating = st.slider("Delete responses with rating ≤", min_value=1, max_value=5, value=2)

            if st.button("🗑️ Delete Low-Rated Responses", type="secondary"):
                with db:
                    # Get responses with low ratings
                    db.cursor.execute("""
                        SELECT DISTINCT r.id
                        FROM responses r
                        JOIN feedback f ON f.response_id = r.id
                        WHERE f.rating <= %s;
                    """, (max_rating,))
                    low_rated_ids = [row['id'] for row in db.cursor.fetchall()]

                    if low_rated_ids:
                        deleted = db.delete_responses_batch(low_rated_ids)
                        st.success(f"Deleted {deleted} responses with rating ≤ {max_rating}")
                        st.rerun()
                    else:
                        st.info("No responses found with that rating")

        st.markdown("---")

        # Individual Response Management
        st.markdown("### Review Individual Responses")

        # Filters
        with st.expander("🔍 Filters"):
            col1, col2, col3 = st.columns(3)

            with col1:
                min_rating_filter = st.selectbox("Min Rating", options=[None, 1, 2, 3, 4, 5], index=0)
            with col2:
                max_rating_filter = st.selectbox("Max Rating", options=[None, 1, 2, 3, 4, 5], index=0)
            with col3:
                limit = st.number_input("Results per page", min_value=10, max_value=100, value=20, step=10)

        # Get responses with filters
        with db:
            responses = db.get_all_responses(
                limit=limit,
                min_rating=min_rating_filter,
                max_rating=max_rating_filter
            )

        if responses:
            st.markdown(f"**Showing {len(responses)} responses**")

            # Initialize session state for selections
            if 'selected_responses' not in st.session_state:
                st.session_state.selected_responses = set()

            # Select all checkbox
            select_all = st.checkbox("Select all on this page")
            if select_all:
                st.session_state.selected_responses.update([r['id'] for r in responses])

            # Delete selected button
            if st.session_state.selected_responses:
                if st.button(f"🗑️ Delete {len(st.session_state.selected_responses)} Selected Responses", type="primary"):
                    with db:
                        deleted = db.delete_responses_batch(list(st.session_state.selected_responses))
                    st.success(f"Deleted {deleted} responses")
                    st.session_state.selected_responses.clear()
                    st.rerun()

            # Display responses as list
            for i, response in enumerate(responses):
                response_id = response['id']

                # Build list item
                has_comments = response.get('comments_count', 0) > 0
                comment_indicator = f" | 💬 {response.get('comments_count', 0)}" if has_comments else ""

                # Checkbox + Query + View button
                col1, col2, col3 = st.columns([0.5, 5, 1])
                with col1:
                    is_selected = st.checkbox(
                        "Select",
                        value=response_id in st.session_state.selected_responses,
                        key=f"select_{response_id}",
                        label_visibility="collapsed"
                    )
                    if is_selected:
                        st.session_state.selected_responses.add(response_id)
                    else:
                        st.session_state.selected_responses.discard(response_id)

                with col2:
                    st.markdown(f"**Q:** {response['query_text'][:100]}...")
                    rating_display = '⭐' * int(response['avg_rating']) if response['avg_rating'] > 0 else 'No rating'
                    st.caption(f"{rating_display}{comment_indicator} | {response['created_at'].strftime('%m/%d/%Y %I:%M %p')}")

                with col3:
                    if st.button("View", key=f"view_response_{response_id}"):
                        show_response_dialog(response, db)

                if i < len(responses) - 1:
                    st.divider()
        else:
            st.info("No responses found with the selected filters")

        # Danger Zone - Delete All Data
        st.markdown("---")
        st.markdown("### ⚠️ Danger Zone")

        with st.expander("🚨 Delete All Data (Irreversible)", expanded=False):
            st.warning("""
            **WARNING: This action cannot be undone!**

            This will permanently delete:
            - ✗ All responses
            - ✗ All queries
            - ✗ All feedback and ratings
            - ✗ All document review flags
            - ✗ All document scores (feedback-based rankings)

            **Documents and source content will NOT be affected.**

            This completely resets all user interactions and feedback-derived data,
            returning the system to a fresh state with only the source documents.
            """)

            # Require confirmation checkbox
            confirm_delete = st.checkbox(
                "I understand this will permanently delete all responses, queries, and feedback",
                key="confirm_delete_all"
            )

            # Show button only when confirmed
            if confirm_delete:
                if st.button("🗑️ DELETE ALL DATA", type="primary", key="delete_all_button"):
                    try:
                        with db:
                            deleted_counts = db.delete_all_user_data()

                        st.success(f"""
                        **All user data has been deleted:**
                        - 🗑️ {deleted_counts['queries']} queries
                        - 🗑️ {deleted_counts['responses']} responses
                        - 🗑️ {deleted_counts['feedback']} feedback items
                        - 🗑️ {deleted_counts['document_flags']} document review flags
                        - 🗑️ {deleted_counts['document_scores']} chunk-level scores reset
                        - 🗑️ {deleted_counts['source_document_scores']} URL-level scores reset

                        **System has been reset to fresh state with only source documents.**
                        """)
                        st.balloons()
                        st.rerun()
                    except Exception as delete_error:
                        st.error(f"Error deleting all data: {delete_error}")
                        import traceback
                        st.code(traceback.format_exc())

    except Exception as e:
        st.error(f"Error in data management: {e}")
        import traceback
        st.code(traceback.format_exc())

def main():
    """Main application."""

    # Sidebar navigation
    st.sidebar.title("📝 Federal Reserve Correspondence System")
    st.sidebar.markdown("---")

    page = st.sidebar.radio(
        "Navigation",
        ["📨 Submit Inquiry", "📝 Review Responses", "📊 Analytics", "📚 Source Content", "ℹ️ How It Works", "🗑️ Data Management"],
        label_visibility="collapsed"
    )

    st.sidebar.markdown("---")
    st.sidebar.markdown("### About")
    st.sidebar.info("""
    **Federal Reserve Public Correspondence Response System**

    This system provides responses to inquiries about Federal Reserve policies, operations, and monetary policy based on official sources.

    **Features:**
    - Submit policy inquiries
    - Professional formatted responses
    - Source citations and references
    - Response quality feedback
    - Analytics and insights

    📖 Visit **How It Works** to learn more about the system.
    """)

    # Route to appropriate page
    if page == "📨 Submit Inquiry":
        query_page()
    elif page == "📝 Review Responses":
        review_page()
    elif page == "📊 Analytics":
        analytics_page()
    elif page == "📚 Source Content":
        source_management_page()
    elif page == "ℹ️ How It Works":
        how_it_works_page()
    elif page == "🗑️ Data Management":
        data_management_page()

if __name__ == "__main__":
    main()
