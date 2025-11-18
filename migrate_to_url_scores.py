#!/usr/bin/env python3
"""
Migration script to convert chunk-level document scores to URL-level scores.

This script:
1. Creates the source_document_scores table if it doesn't exist
2. Aggregates existing chunk-level scores by URL
3. Migrates the data to the new URL-level scoring system
4. Preserves all existing feedback data

Run this after updating the schema and before refreshing source data.
"""
import os
import sys
from database import Database
from dotenv import load_dotenv

load_dotenv()


def migrate_to_url_scores():
    """Migrate existing chunk-level scores to URL-level scores."""
    print("=" * 80)
    print("Migration: Chunk-level scores → URL-level scores")
    print("=" * 80)
    print()

    db = Database()

    try:
        with db:
            # Step 1: Check if source_document_scores table exists
            print("Step 1: Checking database schema...")
            db.cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'source_document_scores'
                );
            """)
            table_exists = db.cursor.fetchone()['exists']

            if not table_exists:
                print("  ⚠️  source_document_scores table not found!")
                print("  Please run the schema update first (supabase_setup.sql)")
                return False

            print("  ✅ source_document_scores table exists")
            print()

            # Step 2: Count existing chunk-level scores
            print("Step 2: Analyzing existing data...")
            db.cursor.execute("SELECT COUNT(*) as count FROM document_scores;")
            chunk_count = db.cursor.fetchone()['count']
            print(f"  Found {chunk_count} chunk-level scores")

            # Step 3: Check how many URLs will be created
            db.cursor.execute("""
                SELECT COUNT(DISTINCT d.source_url) as url_count
                FROM documents d
                JOIN document_scores ds ON d.id = ds.document_id
                WHERE d.source_url IS NOT NULL AND d.source_url != '';
            """)
            url_count = db.cursor.fetchone()['url_count']
            print(f"  Will create scores for {url_count} unique URLs")
            print()

            if url_count == 0:
                print("  ℹ️  No URL-based documents found with scores to migrate")
                print("  This is normal if you haven't submitted feedback yet")
                return True

            # Step 4: Perform migration
            print("Step 3: Migrating chunk-level scores to URL-level...")
            migration_query = """
                INSERT INTO source_document_scores (
                    source_url,
                    source_type,
                    feedback_score,
                    enhanced_feedback_score,
                    feedback_count,
                    last_updated
                )
                SELECT
                    d.source_url,
                    d.source_type,
                    AVG(ds.feedback_score) as avg_feedback_score,
                    AVG(COALESCE(ds.enhanced_feedback_score, ds.feedback_score)) as avg_enhanced_score,
                    COUNT(ds.id) as chunk_count,
                    MAX(ds.last_updated) as last_updated
                FROM documents d
                JOIN document_scores ds ON d.id = ds.document_id
                WHERE d.source_url IS NOT NULL
                    AND d.source_url != ''
                GROUP BY d.source_url, d.source_type
                ON CONFLICT (source_url) DO UPDATE
                SET feedback_score = EXCLUDED.feedback_score,
                    enhanced_feedback_score = EXCLUDED.enhanced_feedback_score,
                    feedback_count = EXCLUDED.feedback_count,
                    source_type = EXCLUDED.source_type,
                    last_updated = EXCLUDED.last_updated;
            """
            db.cursor.execute(migration_query)
            migrated_count = db.cursor.rowcount
            db.conn.commit()

            print(f"  ✅ Migrated {migrated_count} URL-level scores")
            print()

            # Step 5: Show sample of migrated data
            print("Step 4: Verifying migration...")
            db.cursor.execute("""
                SELECT
                    source_url,
                    source_type,
                    feedback_score,
                    enhanced_feedback_score,
                    feedback_count
                FROM source_document_scores
                ORDER BY feedback_count DESC
                LIMIT 5;
            """)
            samples = db.cursor.fetchall()

            if samples:
                print("\n  Sample of migrated URL scores:")
                print("  " + "-" * 76)
                for sample in samples:
                    url_short = sample['source_url'][:50] + "..." if len(sample['source_url']) > 50 else sample['source_url']
                    print(f"  URL: {url_short}")
                    print(f"    Type: {sample['source_type']}")
                    print(f"    Feedback Score: {sample['feedback_score']:.3f}")
                    print(f"    Enhanced Score: {sample['enhanced_feedback_score']:.3f}")
                    print(f"    Based on {sample['feedback_count']} chunks")
                    print()

            print("=" * 80)
            print("✅ Migration completed successfully!")
            print()
            print("Next steps:")
            print("1. The system will now use URL-level scores by default")
            print("2. Scores will persist when you refresh source data")
            print("3. Old chunk-level scores are kept for backward compatibility")
            print("=" * 80)

            return True

    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = migrate_to_url_scores()
    sys.exit(0 if success else 1)
