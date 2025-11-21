"""
Add performance indexes to the database.
Run this after building the initial index.
"""

import sqlite3
import os


def add_performance_indexes(db_path="index/library.db"):
    """Add indexes to improve query performance."""

    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return False

    print(f"Adding performance indexes to {db_path}...")

    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()

        # Check existing indexes
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
        existing_indexes = {row[0] for row in cursor.fetchall()}

        indexes_to_create = [
            # Most important: quotes.book_id for JOIN performance
            ("idx_quotes_book_id", "CREATE INDEX IF NOT EXISTS idx_quotes_book_id ON quotes(book_id)"),

            # Useful for filtering/sorting
            ("idx_books_year", "CREATE INDEX IF NOT EXISTS idx_books_year ON books(year)"),
            ("idx_books_entry_type", "CREATE INDEX IF NOT EXISTS idx_books_entry_type ON books(entry_type)"),

            # For quote lookups
            ("idx_quotes_page", "CREATE INDEX IF NOT EXISTS idx_quotes_page ON quotes(page)"),
        ]

        created_count = 0
        for index_name, create_sql in indexes_to_create:
            if index_name in existing_indexes:
                print(f"  ✓ Index {index_name} already exists")
            else:
                print(f"  + Creating index {index_name}...")
                cursor.execute(create_sql)
                created_count += 1

        conn.commit()

        print(f"\n✅ Created {created_count} new indexes")
        print(f"📊 Total indexes: {len(existing_indexes) + created_count}")

        # Analyze tables to update statistics
        print("\nAnalyzing tables to update query planner statistics...")
        cursor.execute("ANALYZE")
        conn.commit()
        print("✅ Analysis complete")

        return True


if __name__ == "__main__":
    success = add_performance_indexes()
    exit(0 if success else 1)
