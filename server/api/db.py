"""
Database connection utilities for The Library.
Provides optimized SQLite connections with proper settings.
"""

import sqlite3
from contextlib import contextmanager
from typing import Generator


def get_optimized_connection(db_path: str = "index/library.db") -> sqlite3.Connection:
    """
    Create an optimized SQLite connection.

    SQLite doesn't support traditional connection pooling like PostgreSQL,
    but we can optimize individual connections with proper PRAGMA settings.
    """
    conn = sqlite3.connect(db_path, check_same_thread=False)

    # Enable WAL mode for better concurrency (multiple readers, one writer)
    conn.execute("PRAGMA journal_mode = WAL")

    # NORMAL synchronous mode is safe with WAL and much faster
    conn.execute("PRAGMA synchronous = NORMAL")

    # Increase cache size for better performance (10MB)
    conn.execute("PRAGMA cache_size = 10000")

    # Keep temp tables in memory
    conn.execute("PRAGMA temp_store = memory")

    # Enable memory-mapped I/O for reads (256MB)
    conn.execute("PRAGMA mmap_size = 268435456")

    return conn


@contextmanager
def get_db(db_path: str = "index/library.db") -> Generator[sqlite3.Connection, None, None]:
    """
    Context manager for database connections.

    Usage:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT ...")
    """
    conn = get_optimized_connection(db_path)
    try:
        yield conn
    finally:
        conn.close()
