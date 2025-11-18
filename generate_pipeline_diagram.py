#!/usr/bin/env python3
"""
Generate architecture diagrams for the Federal Reserve RAG System.
Creates two diagrams:
1. System Architecture - High-level components
2. Query Flow Pipeline - Detailed step-by-step flow
"""

from diagrams import Diagram, Cluster, Edge
from diagrams.onprem.database import PostgreSQL
from diagrams.programming.language import Python
from diagrams.onprem.client import Users
from diagrams.custom import Custom
import os


def generate_system_architecture():
    """Generate high-level system architecture diagram."""

    graph_attr = {
        "fontsize": "16",
        "bgcolor": "white",
        "pad": "0.5",
    }

    with Diagram(
        "Federal Reserve RAG System Architecture",
        filename="images/rag_architecture",
        show=False,
        direction="TB",
        graph_attr=graph_attr,
        outformat="png"
    ):
        user = Users("Users")

        with Cluster("Streamlit Web UI"):
            ui_submit = Python("Submit Inquiry")
            ui_review = Python("Review Responses")
            ui_analytics = Python("Analytics Dashboard")
            ui_manage = Python("Data Management")
            ui_how = Python("How It Works")

        with Cluster("RAG System Core"):
            pii_redactor = Python("PII Redactor\n(Presidio + spaCy)")
            query_proc = Python("Query Processing\n& Categorization")
            embedding_svc = Python("Embedding Service\n(MiniLM-L6-v2)")
            retrieval = Python("Document Retrieval\n& Hybrid Ranking")
            response_gen = Python("Response Generator")
            feedback_analyzer = Python("Feedback Analyzer\n(AI Sentiment)")

        with Cluster("External Services"):
            claude = Python("Claude Sonnet 4\n(Anthropic API)")

        with Cluster("PostgreSQL + pgvector"):
            db_docs = PostgreSQL("Documents\n(2,625+ chunks)")
            db_queries = PostgreSQL("Queries")
            db_responses = PostgreSQL("Responses")
            db_feedback = PostgreSQL("Feedback")
            db_scores = PostgreSQL("Document Scores")

        # User interactions
        user >> Edge(label="submit question") >> ui_submit
        user >> Edge(label="rate response") >> ui_review
        user >> Edge(label="view metrics") >> ui_analytics

        # Query flow with PII redaction
        ui_submit >> pii_redactor >> Edge(label="redacted", color="green") >> query_proc
        query_proc >> embedding_svc
        embedding_svc >> retrieval >> db_docs
        db_docs >> Edge(label="top 10 docs") >> response_gen
        response_gen >> claude >> Edge(label="cited response") >> ui_submit >> user

        # Feedback flow with AI analysis
        ui_review >> Edge(label="rating + comment") >> feedback_analyzer
        feedback_analyzer >> Edge(label="AI analysis", color="purple") >> db_feedback
        db_feedback >> Edge(label="update scores") >> db_scores
        db_scores >> Edge(label="enhanced ranking") >> retrieval

        # Storage connections
        pii_redactor >> Edge(label="redacted only", color="green") >> db_queries
        response_gen >> db_responses
        ui_analytics >> db_responses
        ui_manage >> db_responses


def generate_query_flow_pipeline():
    """Generate detailed query flow pipeline diagram with feedback analysis."""

    graph_attr = {
        "fontsize": "13",
        "bgcolor": "white",
        "pad": "0.5",
    }

    with Diagram(
        "RAG Query Flow Pipeline",
        filename="images/rag_query_flow",
        show=False,
        direction="LR",
        graph_attr=graph_attr,
        outformat="png"
    ):
        user_input = Users("User")

        with Cluster("1. Privacy Protection"):
            redact_pii = Python("Redact PII\n(Presidio + spaCy)")
            store_query = PostgreSQL("Store Redacted\nQuery Only")

        with Cluster("2. Query Analysis"):
            detect_category = Python("Detect Category\n(Claude)")
            generate_embedding = Python("Generate Embedding\n(384-dim vector)")

        with Cluster("3. Document Retrieval"):
            vector_search = PostgreSQL("Vector Search\n(cosine similarity)")
            hybrid_rank = Python("Hybrid Ranking\nSimilarity × Enhanced Score")
            retrieve_docs = PostgreSQL("Retrieve Top 10\nDocuments + URLs")

        with Cluster("4. Response Generation"):
            generate_response = Python("Generate Response\n(Claude + citations)")
            store_response = PostgreSQL("Store Response\n& Metadata")

        user_output = Users("User")

        with Cluster("5. AI Feedback Analysis"):
            analyze_comment = Python("Analyze Comment\n(Claude: sentiment,\nissues, severity)")
            store_feedback = PostgreSQL("Store Feedback\n+ Analysis")
            check_patterns = Python("Check Document\nPatterns")
            update_scores = PostgreSQL("Update Enhanced\nFeedback Scores")

        # Main query flow
        user_input >> Edge(label="question") >> redact_pii
        redact_pii >> Edge(label="redacted", color="green") >> store_query
        store_query >> detect_category
        detect_category >> generate_embedding
        generate_embedding >> Edge(label="vector") >> vector_search
        vector_search >> Edge(label="scores") >> hybrid_rank
        hybrid_rank >> Edge(label="ranked") >> retrieve_docs
        retrieve_docs >> Edge(label="context") >> generate_response
        generate_response >> store_response
        store_response >> Edge(label="response") >> user_output

        # Feedback flow
        user_output >> Edge(label="rating + comment") >> analyze_comment
        analyze_comment >> Edge(label="AI analysis", color="purple") >> store_feedback
        store_feedback >> check_patterns
        check_patterns >> Edge(label="if issues") >> update_scores

        # Feedback loop back to retrieval
        update_scores >> Edge(label="improves ranking", style="dashed", color="blue") >> hybrid_rank


def generate_data_flow_diagram():
    """Generate data flow diagram showing crawling and processing."""

    graph_attr = {
        "fontsize": "14",
        "bgcolor": "white",
        "pad": "0.5",
    }

    with Diagram(
        "Content Processing Pipeline",
        filename="images/rag_content_pipeline",
        show=False,
        direction="LR",
        graph_attr=graph_attr,
        outformat="png"
    ):
        # Content sources
        with Cluster("Federal Reserve Website"):
            about_pages = Python("About the Fed\n(272 pages)")
            faq_pages = Python("FAQ Pages\n(87 pages)")

        # Processing steps
        with Cluster("Content Processing"):
            crawler = Python("Web Crawler\n(crawl_about_fed.py)")
            chunker = Python("Text Chunker\n(500 chars, 50 overlap)")
            embedder = Python("Embedding Generator\n(sentence-transformers)")

        # Storage
        with Cluster("PostgreSQL Database"):
            db = PostgreSQL("Documents Table\n(~2,625 chunks)")

        # Flow
        about_pages >> crawler
        faq_pages >> crawler
        crawler >> Edge(label="HTML content") >> chunker
        chunker >> Edge(label="text chunks") >> embedder
        embedder >> Edge(label="vectors + metadata") >> db


if __name__ == "__main__":
    print("Generating Federal Reserve RAG System diagrams...")
    print()

    print("1. Generating system architecture diagram...")
    generate_system_architecture()
    print("   ✓ Created: images/rag_architecture.png")

    print("2. Generating query flow pipeline diagram...")
    generate_query_flow_pipeline()
    print("   ✓ Created: images/rag_query_flow.png")

    print("3. Generating content processing pipeline diagram...")
    generate_data_flow_diagram()
    print("   ✓ Created: images/rag_content_pipeline.png")

    print()
    print("All diagrams generated successfully!")
    print()
    print("To view the diagrams:")
    print("  - open images/rag_architecture.png")
    print("  - open images/rag_query_flow.png")
    print("  - open images/rag_content_pipeline.png")
