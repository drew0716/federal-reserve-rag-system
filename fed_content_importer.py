"""
Federal Reserve Content Importer
Crawls, processes, and imports Federal Reserve content into the RAG system
"""
import os
import sys
import asyncio
import psycopg2
from psycopg2.extras import execute_batch, Json
from dotenv import load_dotenv
from datetime import datetime
from pathlib import Path
import re
import json
from pgvector.psycopg2 import register_vector

# Script directory
script_dir = Path(__file__).parent

from embeddings import EmbeddingService

load_dotenv()

class FedContentImporter:
    """Import Federal Reserve content into the RAG database."""

    def __init__(self):
        """Initialize the importer."""
        self.db_params = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': os.getenv('DB_PORT', '5433'),
            'database': os.getenv('DB_NAME', 'rag_system'),
            'user': os.getenv('DB_USER', 'rag_user'),
            'password': os.getenv('DB_PASSWORD', '')
        }
        self.embeddings = EmbeddingService()
        self.chunk_size = 500  # characters per chunk
        self.chunk_overlap = 50  # overlap between chunks

    def get_connection(self):
        """Get database connection."""
        return psycopg2.connect(**self.db_params)

    def chunk_text(self, text, metadata):
        """
        Split text into overlapping chunks.

        Args:
            text: The text to chunk
            metadata: Dict with source_url, source_title, etc.

        Returns:
            List of chunk dictionaries
        """
        chunks = []
        words = text.split()

        # Approximate characters per word
        chars_per_word = self.chunk_size // 100  # ~5 chars/word estimate
        words_per_chunk = self.chunk_size // chars_per_word
        overlap_words = self.chunk_overlap // chars_per_word

        i = 0
        chunk_num = 0
        while i < len(words):
            chunk_words = words[i:i + words_per_chunk]
            chunk_text = ' '.join(chunk_words)

            if len(chunk_text.strip()) > 20:  # Only keep substantial chunks
                chunks.append({
                    'content': chunk_text,
                    'metadata': {
                        **metadata,
                        'chunk_number': chunk_num,
                        'total_chunks': 0  # Will update at end
                    }
                })
                chunk_num += 1

            i += words_per_chunk - overlap_words

        # Update total chunks
        for chunk in chunks:
            chunk['metadata']['total_chunks'] = len(chunks)

        return chunks

    def parse_fed_file(self, filepath):
        """
        Parse a Federal Reserve text file.

        Expected format:
        <!-- source_url: URL -->
        <!-- title: TITLE -->
        <!-- date_fetched: DATE -->

        CONTENT
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        # Extract metadata from comments
        source_url = re.search(r'<!-- source_url: (.*?) -->', content)
        title = re.search(r'<!-- title: (.*?) -->', content)
        date_fetched = re.search(r'<!-- date_fetched: (.*?) -->', content)

        # Remove metadata comments from content
        clean_content = re.sub(r'<!--.*?-->\n*', '', content, flags=re.DOTALL).strip()

        return {
            'content': clean_content,
            'source_url': source_url.group(1) if source_url else '',
            'source_title': title.group(1) if title else os.path.basename(filepath),
            'date_fetched': date_fetched.group(1) if date_fetched else None
        }

    def import_directory(self, directory, source_type):
        """
        Import all files from a directory.

        Args:
            directory: Path to directory containing text files
            source_type: Type of source (fed_about, fed_faq, etc.)
        """
        if not os.path.exists(directory):
            print(f"⚠️  Directory not found: {directory}")
            return {'added': 0, 'updated': 0, 'errors': 0}

        files = [f for f in os.listdir(directory) if f.endswith('.txt')]
        print(f"\n📂 Processing {len(files)} files from {directory}")
        print(f"   Source type: {source_type}")

        stats = {'added': 0, 'updated': 0, 'errors': 0}
        all_chunks = []

        # Process each file
        for filename in files:
            try:
                filepath = os.path.join(directory, filename)
                parsed = self.parse_fed_file(filepath)

                if not parsed['content']:
                    continue

                # Create chunks
                chunks = self.chunk_text(
                    parsed['content'],
                    {
                        'source_url': parsed['source_url'],
                        'source_title': parsed['source_title'],
                        'source_type': source_type,
                        'original_file': filename
                    }
                )

                all_chunks.extend(chunks)

            except Exception as e:
                print(f"⚠️  Error processing {filename}: {e}")
                stats['errors'] += 1

        print(f"   Created {len(all_chunks)} chunks from {len(files)} files")

        # Generate embeddings in batches
        print("   Generating embeddings...")
        batch_size = 100
        for i in range(0, len(all_chunks), batch_size):
            batch = all_chunks[i:i + batch_size]
            texts = [chunk['content'] for chunk in batch]
            embeddings = self.embeddings.embed_documents(texts)

            for chunk, embedding in zip(batch, embeddings):
                chunk['embedding'] = embedding

        # Store in database
        print("   Storing in database...")
        stats['added'] = self._store_chunks(all_chunks, source_type)

        return stats

    def _store_chunks(self, chunks, source_type):
        """Store chunks in database, replacing existing content from this source."""
        conn = self.get_connection()
        register_vector(conn)  # Register pgvector types
        cursor = conn.cursor()

        try:
            # Delete existing documents from this source
            cursor.execute(
                "DELETE FROM documents WHERE source_type = %s AND is_external_source = TRUE",
                (source_type,)
            )
            deleted_count = cursor.rowcount
            print(f"   Deleted {deleted_count} existing documents for {source_type}")

            # Insert new documents
            insert_query = """
                INSERT INTO documents (
                    content, embedding, metadata, source_type, source_url,
                    source_title, is_external_source, last_refreshed
                )
                VALUES (%s, %s, %s, %s, %s, %s, TRUE, %s)
            """

            data = [
                (
                    chunk['content'],
                    chunk['embedding'].tolist() if hasattr(chunk['embedding'], 'tolist') else chunk['embedding'],
                    Json(chunk['metadata']),  # Wrap in Json() for JSONB
                    source_type,
                    chunk['metadata'].get('source_url'),
                    chunk['metadata'].get('source_title'),
                    datetime.utcnow()
                )
                for chunk in chunks
            ]

            execute_batch(cursor, insert_query, data, page_size=100)
            conn.commit()

            print(f"   ✓ Inserted {len(chunks)} new document chunks")
            return len(chunks)

        except Exception as e:
            conn.rollback()
            print(f"   ✗ Database error: {e}")
            raise
        finally:
            cursor.close()
            conn.close()

    def log_refresh(self, source_type, stats, error=None):
        """Log refresh activity to database."""
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                INSERT INTO source_refresh_log (
                    source_type, documents_added, documents_updated,
                    documents_deleted, refresh_started, refresh_completed,
                    status, error_message
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    source_type,
                    stats.get('added', 0),
                    stats.get('updated', 0),
                    stats.get('deleted', 0),
                    datetime.utcnow(),
                    datetime.utcnow() if not error else None,
                    'completed' if not error else 'failed',
                    str(error) if error else None
                )
            )
            conn.commit()
        finally:
            cursor.close()
            conn.close()

    async def crawl_and_import(self):
        """Run the crawler and import content."""
        print("\n" + "="*60)
        print("FEDERAL RESERVE CONTENT CRAWLER & IMPORTER")
        print("="*60)

        # Import crawler
        from crawl_about_fed import main as crawl_main

        # Run crawler
        print("\n🕷️  Starting web crawler...")
        await crawl_main()

        # Import About the Fed content
        print("\n📥 Importing About the Fed content...")
        stats_about = self.import_directory(
            "about_the_fed_pages",
            "fed_about"
        )
        self.log_refresh("fed_about", stats_about)

        # Import FAQ content
        print("\n📥 Importing FAQ content...")
        stats_faq = self.import_directory(
            "faq_pages",
            "fed_faq"
        )
        self.log_refresh("fed_faq", stats_faq)

        # Summary
        print("\n" + "="*60)
        print("IMPORT COMPLETE")
        print("="*60)
        print(f"About the Fed: {stats_about['added']} documents")
        print(f"FAQs:          {stats_faq['added']} documents")
        print(f"Total:         {stats_about['added'] + stats_faq['added']} documents")
        print(f"Errors:        {stats_about['errors'] + stats_faq['errors']}")
        print("="*60)

    def import_existing_content(self):
        """Import already-crawled content without re-crawling."""
        print("\n" + "="*60)
        print("IMPORTING EXISTING FEDERAL RESERVE CONTENT")
        print("="*60)

        # Import About the Fed content
        print("\n📥 Importing About the Fed content...")
        stats_about = self.import_directory(
            "about_the_fed_pages",
            "fed_about"
        )
        self.log_refresh("fed_about", stats_about)

        # Import FAQ content
        print("\n📥 Importing FAQ content...")
        stats_faq = self.import_directory(
            "faq_pages",
            "fed_faq"
        )
        self.log_refresh("fed_faq", stats_faq)

        # Summary
        print("\n" + "="*60)
        print("IMPORT COMPLETE")
        print("="*60)
        print(f"About the Fed: {stats_about['added']} documents")
        print(f"FAQs:          {stats_faq['added']} documents")
        print(f"Total:         {stats_about['added'] + stats_faq['added']} documents")
        print(f"Errors:        {stats_about['errors'] + stats_faq['errors']}")
        print("="*60)

def main():
    """Main entry point."""
    importer = FedContentImporter()

    import argparse
    parser = argparse.ArgumentParser(description='Import Federal Reserve content')
    parser.add_argument(
        '--crawl',
        action='store_true',
        help='Crawl fresh content before importing'
    )
    parser.add_argument(
        '--import-only',
        action='store_true',
        help='Import existing crawled content without re-crawling'
    )

    args = parser.parse_args()

    if args.crawl:
        asyncio.run(importer.crawl_and_import())
    else:
        importer.import_existing_content()

if __name__ == "__main__":
    main()
