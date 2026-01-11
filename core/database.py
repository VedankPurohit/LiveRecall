"""
LiveRecall Database
SQLite + sqlite-vec for vector similarity search
"""

import sqlite3
import struct
import threading
import time
from contextlib import contextmanager
from pathlib import Path

import sqlite_vec

from core.config import get_database_path

# CLIP ViT-L-14 produces 768-dimensional embeddings
EMBEDDING_DIM = 768

# BGE-small-en-v1.5 produces 384-dimensional text embeddings
TEXT_EMBEDDING_DIM = 384


def serialize_embedding(embedding: list[float]) -> bytes:
    """Serialize embedding list to bytes for sqlite-vec"""
    return struct.pack(f"{len(embedding)}f", *embedding)


def deserialize_embedding(blob: bytes) -> list[float]:
    """Deserialize bytes back to embedding list"""
    return list(struct.unpack(f"{len(blob) // 4}f", blob))


class Database:
    """SQLite database with vector search support"""

    def __init__(self, db_path: Path | None = None):
        self.db_path = db_path or get_database_path()
        self.conn: sqlite3.Connection | None = None
        self._lock = threading.Lock()  # Thread safety for concurrent access

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
        """Context manager for cursor with thread-safe locking"""
        with self._lock:  # Ensure only one thread accesses DB at a time
            if self.conn is None:
                raise RuntimeError("Database not connected")
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

            # Migration: add is_hidden column if it doesn't exist
            self._migrate_hidden_column(cur)

            # Migration: add has_ocr column if it doesn't exist
            self._migrate_ocr_column(cur)

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

            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_screenshots_is_hidden
                ON screenshots(is_hidden)
            """)

            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_screenshots_has_ocr
                ON screenshots(has_ocr)
            """)

            # Virtual table for vector search (CLIP image embeddings)
            cur.execute(f"""
                CREATE VIRTUAL TABLE IF NOT EXISTS screenshot_embeddings
                USING vec0(
                    screenshot_id INTEGER PRIMARY KEY,
                    embedding float[{EMBEDDING_DIM}]
                )
            """)

            # OCR tables
            self._initialize_ocr_tables(cur)

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

    def _migrate_hidden_column(self, cur):
        """Add is_hidden column to existing databases"""
        cur.execute("PRAGMA table_info(screenshots)")
        columns = {row[1] for row in cur.fetchall()}

        if "is_hidden" not in columns:
            cur.execute("ALTER TABLE screenshots ADD COLUMN is_hidden INTEGER DEFAULT 0")

    def _migrate_ocr_column(self, cur):
        """Add has_ocr column to existing databases"""
        cur.execute("PRAGMA table_info(screenshots)")
        columns = {row[1] for row in cur.fetchall()}

        if "has_ocr" not in columns:
            cur.execute("ALTER TABLE screenshots ADD COLUMN has_ocr INTEGER DEFAULT 0")

    def _initialize_ocr_tables(self, cur):
        """Create OCR-related tables if they don't exist"""
        # Main OCR text table - stores full extracted text per screenshot
        cur.execute("""
            CREATE TABLE IF NOT EXISTS screenshot_ocr (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                screenshot_id INTEGER NOT NULL UNIQUE,
                full_text TEXT NOT NULL,
                confidence REAL,
                word_count INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (screenshot_id) REFERENCES screenshots(id) ON DELETE CASCADE
            )
        """)

        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_screenshot_ocr_screenshot_id
            ON screenshot_ocr(screenshot_id)
        """)

        # Text chunks table - stores dual-size chunks for semantic search
        cur.execute("""
            CREATE TABLE IF NOT EXISTS ocr_text_chunks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ocr_id INTEGER NOT NULL,
                chunk_size TEXT NOT NULL,
                chunk_index INTEGER NOT NULL,
                chunk_text TEXT NOT NULL,
                start_char INTEGER,
                end_char INTEGER,
                FOREIGN KEY (ocr_id) REFERENCES screenshot_ocr(id) ON DELETE CASCADE
            )
        """)

        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_ocr_chunks_ocr_id
            ON ocr_text_chunks(ocr_id)
        """)

        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_ocr_chunks_size
            ON ocr_text_chunks(chunk_size)
        """)

        # FTS5 virtual table for fuzzy text search with trigram tokenizer
        # Note: tokenize='trigram' requires SQLite 3.34+
        try:
            cur.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS ocr_text_fts USING fts5(
                    full_text,
                    content='screenshot_ocr',
                    content_rowid='id',
                    tokenize='trigram'
                )
            """)
        except sqlite3.OperationalError:
            # Fall back to default tokenizer if trigram not available
            cur.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS ocr_text_fts USING fts5(
                    full_text,
                    content='screenshot_ocr',
                    content_rowid='id'
                )
            """)

        # Triggers to keep FTS index in sync with screenshot_ocr table
        cur.execute("""
            CREATE TRIGGER IF NOT EXISTS ocr_fts_insert AFTER INSERT ON screenshot_ocr BEGIN
                INSERT INTO ocr_text_fts(rowid, full_text) VALUES (new.id, new.full_text);
            END
        """)

        cur.execute("""
            CREATE TRIGGER IF NOT EXISTS ocr_fts_delete AFTER DELETE ON screenshot_ocr BEGIN
                INSERT INTO ocr_text_fts(ocr_text_fts, rowid, full_text)
                VALUES ('delete', old.id, old.full_text);
            END
        """)

        cur.execute("""
            CREATE TRIGGER IF NOT EXISTS ocr_fts_update AFTER UPDATE ON screenshot_ocr BEGIN
                INSERT INTO ocr_text_fts(ocr_text_fts, rowid, full_text)
                VALUES ('delete', old.id, old.full_text);
                INSERT INTO ocr_text_fts(rowid, full_text) VALUES (new.id, new.full_text);
            END
        """)

        # Vector table for text chunk embeddings (BGE-small: 384 dimensions)
        cur.execute(f"""
            CREATE VIRTUAL TABLE IF NOT EXISTS ocr_text_embeddings
            USING vec0(
                chunk_id INTEGER PRIMARY KEY,
                embedding float[{TEXT_EMBEDDING_DIM}]
            )
        """)

    # --- Screenshot CRUD ---

    def add_screenshot(self, image_path: str, timestamp: str | None = None, is_hidden: bool = False) -> int:
        """Add a new screenshot (without embedding)

        Args:
            image_path: Path to the screenshot image
            timestamp: Timestamp in YYMMDDHHMMSS format (auto-generated if None)
            is_hidden: Whether the screenshot should be hidden (for incognito mode)
        """
        if timestamp is None:
            timestamp = time.strftime("%y%m%d%H%M%S")

        with self.cursor() as cur:
            cur.execute(
                "INSERT INTO screenshots (image_path, timestamp, has_embedding, is_hidden) VALUES (?, ?, 0, ?)",
                (image_path, timestamp, 1 if is_hidden else 0),
            )
            return cur.lastrowid

    def get_screenshot(self, screenshot_id: int) -> dict | None:
        """Get a screenshot by ID"""
        with self.cursor() as cur:
            cur.execute("SELECT * FROM screenshots WHERE id = ?", (screenshot_id,))
            row = cur.fetchone()
            return dict(row) if row else None

    def get_screenshot_by_path(self, image_path: str) -> dict | None:
        """Get a screenshot by path"""
        with self.cursor() as cur:
            cur.execute("SELECT * FROM screenshots WHERE image_path = ?", (image_path,))
            row = cur.fetchone()
            return dict(row) if row else None

    def delete_screenshot(self, screenshot_id: int) -> bool:
        """Delete a screenshot and its embedding"""
        with self.cursor() as cur:
            # Delete embedding first
            cur.execute("DELETE FROM screenshot_embeddings WHERE screenshot_id = ?", (screenshot_id,))
            # Delete screenshot
            cur.execute("DELETE FROM screenshots WHERE id = ?", (screenshot_id,))
            return cur.rowcount > 0

    def delete_screenshots_bulk(self, screenshot_ids: list[int]) -> list[str]:
        """Delete multiple screenshots and their embeddings.

        Args:
            screenshot_ids: List of screenshot IDs to delete

        Returns:
            List of image paths that were deleted (for file cleanup)
        """
        if not screenshot_ids:
            return []

        with self.cursor() as cur:
            placeholders = ",".join("?" * len(screenshot_ids))

            # Get paths first for file cleanup
            cur.execute(
                f"SELECT image_path FROM screenshots WHERE id IN ({placeholders})",
                screenshot_ids,
            )
            paths = [row[0] for row in cur.fetchall()]

            # Delete embeddings first (foreign key relationship)
            cur.execute(
                f"DELETE FROM screenshot_embeddings WHERE screenshot_id IN ({placeholders})",
                screenshot_ids,
            )

            # Delete screenshots
            cur.execute(
                f"DELETE FROM screenshots WHERE id IN ({placeholders})",
                screenshot_ids,
            )

            return paths

    def set_screenshots_hidden(self, screenshot_ids: list[int], is_hidden: bool) -> int:
        """Set the hidden status of multiple screenshots.

        Args:
            screenshot_ids: List of screenshot IDs to update
            is_hidden: Whether to hide (True) or unhide (False)

        Returns:
            Number of rows affected
        """
        if not screenshot_ids:
            return 0

        with self.cursor() as cur:
            placeholders = ",".join("?" * len(screenshot_ids))
            cur.execute(
                f"UPDATE screenshots SET is_hidden = ? WHERE id IN ({placeholders})",
                [1 if is_hidden else 0] + screenshot_ids,
            )
            return cur.rowcount

    def get_all_screenshots(
        self,
        limit: int | None = None,
        offset: int = 0,
        start_date: str | None = None,
        end_date: str | None = None,
        visibility: str = "visible_only",
    ) -> list[dict]:
        """Get all screenshots with pagination, date filtering, and visibility filter.

        Args:
            limit: Max results to return
            offset: Number of results to skip
            start_date: Filter screenshots after this timestamp (YYMMDDHHMMSS format)
            end_date: Filter screenshots before this timestamp (YYMMDDHHMMSS format)
            visibility: One of "visible_only", "hidden_only", or "all"
        """
        with self.cursor() as cur:
            conditions: list[str] = []
            params: list[str | int] = []

            # Visibility filter
            if visibility == "visible_only":
                conditions.append("(is_hidden = 0 OR is_hidden IS NULL)")
            elif visibility == "hidden_only":
                conditions.append("is_hidden = 1")
            # "all" - no visibility condition

            if start_date:
                conditions.append("timestamp >= ?")
                params.append(start_date)
            if end_date:
                conditions.append("timestamp <= ?")
                params.append(end_date)

            where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

            if limit:
                query = f"SELECT * FROM screenshots {where_clause} ORDER BY timestamp DESC, id DESC LIMIT ? OFFSET ?"
                params.extend([limit, offset])
            else:
                query = f"SELECT * FROM screenshots {where_clause} ORDER BY timestamp DESC, id DESC"

            cur.execute(query, params)
            return [dict(row) for row in cur.fetchall()]

    def get_screenshot_offset(
        self,
        screenshot_id: int,
        visibility: str = "visible_only",
    ) -> int | None:
        """Get the offset/position of a screenshot in the sorted list (timestamp DESC, id DESC).

        Returns the number of screenshots that come before this one in the sorted order.
        Returns None if screenshot not found.

        Args:
            screenshot_id: The ID of the screenshot
            visibility: One of "visible_only", "hidden_only", or "all"
        """
        with self.cursor() as cur:
            # First get the target screenshot's timestamp and id
            cur.execute("SELECT timestamp, id FROM screenshots WHERE id = ?", [screenshot_id])
            row = cur.fetchone()
            if not row:
                return None
            target_ts = row[0]
            target_id = row[1]

            # Count screenshots that come BEFORE this one in ORDER BY timestamp DESC, id DESC
            # A screenshot comes before if:
            # - timestamp > target_ts, OR
            # - timestamp = target_ts AND id > target_id
            vis_condition = ""
            if visibility == "visible_only":
                vis_condition = "AND (is_hidden = 0 OR is_hidden IS NULL)"
            elif visibility == "hidden_only":
                vis_condition = "AND is_hidden = 1"
            # "all" - no visibility condition

            query = f"""
                SELECT COUNT(*) FROM screenshots
                WHERE (timestamp > ? OR (timestamp = ? AND id > ?))
                {vis_condition}
            """
            cur.execute(query, [target_ts, target_ts, target_id])
            return cur.fetchone()[0]

    def get_screenshots_count(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
        visibility: str = "visible_only",
    ) -> int:
        """Get count of screenshots with optional date filtering and visibility filter."""
        with self.cursor() as cur:
            conditions = []
            params = []

            # Visibility filter
            if visibility == "visible_only":
                conditions.append("(is_hidden = 0 OR is_hidden IS NULL)")
            elif visibility == "hidden_only":
                conditions.append("is_hidden = 1")
            # "all" - no visibility condition

            if start_date:
                conditions.append("timestamp >= ?")
                params.append(start_date)
            if end_date:
                conditions.append("timestamp <= ?")
                params.append(end_date)

            where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
            cur.execute(f"SELECT COUNT(*) FROM screenshots {where_clause}", params)
            return cur.fetchone()[0]

    def get_date_range(self, visibility: str = "visible_only") -> dict:
        """Get the min and max timestamps in the database."""
        with self.cursor() as cur:
            if visibility == "visible_only":
                where = "WHERE (is_hidden = 0 OR is_hidden IS NULL)"
            elif visibility == "hidden_only":
                where = "WHERE is_hidden = 1"
            else:
                where = ""

            cur.execute(f"SELECT MIN(timestamp), MAX(timestamp) FROM screenshots {where}")
            row = cur.fetchone()
            return {"min_date": row[0], "max_date": row[1]}

    def get_density_data(self, buckets: int = 100, visibility: str = "visible_only") -> list[dict]:
        """Get screenshot count per time bucket for timeline density visualization.

        Args:
            buckets: Number of time buckets to divide the range into
            visibility: One of "visible_only", "hidden_only", or "all"

        Returns a list of buckets with start timestamp, end timestamp, and count.
        """
        from datetime import datetime, timedelta

        # Build visibility condition
        if visibility == "visible_only":
            vis_condition = "(is_hidden = 0 OR is_hidden IS NULL)"
        elif visibility == "hidden_only":
            vis_condition = "is_hidden = 1"
        else:
            vis_condition = "1=1"

        with self.cursor() as cur:
            # Get date range
            cur.execute(f"SELECT MIN(timestamp), MAX(timestamp), COUNT(*) FROM screenshots WHERE {vis_condition}")
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
                    f"SELECT COUNT(*) FROM screenshots WHERE {vis_condition} AND timestamp >= ? AND timestamp < ?",
                    (start_ts, end_ts),
                )
                count = cur.fetchone()[0]

                result.append({"start": start_ts, "end": end_ts, "count": count})

            return result

    # --- Embedding operations ---

    def get_unsynced_screenshots(self, limit: int | None = None) -> list[dict]:
        """Get screenshots that don't have embeddings yet"""
        with self.cursor() as cur:
            if limit:
                cur.execute("SELECT * FROM screenshots WHERE has_embedding = 0 ORDER BY id ASC LIMIT ?", (limit,))
            else:
                cur.execute("SELECT * FROM screenshots WHERE has_embedding = 0 ORDER BY id ASC")
            return [dict(row) for row in cur.fetchall()]

    def get_unsynced_count(self) -> int:
        """Get count of screenshots without embeddings"""
        with self.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM screenshots WHERE has_embedding = 0")
            return cur.fetchone()[0]

    def get_screenshot_count(self) -> int:
        """Get total count of all screenshots"""
        with self.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM screenshots")
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
                (screenshot_id, embedding_bytes),
            )
            # Mark screenshot as having embedding
            cur.execute("UPDATE screenshots SET has_embedding = 1 WHERE id = ?", (screenshot_id,))
            return True

    def search_similar(
        self,
        query_embedding: list[float],
        limit: int = 10,
        min_similarity: float = 0.0,
        similarity_metric: str = "cosine",
        visibility: str = "visible_only",
    ) -> list[dict]:
        """Search for similar screenshots using vector similarity

        Args:
            query_embedding: The query embedding vector
            limit: Maximum number of results
            min_similarity: Minimum similarity threshold
            similarity_metric: "cosine" for cosine similarity or "distance" for 1/(1+L2)
            visibility: One of "visible_only", "hidden_only", or "all"
        """
        if len(query_embedding) != EMBEDDING_DIM:
            raise ValueError(f"Query embedding must be {EMBEDDING_DIM} dimensions")

        query_bytes = serialize_embedding(query_embedding)

        # Build visibility condition
        if visibility == "visible_only":
            vis_condition = "AND (s.is_hidden = 0 OR s.is_hidden IS NULL)"
        elif visibility == "hidden_only":
            vis_condition = "AND s.is_hidden = 1"
        else:
            vis_condition = ""

        with self.cursor() as cur:
            # sqlite-vec uses L2 distance, lower is more similar
            # Note: We fetch more than limit to account for visibility filtering
            cur.execute(
                f"""
                SELECT
                    s.*,
                    e.distance as vec_distance
                FROM screenshot_embeddings e
                JOIN screenshots s ON s.id = e.screenshot_id
                WHERE e.embedding MATCH ?
                    AND k = ?
                    {vis_condition}
                ORDER BY e.distance ASC
            """,
                (query_bytes, limit * 2 if visibility != "all" else limit),
            )

            results = []
            for row in cur.fetchall():
                result = dict(row)
                distance = result.pop("vec_distance", 0)

                if similarity_metric == "cosine":
                    # Convert L2 distance to cosine similarity
                    # For normalized vectors: L2² = 2(1 - cosine_sim)
                    # So: cosine_sim = 1 - L2²/2
                    similarity = max(0.0, min(1.0, 1.0 - (distance**2) / 2))
                else:
                    # Use inverse distance: 1 / (1 + distance)
                    similarity = 1.0 / (1.0 + distance)

                result["similarity"] = similarity
                if result["similarity"] >= min_similarity:
                    results.append(result)
                    if len(results) >= limit:
                        break

            return results

    # --- Compression operations ---

    def get_compressible_screenshots(self, older_than_days: int, limit: int | None = None) -> list[dict]:
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
            cur.execute(
                """
                SELECT COUNT(*) FROM screenshots
                WHERE is_compressed = 0
                AND created_at < datetime('now', ?)
            """,
                (f"-{older_than_days} days",),
            )
            return cur.fetchone()[0]

    def mark_compressed(
        self,
        screenshot_id: int,
        original_size: int,
    ) -> bool:
        """Mark a screenshot as compressed"""
        with self.cursor() as cur:
            cur.execute(
                """
                UPDATE screenshots
                SET is_compressed = 1,
                    original_size_bytes = ?,
                    compressed_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """,
                (original_size, screenshot_id),
            )
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

    # --- OCR operations ---

    def add_ocr_text(
        self,
        screenshot_id: int,
        full_text: str,
        confidence: float | None = None,
        word_count: int | None = None,
    ) -> int:
        """Add OCR extracted text for a screenshot.

        Args:
            screenshot_id: ID of the screenshot
            full_text: Full extracted text (can be empty string)
            confidence: Average OCR confidence (0-1)
            word_count: Number of words extracted

        Returns:
            ID of the created screenshot_ocr record
        """
        if word_count is None:
            word_count = len(full_text.split()) if full_text else 0

        with self.cursor() as cur:
            # Use ON CONFLICT DO UPDATE to preserve the id (avoid orphaning chunks)
            cur.execute(
                """
                INSERT INTO screenshot_ocr (screenshot_id, full_text, confidence, word_count)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(screenshot_id) DO UPDATE SET
                    full_text = excluded.full_text,
                    confidence = excluded.confidence,
                    word_count = excluded.word_count
            """,
                (screenshot_id, full_text, confidence, word_count),
            )
            # Get the id (either new or existing)
            cur.execute(
                "SELECT id FROM screenshot_ocr WHERE screenshot_id = ?",
                (screenshot_id,),
            )
            return cur.fetchone()[0]

    def get_ocr_text(self, screenshot_id: int) -> dict | None:
        """Get OCR text for a screenshot"""
        with self.cursor() as cur:
            cur.execute("SELECT * FROM screenshot_ocr WHERE screenshot_id = ?", (screenshot_id,))
            row = cur.fetchone()
            return dict(row) if row else None

    def add_ocr_chunk(
        self,
        ocr_id: int,
        chunk_size: str,
        chunk_index: int,
        chunk_text: str,
        start_char: int | None = None,
        end_char: int | None = None,
    ) -> int:
        """Add a text chunk for an OCR record.

        Args:
            ocr_id: ID of the screenshot_ocr record
            chunk_size: 'small' or 'large'
            chunk_index: Index of this chunk in the sequence
            chunk_text: The chunk text
            start_char: Starting character position in full text
            end_char: Ending character position in full text

        Returns:
            ID of the created chunk record
        """
        with self.cursor() as cur:
            cur.execute(
                """
                INSERT INTO ocr_text_chunks (ocr_id, chunk_size, chunk_index, chunk_text, start_char, end_char)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (ocr_id, chunk_size, chunk_index, chunk_text, start_char, end_char),
            )
            return cur.lastrowid

    def add_text_embedding(self, chunk_id: int, embedding: list[float]) -> bool:
        """Add embedding for a text chunk"""
        if len(embedding) != TEXT_EMBEDDING_DIM:
            raise ValueError(f"Text embedding must be {TEXT_EMBEDDING_DIM} dimensions, got {len(embedding)}")

        embedding_bytes = serialize_embedding(embedding)

        with self.cursor() as cur:
            # Use INSERT OR REPLACE for idempotent reprocessing
            cur.execute(
                "INSERT OR REPLACE INTO ocr_text_embeddings (chunk_id, embedding) VALUES (?, ?)",
                (chunk_id, embedding_bytes),
            )
            return True

    def mark_ocr_complete(self, screenshot_id: int) -> bool:
        """Mark a screenshot as having OCR processed"""
        with self.cursor() as cur:
            cur.execute("UPDATE screenshots SET has_ocr = 1 WHERE id = ?", (screenshot_id,))
            return cur.rowcount > 0

    def get_screenshots_without_ocr(self, limit: int | None = None) -> list[dict]:
        """Get screenshots that don't have OCR processed yet"""
        with self.cursor() as cur:
            if limit:
                cur.execute(
                    "SELECT * FROM screenshots WHERE has_ocr = 0 ORDER BY id ASC LIMIT ?",
                    (limit,),
                )
            else:
                cur.execute("SELECT * FROM screenshots WHERE has_ocr = 0 ORDER BY id ASC")
            return [dict(row) for row in cur.fetchall()]

    def get_ocr_pending_count(self) -> int:
        """Get count of screenshots without OCR"""
        with self.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM screenshots WHERE has_ocr = 0")
            return cur.fetchone()[0]

    def search_ocr_fts(
        self,
        query: str,
        limit: int = 20,
        visibility: str = "visible_only",
    ) -> list[dict]:
        """Search OCR text using FTS5 full-text search.

        Uses trigram matching for fuzzy search if available.

        Args:
            query: Search query string
            limit: Maximum number of results
            visibility: One of "visible_only", "hidden_only", or "all"

        Returns:
            List of matching screenshots with OCR info and snippets
        """
        # Build visibility condition
        if visibility == "visible_only":
            vis_condition = "AND (s.is_hidden = 0 OR s.is_hidden IS NULL)"
        elif visibility == "hidden_only":
            vis_condition = "AND s.is_hidden = 1"
        else:
            vis_condition = ""

        with self.cursor() as cur:
            cur.execute(
                f"""
                SELECT
                    s.*,
                    o.full_text,
                    o.confidence as ocr_confidence,
                    o.word_count,
                    snippet(ocr_text_fts, 0, '<mark>', '</mark>', '...', 32) as ocr_snippet,
                    bm25(ocr_text_fts) as relevance_score
                FROM ocr_text_fts f
                JOIN screenshot_ocr o ON f.rowid = o.id
                JOIN screenshots s ON o.screenshot_id = s.id
                WHERE ocr_text_fts MATCH ?
                    {vis_condition}
                ORDER BY bm25(ocr_text_fts)
                LIMIT ?
            """,
                (query, limit),
            )

            return [dict(row) for row in cur.fetchall()]

    def search_ocr_exact(
        self,
        query: str,
        limit: int = 20,
        visibility: str = "visible_only",
    ) -> list[dict]:
        """Search OCR text for exact phrase match.

        Args:
            query: Exact phrase to search for
            limit: Maximum number of results
            visibility: One of "visible_only", "hidden_only", or "all"

        Returns:
            List of matching screenshots with OCR info
        """
        # Build visibility condition
        if visibility == "visible_only":
            vis_condition = "AND (s.is_hidden = 0 OR s.is_hidden IS NULL)"
        elif visibility == "hidden_only":
            vis_condition = "AND s.is_hidden = 1"
        else:
            vis_condition = ""

        # Quote query for exact phrase match in FTS5
        quoted_query = f'"{query}"'

        with self.cursor() as cur:
            cur.execute(
                f"""
                SELECT
                    s.*,
                    o.full_text,
                    o.confidence as ocr_confidence,
                    o.word_count,
                    highlight(ocr_text_fts, 0, '<mark>', '</mark>') as ocr_highlighted
                FROM ocr_text_fts f
                JOIN screenshot_ocr o ON f.rowid = o.id
                JOIN screenshots s ON o.screenshot_id = s.id
                WHERE ocr_text_fts MATCH ?
                    {vis_condition}
                ORDER BY s.timestamp DESC
                LIMIT ?
            """,
                (quoted_query, limit),
            )

            return [dict(row) for row in cur.fetchall()]

    def search_text_embeddings(
        self,
        query_embedding: list[float],
        chunk_size: str | None = None,
        limit: int = 20,
        visibility: str = "visible_only",
    ) -> list[dict]:
        """Search text chunks by semantic similarity.

        Args:
            query_embedding: Query embedding vector (384-dim)
            chunk_size: Filter by 'small' or 'large' chunks, or None for all
            limit: Maximum number of results
            visibility: One of "visible_only", "hidden_only", or "all"

        Returns:
            List of matching screenshots with similarity scores
        """
        if len(query_embedding) != TEXT_EMBEDDING_DIM:
            raise ValueError(f"Query embedding must be {TEXT_EMBEDDING_DIM} dimensions")

        query_bytes = serialize_embedding(query_embedding)

        # Build conditions with parameterized queries to prevent SQL injection
        params: list = [query_bytes, limit * 2]
        chunk_condition = ""
        if chunk_size:
            # Validate chunk_size to prevent SQL injection
            if chunk_size not in ("small", "large"):
                raise ValueError(f"chunk_size must be 'small' or 'large', got '{chunk_size}'")
            chunk_condition = "AND c.chunk_size = ?"
            params.append(chunk_size)

        if visibility == "visible_only":
            vis_condition = "AND (s.is_hidden = 0 OR s.is_hidden IS NULL)"
        elif visibility == "hidden_only":
            vis_condition = "AND s.is_hidden = 1"
        else:
            vis_condition = ""

        with self.cursor() as cur:
            cur.execute(
                f"""
                SELECT
                    s.*,
                    o.full_text,
                    o.confidence as ocr_confidence,
                    c.chunk_text,
                    c.chunk_size,
                    c.chunk_index,
                    e.distance as vec_distance
                FROM ocr_text_embeddings e
                JOIN ocr_text_chunks c ON c.id = e.chunk_id
                JOIN screenshot_ocr o ON o.id = c.ocr_id
                JOIN screenshots s ON s.id = o.screenshot_id
                WHERE e.embedding MATCH ?
                    AND k = ?
                    {chunk_condition}
                    {vis_condition}
                ORDER BY e.distance ASC
            """,
                params,
            )

            results = []
            seen_screenshots = set()

            for row in cur.fetchall():
                result = dict(row)
                screenshot_id = result["id"]

                # Deduplicate by screenshot (keep best match)
                if screenshot_id in seen_screenshots:
                    continue
                seen_screenshots.add(screenshot_id)

                # Convert L2 distance to similarity
                distance = result.pop("vec_distance", 0)
                result["text_similarity"] = max(0.0, min(1.0, 1.0 - (distance**2) / 2))

                results.append(result)
                if len(results) >= limit:
                    break

            return results

    def search_hybrid(
        self,
        query: str,
        image_embedding: list[float] | None = None,
        text_embedding: list[float] | None = None,
        mode: str = "auto",
        limit: int = 20,
        visibility: str = "visible_only",
        rrf_k: int = 60,
    ) -> list[dict]:
        """Hybrid search combining image and text search methods.

        Uses Reciprocal Rank Fusion (RRF) to combine results from:
        - CLIP image semantic search
        - FTS5 fuzzy text search
        - BGE text embedding search (small + large chunks)

        RRF formula: score(d) = Σ (1 / (k + rank(d, q)))
        Higher k = more emphasis on top results, lower k = more equal weighting

        Args:
            query: The search query string
            image_embedding: CLIP image embedding (768-dim) for image search
            text_embedding: BGE text embedding (384-dim) for text semantic search
            mode: Search mode - "auto", "image", "text_fuzzy", "text_semantic"
            limit: Maximum number of results
            visibility: One of "visible_only", "hidden_only", or "all"
            rrf_k: RRF constant (default 60, standard value)

        Returns:
            List of screenshots with combined RRF scores and match sources
        """
        # Collect results from each search method
        results_by_source: dict[str, list[tuple[int, float]]] = {}

        # Determine which methods to use based on mode
        use_image = mode in ("auto", "image") and image_embedding is not None
        use_fts = mode in ("auto", "text_fuzzy")
        use_text_semantic = mode in ("auto", "text_semantic") and text_embedding is not None

        # 1. CLIP Image Search
        if use_image and image_embedding is not None:
            try:
                image_results = self.search_similar(
                    query_embedding=image_embedding,
                    limit=limit * 2,  # Get more for RRF merge
                    visibility=visibility,
                )
                results_by_source["image"] = [(r["id"], r.get("similarity", 0)) for r in image_results]
            except Exception as e:
                print(f"Image search error: {e}")

        # 2. FTS5 Fuzzy Text Search
        if use_fts:
            try:
                fts_results = self.search_ocr_fts(
                    query=query,
                    limit=limit * 2,
                    visibility=visibility,
                )
                results_by_source["text_fts"] = [(r["id"], r.get("relevance_score", 0)) for r in fts_results]
            except Exception as e:
                print(f"FTS search error: {e}")

        # 3. BGE Text Semantic Search (small chunks)
        if use_text_semantic and text_embedding is not None:
            try:
                small_results = self.search_text_embeddings(
                    query_embedding=text_embedding,
                    chunk_size="small",
                    limit=limit * 2,
                    visibility=visibility,
                )
                results_by_source["text_semantic_small"] = [
                    (r["id"], r.get("text_similarity", 0)) for r in small_results
                ]
            except Exception as e:
                print(f"Text semantic (small) search error: {e}")

        # 4. BGE Text Semantic Search (large chunks)
        if use_text_semantic and text_embedding is not None:
            try:
                large_results = self.search_text_embeddings(
                    query_embedding=text_embedding,
                    chunk_size="large",
                    limit=limit * 2,
                    visibility=visibility,
                )
                results_by_source["text_semantic_large"] = [
                    (r["id"], r.get("text_similarity", 0)) for r in large_results
                ]
            except Exception as e:
                print(f"Text semantic (large) search error: {e}")

        # Apply RRF to combine results
        rrf_scores: dict[int, float] = {}
        match_sources: dict[int, list[str]] = {}

        for source, ranked_results in results_by_source.items():
            for rank, (screenshot_id, _score) in enumerate(ranked_results, start=1):
                # RRF contribution from this source
                rrf_contribution = 1.0 / (rrf_k + rank)
                rrf_scores[screenshot_id] = rrf_scores.get(screenshot_id, 0) + rrf_contribution

                # Track which sources matched this screenshot
                if screenshot_id not in match_sources:
                    match_sources[screenshot_id] = []
                match_sources[screenshot_id].append(source)

        # Sort by RRF score
        sorted_ids = sorted(rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True)[:limit]

        # Fetch full screenshot data
        results = []
        if sorted_ids:
            placeholders = ",".join("?" * len(sorted_ids))

            if visibility == "visible_only":
                vis_condition = "AND (is_hidden = 0 OR is_hidden IS NULL)"
            elif visibility == "hidden_only":
                vis_condition = "AND is_hidden = 1"
            else:
                vis_condition = ""

            with self.cursor() as cur:
                cur.execute(
                    f"""
                    SELECT s.*, o.full_text as ocr_text
                    FROM screenshots s
                    LEFT JOIN screenshot_ocr o ON o.screenshot_id = s.id
                    WHERE s.id IN ({placeholders})
                    {vis_condition}
                """,
                    sorted_ids,
                )

                # Build lookup for fetched data
                fetched = {row["id"]: dict(row) for row in cur.fetchall()}

            # Combine with scores, maintaining RRF order
            for screenshot_id in sorted_ids:
                if screenshot_id in fetched:
                    result = fetched[screenshot_id]
                    result["similarity"] = rrf_scores[screenshot_id]
                    result["match_sources"] = match_sources.get(screenshot_id, [])

                    # Create snippet if text search matched
                    if "text_fts" in result["match_sources"] or any(
                        s.startswith("text_semantic") for s in result["match_sources"]
                    ):
                        ocr_text = result.get("ocr_text", "")
                        if ocr_text:
                            result["ocr_snippet"] = self._create_snippet(ocr_text, query)

                    results.append(result)

        return results

    def _create_snippet(self, text: str, query: str, context_chars: int = 50) -> str:
        """Create a text snippet with query highlighted.

        Args:
            text: Full text to search in
            query: Query to highlight
            context_chars: Characters of context around match

        Returns:
            Snippet with **highlighted** query match
        """
        if not text or not query:
            return ""

        # Find best match position (case-insensitive)
        text_lower = text.lower()
        query_words = query.lower().split()

        # Find first occurrence of any query word
        best_pos = len(text)
        best_word = ""
        for word in query_words:
            pos = text_lower.find(word)
            if pos != -1 and pos < best_pos:
                best_pos = pos
                best_word = word

        if best_pos == len(text):
            # No match found, return start of text
            return text[: context_chars * 2] + "..." if len(text) > context_chars * 2 else text

        # Calculate snippet boundaries
        start = max(0, best_pos - context_chars)
        end = min(len(text), best_pos + len(best_word) + context_chars)

        # Build snippet
        snippet = ""
        if start > 0:
            snippet += "..."
        snippet += text[start:best_pos]
        snippet += f"**{text[best_pos : best_pos + len(best_word)]}**"
        snippet += text[best_pos + len(best_word) : end]
        if end < len(text):
            snippet += "..."

        return snippet

    def get_ocr_stats(self) -> dict:
        """Get OCR processing statistics"""
        with self.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM screenshots WHERE has_ocr = 1")
            with_ocr = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM screenshots WHERE has_ocr = 0")
            without_ocr = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM screenshot_ocr WHERE full_text != ''")
            with_text = cur.fetchone()[0]

            cur.execute("SELECT AVG(confidence) FROM screenshot_ocr WHERE confidence IS NOT NULL")
            avg_confidence = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM ocr_text_chunks")
            total_chunks = cur.fetchone()[0]

            return {
                "total_screenshots": with_ocr + without_ocr,
                "with_ocr": with_ocr,
                "without_ocr": without_ocr,
                "with_text": with_text,
                "avg_confidence": avg_confidence,
                "total_chunks": total_chunks,
            }

    def delete_ocr_data(self, screenshot_id: int) -> bool:
        """Delete OCR data for a screenshot (for reprocessing)"""
        with self.cursor() as cur:
            # Get OCR record ID
            cur.execute("SELECT id FROM screenshot_ocr WHERE screenshot_id = ?", (screenshot_id,))
            row = cur.fetchone()
            if not row:
                return False

            ocr_id = row[0]

            # Get chunk IDs for this OCR record
            cur.execute("SELECT id FROM ocr_text_chunks WHERE ocr_id = ?", (ocr_id,))
            chunk_ids = [r[0] for r in cur.fetchall()]

            # Delete text embeddings
            if chunk_ids:
                placeholders = ",".join("?" * len(chunk_ids))
                cur.execute(f"DELETE FROM ocr_text_embeddings WHERE chunk_id IN ({placeholders})", chunk_ids)

            # Delete chunks
            cur.execute("DELETE FROM ocr_text_chunks WHERE ocr_id = ?", (ocr_id,))

            # Delete OCR record (FTS will auto-sync via trigger)
            cur.execute("DELETE FROM screenshot_ocr WHERE id = ?", (ocr_id,))

            # Reset has_ocr flag
            cur.execute("UPDATE screenshots SET has_ocr = 0 WHERE id = ?", (screenshot_id,))

            return True

    def reset_all_ocr(self) -> int:
        """Reset all OCR data for reprocessing with new provider.

        Returns:
            Number of screenshots that will need reprocessing
        """
        with self.cursor() as cur:
            # Delete all text embeddings
            cur.execute("DELETE FROM ocr_text_embeddings")

            # Delete all chunks
            cur.execute("DELETE FROM ocr_text_chunks")

            # Delete all OCR records
            cur.execute("DELETE FROM screenshot_ocr")

            # Reset all has_ocr flags
            cur.execute("UPDATE screenshots SET has_ocr = 0")
            count = cur.rowcount

            return count

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
