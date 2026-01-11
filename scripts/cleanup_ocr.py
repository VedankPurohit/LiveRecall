#!/usr/bin/env python3
"""
Cleanup script to reset OCR data before restarting the app.
Run this after fixing bugs in the OCR processing pipeline.

Usage:
    uv run python scripts/cleanup_ocr.py
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.database import db


def main():
    print("OCR Data Cleanup Script")
    print("=" * 50)

    # Connect to database
    db.connect()

    try:
        # Get current stats
        with db.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM screenshots")
            total_screenshots = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM screenshots WHERE has_ocr = 1")
            with_ocr = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM screenshot_ocr")
            ocr_records = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM ocr_text_chunks")
            chunk_records = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM ocr_text_embeddings")
            embedding_records = cur.fetchone()[0]

        print("\nCurrent database state:")
        print(f"  Total screenshots: {total_screenshots}")
        print(f"  Screenshots with has_ocr=1: {with_ocr}")
        print(f"  OCR records: {ocr_records}")
        print(f"  Chunk records: {chunk_records}")
        print(f"  Text embedding records: {embedding_records}")

        # Check for inconsistencies
        with db.cursor() as cur:
            # Screenshots marked as having OCR but no actual OCR record
            cur.execute("""
                SELECT COUNT(*) FROM screenshots s
                WHERE s.has_ocr = 1
                AND NOT EXISTS (SELECT 1 FROM screenshot_ocr o WHERE o.screenshot_id = s.id)
            """)
            orphan_has_ocr = cur.fetchone()[0]

            # OCR records without any chunks (could be intentional if text was empty)
            cur.execute("""
                SELECT COUNT(*) FROM screenshot_ocr o
                WHERE NOT EXISTS (SELECT 1 FROM ocr_text_chunks c WHERE c.ocr_id = o.id)
                AND o.full_text != ''
            """)
            ocr_without_chunks = cur.fetchone()[0]

            # Chunks without embeddings
            cur.execute("""
                SELECT COUNT(*) FROM ocr_text_chunks c
                WHERE NOT EXISTS (SELECT 1 FROM ocr_text_embeddings e WHERE e.chunk_id = c.id)
            """)
            chunks_without_embeddings = cur.fetchone()[0]

        print("\nInconsistencies found:")
        print(f"  Screenshots with has_ocr=1 but no OCR record: {orphan_has_ocr}")
        print(f"  OCR records with text but no chunks: {ocr_without_chunks}")
        print(f"  Chunks without embeddings: {chunks_without_embeddings}")

        if orphan_has_ocr > 0 or ocr_without_chunks > 0 or chunks_without_embeddings > 0:
            print("\n" + "=" * 50)
            print("Found inconsistencies! Recommend full OCR reset.")
            print("=" * 50)

            response = input("\nReset ALL OCR data and reprocess? (y/N): ")
            if response.lower() == "y":
                print("\nResetting all OCR data...")
                count = db.reset_all_ocr()
                print(f"Reset complete. {count} screenshots will be reprocessed on next sync.")
            else:
                print("\nSkipped reset. You can manually fix issues or run this script again.")
        else:
            print("\nNo inconsistencies found!")
            response = input("\nDo you still want to reset ALL OCR data? (y/N): ")
            if response.lower() == "y":
                print("\nResetting all OCR data...")
                count = db.reset_all_ocr()
                print(f"Reset complete. {count} screenshots will be reprocessed on next sync.")

    finally:
        db.disconnect()

    print("\nDone! You can now restart the app.")


if __name__ == "__main__":
    main()
