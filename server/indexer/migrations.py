"""
Database migrations for The Library.
Handles schema updates for edit workflow and conflict detection.
"""

import sqlite3
from datetime import datetime
from pathlib import Path


def create_edits_table(conn: sqlite3.Connection):
    """
    Create edits table for overlay approach.
    Stores user edits without modifying source CSV/JSON files.
    """
    conn.execute("""
    CREATE TABLE IF NOT EXISTS edits (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        entity_type TEXT NOT NULL CHECK(entity_type IN ('book', 'quote')),
        entity_id INTEGER NOT NULL,
        field_name TEXT NOT NULL,
        old_value TEXT,
        new_value TEXT,
        edited_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        edited_by TEXT,
        status TEXT DEFAULT 'active' CHECK(status IN ('active', 'reverted', 'merged')),
        UNIQUE(entity_type, entity_id, field_name, status)
    )
    """)

    # Index for fast lookups during search
    conn.execute("""
    CREATE INDEX IF NOT EXISTS idx_edits_lookup
    ON edits(entity_type, entity_id, status)
    """)

    conn.commit()
    print("✓ Created edits table")


def create_conflicts_table(conn: sqlite3.Connection):
    """
    Create conflicts table for tracking CSV/JSON vs database mismatches.
    When indexer detects differences, it records them here for admin resolution.
    """
    conn.execute("""
    CREATE TABLE IF NOT EXISTS conflicts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        entity_type TEXT NOT NULL CHECK(entity_type IN ('book', 'quote')),
        entity_id INTEGER NOT NULL,
        field_name TEXT NOT NULL,
        db_value TEXT,
        source_value TEXT,
        source_file TEXT,
        detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        resolved_at TIMESTAMP,
        resolution TEXT CHECK(resolution IN (NULL, 'keep_db', 'use_source', 'merge')),
        resolved_by TEXT,
        notes TEXT
    )
    """)

    # Index for conflict resolution UI
    conn.execute("""
    CREATE INDEX IF NOT EXISTS idx_conflicts_unresolved
    ON conflicts(resolved_at) WHERE resolved_at IS NULL
    """)

    conn.commit()
    print("✓ Created conflicts table")


def add_metadata_columns(conn: sqlite3.Connection):
    """
    Add metadata tracking columns to books and quotes tables.
    Tracks when records were last modified in DB vs source files.
    """
    # Check if columns already exist
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(books)")
    books_columns = [row[1] for row in cursor.fetchall()]

    if 'last_modified' not in books_columns:
        conn.execute("""
        ALTER TABLE books ADD COLUMN last_modified TIMESTAMP
        """)
        # Set default value for existing rows
        conn.execute("""
        UPDATE books SET last_modified = CURRENT_TIMESTAMP WHERE last_modified IS NULL
        """)
        print("✓ Added last_modified to books table")

    if 'source_modified' not in books_columns:
        conn.execute("""
        ALTER TABLE books ADD COLUMN source_modified TIMESTAMP
        """)
        print("✓ Added source_modified to books table")

    # Same for quotes
    cursor.execute("PRAGMA table_info(quotes)")
    quotes_columns = [row[1] for row in cursor.fetchall()]

    if 'last_modified' not in quotes_columns:
        conn.execute("""
        ALTER TABLE quotes ADD COLUMN last_modified TIMESTAMP
        """)
        # Set default value for existing rows
        conn.execute("""
        UPDATE quotes SET last_modified = CURRENT_TIMESTAMP WHERE last_modified IS NULL
        """)
        print("✓ Added last_modified to quotes table")

    if 'source_modified' not in quotes_columns:
        conn.execute("""
        ALTER TABLE quotes ADD COLUMN source_modified TIMESTAMP
        """)
        print("✓ Added source_modified to quotes table")

    conn.commit()


def migrate_database(db_path: str):
    """
    Run all migrations on the database.
    Safe to run multiple times (idempotent).
    """
    print(f"Running migrations on {db_path}...")

    conn = sqlite3.connect(db_path)

    # Enable WAL mode for better concurrency
    conn.execute("PRAGMA journal_mode = WAL")

    try:
        create_edits_table(conn)
        create_conflicts_table(conn)
        add_metadata_columns(conn)

        print("\n✅ All migrations completed successfully")

        # Show stats
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM edits")
        edits_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM conflicts WHERE resolved_at IS NULL")
        unresolved_conflicts = cursor.fetchone()[0]

        print(f"\nDatabase status:")
        print(f"  Active edits: {edits_count}")
        print(f"  Unresolved conflicts: {unresolved_conflicts}")

    except Exception as e:
        print(f"❌ Migration failed: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run database migrations")
    parser.add_argument("--db-path", default="index/library.db",
                       help="Path to SQLite database")
    args = parser.parse_args()

    # Ensure database exists
    if not Path(args.db_path).exists():
        print(f"❌ Database not found at {args.db_path}")
        print("Run indexer first: python indexer/build_index.py")
        exit(1)

    migrate_database(args.db_path)
