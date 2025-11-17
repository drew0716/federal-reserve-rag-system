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
    """Get a new database connection."""
    return psycopg2.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        port=os.getenv('DB_PORT', '5433'),
        database=os.getenv('DB_NAME', 'rag_system'),
        user=os.getenv('DB_USER', 'rag_user'),
        password=os.getenv('DB_PASSWORD', '')
    )

# Initialize RAG system
@st.cache_resource
def get_rag_system():
    """Initialize RAG system."""
    return RAGSystem()

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
    max_tokens = 500  # Keep responses concise

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
                    'retrieved_documents': response['retrieved_documents'],
                    'model': response['model']
                }
                st.session_state.show_copy_code = False  # Reset copy state

            except Exception as e:
                st.error(f"Error generating response: {e}")
                return

    # Display response if available (persists across reruns)
    if 'current_response' in st.session_state:
        response = st.session_state.current_response

        # Display response section
        st.markdown("---")
        st.markdown("## 📝 Response")

        # Copy button with improved UX
        col1, col2 = st.columns([1, 5])
        with col1:
            if st.button("📋 Copy Response", key="copy_response", help="Show text for copying"):
                st.session_state.show_copy_code = not st.session_state.get('show_copy_code', False)

        # Show copyable text if button was clicked
        if st.session_state.get('show_copy_code', False):
            st.code(response['text'], language=None)
            st.info("💡 Select the text above and copy it (Cmd+C or Ctrl+C)")

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
        st.markdown("## 📊 Rate this Response")

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
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO feedback (response_id, rating, comment)
                    VALUES (%s, %s, %s)
                    """,
                    (response['id'], rating, comment if comment else None)
                )
                conn.commit()
                cursor.close()
                conn.close()

                st.success("✅ Thank you for your feedback!")

                # Clear the response after successful feedback
                del st.session_state.current_response
                st.rerun()

            except Exception as e:
                st.error(f"Error submitting feedback: {e}")

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

        current_page = st.session_state.review_page
        response = unrated_responses[current_page]

        # Display response
        st.markdown(f"### Response {current_page + 1} of {len(unrated_responses)}")

        st.markdown(f"**Query:** {response['query_text']}")
        st.markdown(f"**Date:** {response['created_at'].strftime('%Y-%m-%d %H:%M:%S')}")
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
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute(
                        """
                        INSERT INTO feedback (response_id, rating, comment)
                        VALUES (%s, %s, %s)
                        """,
                        (response['response_id'], rating, comment if comment else None)
                    )
                    conn.commit()
                    cursor.close()
                    conn.close()

                    st.success("✅ Feedback submitted!")
                    # Move to next response
                    if current_page < len(unrated_responses) - 1:
                        st.session_state.review_page = current_page + 1
                    st.rerun()

                except Exception as e:
                    st.error(f"Error submitting feedback: {e}")

    except Exception as e:
        st.error(f"Error loading unrated responses: {e}")

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

        # Recent feedback
        st.markdown("### 💬 Recent Feedback")
        cursor.execute("""
            SELECT
                f.rating,
                f.comment,
                f.created_at,
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
            for fb in recent_feedback:
                with st.expander(f"{'⭐' * fb['rating']} - {fb['created_at'].strftime('%Y-%m-%d %H:%M')}"):
                    st.markdown(f"**Query:** {fb['query_text']}")
                    if fb['comment']:
                        st.markdown(f"**Comment:** {fb['comment']}")
                    st.markdown(f"**Response:** {fb['response_text'][:200]}...")
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
                col3.metric("Last Refresh", most_recent.strftime('%Y-%m-%d %H:%M'))
            else:
                col3.metric("Last Refresh", "Never")

            # Sources table
            st.markdown("---")
            st.markdown("### 📋 Source Breakdown")
            df_sources = pd.DataFrame(sources)
            df_sources['last_refresh'] = df_sources['last_refresh'].apply(
                lambda x: x.strftime('%Y-%m-%d %H:%M') if x else 'Never'
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
                with st.expander(f"{status_icon} {log['source_type']} - {log['refresh_started'].strftime('%Y-%m-%d %H:%M')}"):
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
                        import subprocess
                        result = subprocess.run(
                            ['python', 'fed_content_importer.py', '--crawl'],
                            capture_output=True,
                            text=True,
                            timeout=600  # 10 minute timeout
                        )

                        if result.returncode == 0:
                            st.success("✅ Refresh completed successfully!")
                            st.rerun()
                        else:
                            st.error(f"❌ Refresh failed: {result.stderr}")
                    except subprocess.TimeoutExpired:
                        st.error("❌ Refresh timed out after 10 minutes")
                    except Exception as e:
                        st.error(f"❌ Error: {e}")

        with col2:
            st.info("""
            **Import existing content** (faster, no web crawling):
            ```bash
            python fed_content_importer.py --import-only
            ```

            **Full refresh with crawling**:
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
                    st.markdown(f"**Refreshed:** {doc['last_refreshed'].strftime('%Y-%m-%d %H:%M')}")
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
                st.metric("Last Updated", last_update.strftime('%Y-%m-%d'))
        except:
            st.info("Database statistics unavailable")

    # How Retrieval Works
    st.markdown("---")
    st.markdown("## 🔍 How Document Retrieval Works")

    st.markdown("""
    When you submit a question, the system:

    1. **Converts your question to a vector embedding** - A numerical representation that captures semantic meaning
    2. **Searches the document database** - Uses vector similarity to find the most relevant content
    3. **Ranks results using a hybrid scoring system:**
    """)

    st.code("""
Final Score = Similarity Score × (Base Score × (1 + Feedback Weight × Feedback Score))

Where:
- Similarity Score: How well the document matches your question (0-1)
- Base Score: Default quality score (1.0 for all documents)
- Feedback Score: Adjustment based on user ratings (-1.0 to +1.0)
- Feedback Weight: How much feedback influences ranking (0.3 = 30%)
    """, language="python")

    st.markdown("""
    4. **Retrieves top 10 most relevant documents** - Provides comprehensive context
    5. **Generates response** - Claude processes the retrieved documents and your question
    """)

    # Feedback System
    st.markdown("---")
    st.markdown("## 📊 How Feedback Gets Incorporated")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        **User Ratings Impact Future Results:**

        When you rate a response (1-5 stars), the system:

        1. **Associates your rating with all documents** used in that response
        2. **Calculates average ratings** for each document across all responses
        3. **Converts ratings to feedback scores:**
           - 5 stars → +1.0 (boost ranking)
           - 3 stars → 0.0 (neutral)
           - 1 star → -1.0 (lower ranking)

        4. **Updates document scores** in the database
        5. **Applies scores to future searches** - Better-rated documents rank higher
        """)

    with col2:
        st.markdown("""
        **Feedback Score Calculation:**
        """)
        st.code("""
Feedback Score = (Average Rating - 3.0) / 2.0

Examples:
- Avg 5.0 stars → +1.0
- Avg 4.0 stars → +0.5
- Avg 3.0 stars →  0.0
- Avg 2.0 stars → -0.5
- Avg 1.0 stars → -1.0
        """, language="python")

        st.info("""
        💡 **Continuous Learning:** The system improves over time as it learns
        which documents provide the most helpful information for different types of questions.
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
        st.metric("Max Response Length", "500 tokens")
        st.metric("Documents Retrieved", "10")
        st.metric("Embedding Model", "MiniLM-L6")

    # Privacy and Data
    st.markdown("---")
    st.markdown("## 🔒 Data Storage and Privacy")

    st.markdown("""
    **What Gets Stored:**
    - Your questions and the generated responses
    - Ratings and feedback comments you provide
    - Response metadata (timestamp, model version, retrieved documents)

    **Data Retention:**
    - Stored indefinitely by default to improve system learning
    - Can be deleted using the **Data Management** page
    - Bulk deletion available by date or rating

    **Privacy Notes:**
    - All data stored locally in PostgreSQL database
    - No personal identifying information collected
    - Questions are anonymized - not linked to users
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

            # Display responses
            for response in responses:
                response_id = response['id']

                with st.expander(
                    f"**Q:** {response['query_text'][:100]}... | "
                    f"Rating: {'⭐' * int(response['avg_rating']) if response['avg_rating'] > 0 else 'No rating'} | "
                    f"{response['created_at'].strftime('%Y-%m-%d %H:%M')}"
                ):
                    # Selection checkbox
                    is_selected = st.checkbox(
                        f"Select response {response_id}",
                        value=response_id in st.session_state.selected_responses,
                        key=f"select_{response_id}"
                    )

                    if is_selected:
                        st.session_state.selected_responses.add(response_id)
                    else:
                        st.session_state.selected_responses.discard(response_id)

                    st.markdown(f"**Query:** {response['query_text']}")
                    st.markdown(f"**Response:**")
                    st.markdown(response['response_text'])
                    st.markdown(f"**Model:** {response['model_version']}")
                    st.markdown(f"**Average Rating:** {response['avg_rating']:.2f} ({response['feedback_count']} ratings)")
                    st.markdown(f"**Created:** {response['created_at']}")

                    # Individual delete button
                    if st.button(f"Delete Response #{response_id}", key=f"delete_{response_id}"):
                        with db:
                            if db.delete_response(response_id):
                                st.success(f"Deleted response #{response_id}")
                                st.rerun()
        else:
            st.info("No responses found with the selected filters")

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
