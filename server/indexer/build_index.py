"""
SQLite + FTS5 index builder for The Library.
Ingests CSV bibliography and JSON highlight files into searchable database.
"""

import sqlite3
import json
import csv
import os
import sys
from pathlib import Path
import argparse
from typing import Dict, List, Optional
import re

def setup_database(db_path: str) -> sqlite3.Connection:
    """Create database with optimized settings for Pi 4"""
    conn = sqlite3.connect(db_path)

    # Pi 4 optimizations as per CLAUDE.md
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    conn.execute("PRAGMA cache_size = 10000")
    conn.execute("PRAGMA temp_store = memory")

    return conn

def create_tables(conn: sqlite3.Connection):
    """Create books and quotes tables with FTS5 virtual table"""

    # Books table - NOTE: Using CSV structure from data/biblio/final_biblio_EXCELLENCE_FINALE.csv
    conn.execute("""
    CREATE TABLE IF NOT EXISTS books (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        authors TEXT,
        year INTEGER,
        publisher TEXT,
        journal TEXT,
        doi TEXT,
        isbn TEXT,
        themes TEXT,
        keywords TEXT,
        summary TEXT,
        iso690 TEXT,
        source_file TEXT,
        file_path TEXT
    )
    """)

    # Quotes table - NOTE: Using JSON structure from data/extracts/*.json files
    conn.execute("""
    CREATE TABLE IF NOT EXISTS quotes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        book_id INTEGER,
        quote_text TEXT NOT NULL,
        page INTEGER,
        section TEXT,
        keywords TEXT,
        source_file TEXT,
        FOREIGN KEY (book_id) REFERENCES books (id)
    )
    """)

    # FTS5 virtual table for full-text search
    conn.execute("""
    CREATE VIRTUAL TABLE IF NOT EXISTS quotes_fts USING fts5(
        quote_text,
        keywords,
        content='quotes',
        content_rowid='id'
    )
    """)

    conn.commit()

def load_bibliography(conn: sqlite3.Connection, csv_path: str) -> Dict[str, int]:
    """
    Load books from CSV file.
    NOTE: CSV structure based on actual file at data/biblio/final_biblio_EXCELLENCE_FINALE.csv
    Returns mapping of source_file -> book_id for linking with extracts
    """

    if not os.path.exists(csv_path):
        print(f"Warning: Bibliography CSV not found at {csv_path}")
        return {}

    book_mapping = {}

    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)

        for row in reader:
            # Extract relevant fields from the extensive CSV structure
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO books (title, authors, year, publisher, journal, doi, isbn,
                             themes, keywords, summary, iso690, source_file, file_path)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                row.get('final_verified_title') or row.get('title', ''),
                row.get('final_verified_authors') or row.get('author_final', ''),
                int(float(row['year'])) if row.get('year') and str(row['year']).replace('.', '').replace('-', '').isdigit() else None,
                row.get('final_verified_publisher') or row.get('publisher', ''),
                row.get('journal', ''),
                row.get('DOI') or row.get('doi', ''),
                row.get('isbn_13') or row.get('isbn', ''),
                row.get('theme', ''),
                row.get('keywords', ''),
                row.get('summary', ''),
                row.get('biblio_iso690_finale') or row.get('biblio_fr_iso690', ''),
                row.get('source_file', ''),
                row.get('file_path', '')
            ))

            book_id = cursor.lastrowid

            # Map by filename for linking with extracts
            # Use title as fallback since file_path may not exist in CSV
            if row.get('file_path'):
                filename = Path(row['file_path']).stem
                book_mapping[filename] = book_id
            elif row.get('title'):
                # Use title as mapping key for fuzzy matching
                title = row['title'].strip()
                book_mapping[title] = book_id

    conn.commit()
    print(f"Loaded {len(book_mapping)} books from bibliography")
    return book_mapping

def extract_filename_from_json(json_filename: str) -> str:
    """
    Extract base filename from JSON highlights file.
    NOTE: JSON files are named like "Book Title_highlights.json"
    """
    return json_filename.replace('_highlights.json', '').replace('_highlights', '')

def load_quotes(conn: sqlite3.Connection, extracts_dir: str, book_mapping: Dict[str, int]):
    """
    Load quotes from JSON highlight files.
    NOTE: JSON structure based on files in data/extracts/ with format:
    {"file": "/path/to/file.pdf", "highlights": [{"page": N, "text": "...", "keywords": "..."}]}
    """

    if not os.path.exists(extracts_dir):
        print(f"Warning: Extracts directory not found at {extracts_dir}")
        return

    quote_count = 0
    unknown_books = set()

    for json_file in Path(extracts_dir).glob("*_highlights.json"):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Extract book identifier from filename or path
            json_stem = extract_filename_from_json(json_file.name)

            # Try to find matching book
            book_id = None

            # First try direct filename match
            if json_stem in book_mapping:
                book_id = book_mapping[json_stem]
            else:
                # Try fuzzy matching on available book titles
                # This is a fallback since biblio->extracts mapping isn't implemented yet
                for book_key, mapped_id in book_mapping.items():
                    if book_key.lower() in json_stem.lower() or json_stem.lower() in book_key.lower():
                        book_id = mapped_id
                        break

            if not book_id:
                # Create placeholder book entry for now
                cursor = conn.cursor()

                # Extract title from the file path in JSON if available
                source_path = data.get('file', json_stem)
                title = Path(source_path).stem if source_path else json_stem

                cursor.execute("""
                INSERT INTO books (title, source_file, file_path)
                VALUES (?, ?, ?)
                """, (title, str(json_file), source_path))

                book_id = cursor.lastrowid
                unknown_books.add(json_stem)

            # Load highlights/quotes
            highlights = data.get('highlights', [])
            for highlight in highlights:
                quote_text = highlight.get('text', '').strip()
                if quote_text:  # Skip empty quotes
                    page = highlight.get('page')
                    keywords = highlight.get('keywords', '')

                    cursor = conn.cursor()
                    cursor.execute("""
                    INSERT INTO quotes (book_id, quote_text, page, keywords, source_file)
                    VALUES (?, ?, ?, ?, ?)
                    """, (book_id, quote_text, page, keywords, str(json_file)))

                    quote_count += 1

        except Exception as e:
            print(f"Error processing {json_file}: {e}")
            continue

    conn.commit()
    print(f"Loaded {quote_count} quotes from {len(list(Path(extracts_dir).glob('*_highlights.json')))} files")
    if unknown_books:
        print(f"Warning: {len(unknown_books)} files had no bibliography match and were created as placeholder books")

def rebuild_fts_index(conn: sqlite3.Connection):
    """Rebuild FTS5 virtual table from quotes table"""

    try:
        # Clear existing FTS data
        conn.execute("DELETE FROM quotes_fts")
    except sqlite3.DatabaseError:
        # If FTS table is corrupted, recreate it
        conn.execute("DROP TABLE IF EXISTS quotes_fts")
        conn.execute("""
        CREATE VIRTUAL TABLE quotes_fts USING fts5(
            quote_text,
            keywords,
            content='quotes',
            content_rowid='id'
        )
        """)

    # Rebuild from quotes table
    conn.execute("""
    INSERT INTO quotes_fts(rowid, quote_text, keywords)
    SELECT id, quote_text, COALESCE(keywords, '') FROM quotes
    """)

    conn.commit()
    print("Rebuilt FTS5 index")

def main():
    parser = argparse.ArgumentParser(description="Build SQLite + FTS5 index for The Library")
    parser.add_argument("--fts-only", action="store_true",
                       help="Only rebuild FTS index (faster)")
    parser.add_argument("--db-path", default="index/library.db",
                       help="SQLite database path")

    # Auto-detect data directory - works in both development and Docker container
    default_data_dir = None
    if os.path.exists("/app/data"):  # Docker container path
        default_data_dir = "/app/data"
    elif os.path.exists("../data"):  # Local development path
        default_data_dir = "../data"
    elif os.path.exists("data"):  # Alternative local path
        default_data_dir = "data"
    else:
        default_data_dir = "../data"  # Fallback

    parser.add_argument("--data-dir", default=default_data_dir,
                       help="Data directory containing biblio/ and extracts/")

    args = parser.parse_args()

    # Ensure index directory exists
    os.makedirs(Path(args.db_path).parent, exist_ok=True)

    conn = setup_database(args.db_path)

    try:
        if args.fts_only:
            print("Rebuilding FTS index only...")
            rebuild_fts_index(conn)
        else:
            print("Building complete index...")

            # Drop and recreate tables for fresh start
            conn.execute("DROP TABLE IF EXISTS quotes_fts")
            conn.execute("DROP TABLE IF EXISTS quotes")
            conn.execute("DROP TABLE IF EXISTS books")

            create_tables(conn)

            # Load data
            biblio_path = os.path.join(args.data_dir, "biblio", "bibliographie_finale_these_FINAL_translated.csv")
            extracts_dir = os.path.join(args.data_dir, "extracts")

            book_mapping = load_bibliography(conn, biblio_path)
            load_quotes(conn, extracts_dir, book_mapping)
            rebuild_fts_index(conn)

        # Final stats
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM books")
        book_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM quotes")
        quote_count = cursor.fetchone()[0]

        print(f"\nIndex build complete:")
        print(f"  Books: {book_count}")
        print(f"  Quotes: {quote_count}")
        print(f"  Database: {args.db_path}")

    finally:
        conn.close()

if __name__ == "__main__":
    main()