"""
LiveRecall Database
SQLite + sqlite-vec for vector similarity search
"""
import sqlite3
import struct
import time
from pathlib import Path
from typing import Optional
from contextlib import contextmanager

import sqlite_vec

from core.config import get_database_path

# CLIP ViT-L-14 produces 768-dimensional embeddings
EMBEDDING_DIM = 768


def serialize_embedding(embedding: list[float]) -> bytes:
    """Serialize embedding list to bytes for sqlite-vec"""
    return struct.pack(f"{len(embedding)}f", *embedding)


def deserialize_embedding(blob: bytes) -> list[float]:
    """Deserialize bytes back to embedding list"""
    return list(struct.unpack(f"{len(blob) // 4}f", blob))


class Database:
    """SQLite database with vector search support"""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or get_database_path()
        self.conn: Optional[sqlite3.Connection] = None

    def connect(self):
        """Connect to database and initialize sqlite-vec"""
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row

        # Load sqlite-vec extension
        self.conn.enable_load_extension(True)
        sqlite_vec.load(self.conn)
        self.conn.enable_load_extension(False)

        self._initialize_tables()
        return self

    def disconnect(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            self.conn = None

    @contextmanager
    def cursor(self):
        """Context manager for cursor"""
        cur = self.conn.cursor()
        try:
            yield cur
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise
        finally:
            cur.close()

    def _initialize_tables(self):
        """Create tables if they don't exist"""
        with self.cursor() as cur:
            # Main screenshots table (base schema without compression columns for migration compatibility)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS screenshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    image_path TEXT NOT NULL UNIQUE,
                    timestamp TEXT NOT NULL,
                    has_embedding INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Migration: add compression columns if they don't exist
            self._migrate_compression_columns(cur)

            # Index for faster queries
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_screenshots_timestamp
                ON screenshots(timestamp)
            """)

            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_screenshots_has_embedding
                ON screenshots(has_embedding)
            """)

            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_screenshots_is_compressed
                ON screenshots(is_compressed)
            """)

            # Virtual table for vector search
            cur.execute(f"""
                CREATE VIRTUAL TABLE IF NOT EXISTS screenshot_embeddings
                USING vec0(
                    screenshot_id INTEGER PRIMARY KEY,
                    embedding float[{EMBEDDING_DIM}]
                )
            """)

    def _migrate_compression_columns(self, cur):
        """Add compression columns to existing databases"""
        # Check if columns exist
        cur.execute("PRAGMA table_info(screenshots)")
        columns = {row[1] for row in cur.fetchall()}

        if "is_compressed" not in columns:
            cur.execute("ALTER TABLE screenshots ADD COLUMN is_compressed INTEGER DEFAULT 0")

        if "original_size_bytes" not in columns:
            cur.execute("ALTER TABLE screenshots ADD COLUMN original_size_bytes INTEGER")

        if "compressed_at" not in columns:
            cur.execute("ALTER TABLE screenshots ADD COLUMN compressed_at TEXT")

    # --- Screenshot CRUD ---

    def add_screenshot(self, image_path: str, timestamp: Optional[str] = None) -> int:
        """Add a new screenshot (without embedding)"""
        if timestamp is None:
            timestamp = time.strftime("%y%m%d%H%M%S")

        with self.cursor() as cur:
            cur.execute(
                "INSERT INTO screenshots (image_path, timestamp, has_embedding) VALUES (?, ?, 0)",
                (image_path, timestamp)
            )
            return cur.lastrowid

    def get_screenshot(self, screenshot_id: int) -> Optional[dict]:
        """Get a screenshot by ID"""
        with self.cursor() as cur:
            cur.execute("SELECT * FROM screenshots WHERE id = ?", (screenshot_id,))
            row = cur.fetchone()
            return dict(row) if row else None

    def get_screenshot_by_path(self, image_path: str) -> Optional[dict]:
        """Get a screenshot by path"""
        with self.cursor() as cur:
            cur.execute("SELECT * FROM screenshots WHERE image_path = ?", (image_path,))
            row = cur.fetchone()
            return dict(row) if row else None

    def delete_screenshot(self, screenshot_id: int) -> bool:
        """Delete a screenshot and its embedding"""
        with self.cursor() as cur:
            # Delete embedding first
            cur.execute(
                "DELETE FROM screenshot_embeddings WHERE screenshot_id = ?",
                (screenshot_id,)
            )
            # Delete screenshot
            cur.execute("DELETE FROM screenshots WHERE id = ?", (screenshot_id,))
            return cur.rowcount > 0

    def get_all_screenshots(
        self,
        limit: Optional[int] = None,
        offset: int = 0,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> list[dict]:
        """Get all screenshots with pagination and optional date filtering.

        Args:
            limit: Max results to return
            offset: Number of results to skip
            start_date: Filter screenshots after this timestamp (YYMMDDHHMMSS format)
            end_date: Filter screenshots before this timestamp (YYMMDDHHMMSS format)
        """
        with self.cursor() as cur:
            conditions = []
            params = []

            if start_date:
                conditions.append("timestamp >= ?")
                params.append(start_date)
            if end_date:
                conditions.append("timestamp <= ?")
                params.append(end_date)

            where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

            if limit:
                query = f"SELECT * FROM screenshots {where_clause} ORDER BY timestamp DESC LIMIT ? OFFSET ?"
                params.extend([limit, offset])
            else:
                query = f"SELECT * FROM screenshots {where_clause} ORDER BY timestamp DESC"

            cur.execute(query, params)
            return [dict(row) for row in cur.fetchall()]

    def get_screenshots_count(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> int:
        """Get count of screenshots with optional date filtering."""
        with self.cursor() as cur:
            conditions = []
            params = []

            if start_date:
                conditions.append("timestamp >= ?")
                params.append(start_date)
            if end_date:
                conditions.append("timestamp <= ?")
                params.append(end_date)

            where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
            cur.execute(f"SELECT COUNT(*) FROM screenshots {where_clause}", params)
            return cur.fetchone()[0]

    def get_date_range(self) -> dict:
        """Get the min and max timestamps in the database."""
        with self.cursor() as cur:
            cur.execute("SELECT MIN(timestamp), MAX(timestamp) FROM screenshots")
            row = cur.fetchone()
            return {
                "min_date": row[0],
                "max_date": row[1]
            }

    def get_density_data(self, buckets: int = 100) -> list[dict]:
        """Get screenshot count per time bucket for timeline density visualization.

        Returns a list of buckets with start timestamp, end timestamp, and count.
        """
        from datetime import datetime, timedelta

        with self.cursor() as cur:
            # Get date range
            cur.execute("SELECT MIN(timestamp), MAX(timestamp), COUNT(*) FROM screenshots")
            row = cur.fetchone()
            min_ts, max_ts, total = row[0], row[1], row[2]

            if not min_ts or not max_ts or total == 0:
                return []

            def parse_ts(ts: str) -> datetime:
                """Convert YYMMDDHHMMSS to datetime."""
                if len(ts) != 12:
                    return datetime.now()
                year = 2000 + int(ts[0:2])
                month = int(ts[2:4])
                day = int(ts[4:6])
                hour = int(ts[6:8])
                minute = int(ts[8:10])
                second = int(ts[10:12])
                return datetime(year, month, day, hour, minute, second)

            def format_ts(dt: datetime) -> str:
                """Convert datetime back to YYMMDDHHMMSS format."""
                return dt.strftime("%y%m%d%H%M%S")

            min_dt = parse_ts(min_ts)
            max_dt = parse_ts(max_ts)

            if max_dt <= min_dt:
                return [{"start": min_ts, "end": max_ts, "count": total}]

            total_seconds = (max_dt - min_dt).total_seconds()
            bucket_seconds = total_seconds / buckets
            result = []

            for i in range(buckets):
                bucket_start_dt = min_dt + timedelta(seconds=i * bucket_seconds)
                bucket_end_dt = min_dt + timedelta(seconds=(i + 1) * bucket_seconds)

                start_ts = format_ts(bucket_start_dt)
                end_ts = format_ts(bucket_end_dt)

                cur.execute(
                    "SELECT COUNT(*) FROM screenshots WHERE timestamp >= ? AND timestamp < ?",
                    (start_ts, end_ts)
                )
                count = cur.fetchone()[0]

                result.append({
                    "start": start_ts,
                    "end": end_ts,
                    "count": count
                })

            return result

    # --- Embedding operations ---

    def get_unsynced_screenshots(self, limit: Optional[int] = None) -> list[dict]:
        """Get screenshots that don't have embeddings yet"""
        with self.cursor() as cur:
            if limit:
                cur.execute(
                    "SELECT * FROM screenshots WHERE has_embedding = 0 ORDER BY id ASC LIMIT ?",
                    (limit,)
                )
            else:
                cur.execute(
                    "SELECT * FROM screenshots WHERE has_embedding = 0 ORDER BY id ASC"
                )
            return [dict(row) for row in cur.fetchall()]

    def get_unsynced_count(self) -> int:
        """Get count of screenshots without embeddings"""
        with self.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM screenshots WHERE has_embedding = 0")
            return cur.fetchone()[0]

    def add_embedding(self, screenshot_id: int, embedding: list[float]) -> bool:
        """Add embedding for a screenshot"""
        if len(embedding) != EMBEDDING_DIM:
            raise ValueError(f"Embedding must be {EMBEDDING_DIM} dimensions, got {len(embedding)}")

        embedding_bytes = serialize_embedding(embedding)

        with self.cursor() as cur:
            # Insert into vector table
            cur.execute(
                "INSERT INTO screenshot_embeddings (screenshot_id, embedding) VALUES (?, ?)",
                (screenshot_id, embedding_bytes)
            )
            # Mark screenshot as having embedding
            cur.execute(
                "UPDATE screenshots SET has_embedding = 1 WHERE id = ?",
                (screenshot_id,)
            )
            return True

    def search_similar(
        self,
        query_embedding: list[float],
        limit: int = 10,
        min_similarity: float = 0.0,
        similarity_metric: str = "cosine"
    ) -> list[dict]:
        """Search for similar screenshots using vector similarity

        Args:
            query_embedding: The query embedding vector
            limit: Maximum number of results
            min_similarity: Minimum similarity threshold
            similarity_metric: "cosine" for cosine similarity or "distance" for 1/(1+L2)
        """
        if len(query_embedding) != EMBEDDING_DIM:
            raise ValueError(f"Query embedding must be {EMBEDDING_DIM} dimensions")

        query_bytes = serialize_embedding(query_embedding)

        with self.cursor() as cur:
            # sqlite-vec uses L2 distance, lower is more similar
            cur.execute("""
                SELECT
                    s.*,
                    e.distance as vec_distance
                FROM screenshot_embeddings e
                JOIN screenshots s ON s.id = e.screenshot_id
                WHERE e.embedding MATCH ?
                    AND k = ?
                ORDER BY e.distance ASC
            """, (query_bytes, limit))

            results = []
            for row in cur.fetchall():
                result = dict(row)
                distance = result.pop("vec_distance", 0)

                if similarity_metric == "cosine":
                    # Convert L2 distance to cosine similarity
                    # For normalized vectors: L2² = 2(1 - cosine_sim)
                    # So: cosine_sim = 1 - L2²/2
                    similarity = max(0.0, min(1.0, 1.0 - (distance ** 2) / 2))
                else:
                    # Use inverse distance: 1 / (1 + distance)
                    similarity = 1.0 / (1.0 + distance)

                result["similarity"] = similarity
                if result["similarity"] >= min_similarity:
                    results.append(result)

            return results

    # --- Compression operations ---

    def get_compressible_screenshots(self, older_than_days: int, limit: Optional[int] = None) -> list[dict]:
        """Get screenshots eligible for compression (old + not compressed)"""
        with self.cursor() as cur:
            query = """
                SELECT * FROM screenshots
                WHERE is_compressed = 0
                AND created_at < datetime('now', ?)
                ORDER BY created_at ASC
            """
            days_ago = f"-{older_than_days} days"

            if limit:
                query += " LIMIT ?"
                cur.execute(query, (days_ago, limit))
            else:
                cur.execute(query, (days_ago,))

            return [dict(row) for row in cur.fetchall()]

    def get_compressible_count(self, older_than_days: int) -> int:
        """Get count of screenshots eligible for compression"""
        with self.cursor() as cur:
            cur.execute("""
                SELECT COUNT(*) FROM screenshots
                WHERE is_compressed = 0
                AND created_at < datetime('now', ?)
            """, (f"-{older_than_days} days",))
            return cur.fetchone()[0]

    def mark_compressed(
        self,
        screenshot_id: int,
        original_size: int,
    ) -> bool:
        """Mark a screenshot as compressed"""
        with self.cursor() as cur:
            cur.execute("""
                UPDATE screenshots
                SET is_compressed = 1,
                    original_size_bytes = ?,
                    compressed_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (original_size, screenshot_id))
            return cur.rowcount > 0

    def get_compression_stats(self) -> dict:
        """Get compression statistics"""
        with self.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM screenshots WHERE is_compressed = 1")
            compressed_count = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM screenshots WHERE is_compressed = 0")
            uncompressed_count = cur.fetchone()[0]

            cur.execute("SELECT SUM(original_size_bytes) FROM screenshots WHERE is_compressed = 1")
            original_total = cur.fetchone()[0] or 0

            return {
                "compressed_count": compressed_count,
                "uncompressed_count": uncompressed_count,
                "original_size_bytes": original_total,
            }

    # --- Stats ---

    def get_stats(self) -> dict:
        """Get database statistics"""
        with self.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM screenshots")
            total = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM screenshots WHERE has_embedding = 1")
            synced = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM screenshots WHERE has_embedding = 0")
            unsynced = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM screenshots WHERE is_compressed = 1")
            compressed = cur.fetchone()[0]

            return {
                "total_screenshots": total,
                "synced": synced,
                "unsynced": unsynced,
                "compressed": compressed,
            }

    def clear_all(self) -> bool:
        """Clear all data (dangerous!)"""
        with self.cursor() as cur:
            cur.execute("DELETE FROM screenshot_embeddings")
            cur.execute("DELETE FROM screenshots")
            return True


# Global database instance
db = Database()


if __name__ == "__main__":
    # Test the database
    db.connect()
    print(f"Database at: {db.db_path}")
    print(f"Stats: {db.get_stats()}")
    db.disconnect()
