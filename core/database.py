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
            # Main screenshots table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS screenshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    image_path TEXT NOT NULL UNIQUE,
                    timestamp TEXT NOT NULL,
                    has_embedding INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Index for faster queries
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_screenshots_timestamp
                ON screenshots(timestamp)
            """)

            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_screenshots_has_embedding
                ON screenshots(has_embedding)
            """)

            # Virtual table for vector search
            cur.execute(f"""
                CREATE VIRTUAL TABLE IF NOT EXISTS screenshot_embeddings
                USING vec0(
                    screenshot_id INTEGER PRIMARY KEY,
                    embedding float[{EMBEDDING_DIM}]
                )
            """)

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

    def get_all_screenshots(self, limit: Optional[int] = None, offset: int = 0) -> list[dict]:
        """Get all screenshots with pagination"""
        with self.cursor() as cur:
            if limit:
                cur.execute(
                    "SELECT * FROM screenshots ORDER BY timestamp DESC LIMIT ? OFFSET ?",
                    (limit, offset)
                )
            else:
                cur.execute("SELECT * FROM screenshots ORDER BY timestamp DESC")
            return [dict(row) for row in cur.fetchall()]

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
        min_similarity: float = 0.0
    ) -> list[dict]:
        """Search for similar screenshots using vector similarity"""
        if len(query_embedding) != EMBEDDING_DIM:
            raise ValueError(f"Query embedding must be {EMBEDDING_DIM} dimensions")

        query_bytes = serialize_embedding(query_embedding)

        with self.cursor() as cur:
            # sqlite-vec uses L2 distance, lower is more similar
            # We convert to similarity score (1 / (1 + distance))
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
                # Convert distance to similarity (0-1 scale, 1 = most similar)
                distance = result.pop("vec_distance", 0)
                result["similarity"] = 1 / (1 + distance)
                if result["similarity"] >= min_similarity:
                    results.append(result)

            return results

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

            return {
                "total_screenshots": total,
                "synced": synced,
                "unsynced": unsynced,
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
