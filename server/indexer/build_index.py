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

    # Books table - Updated to match actual CSV structure from bibliography.final.with_annots.flat.csv
    conn.execute("""
    CREATE TABLE IF NOT EXISTS books (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        authors TEXT,
        year INTEGER,
        doi TEXT,
        container TEXT,
        volume TEXT,
        issue TEXT,
        pages TEXT,
        publisher TEXT,
        issn TEXT,
        source_path TEXT,
        meta_title TEXT,
        meta_author TEXT,
        web_url_guess TEXT,
        domain_guess TEXT,
        doc_summary TEXT,
        doc_keywords TEXT,
        highlight_count INTEGER
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
    Updated to use actual CSV structure from bibliography.final.with_annots.flat.csv
    Returns mapping of source_path -> book_id for linking with extracts
    """

    if not os.path.exists(csv_path):
        print(f"Warning: Bibliography CSV not found at {csv_path}")
        return {}

    book_mapping = {}

    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)

        for row in reader:
            # Skip empty rows
            if not row.get('title') and not row.get('source_path'):
                continue

            # Extract relevant fields using actual CSV column names
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO books (title, authors, year, doi, container, volume, issue, pages,
                             publisher, issn, source_path, meta_title, meta_author,
                             web_url_guess, domain_guess, doc_summary, doc_keywords, highlight_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                row.get('title', ''),
                row.get('authors', ''),
                int(float(row['year'])) if row.get('year') and str(row['year']).replace('.', '').replace('-', '').isdigit() else None,
                row.get('doi', ''),
                row.get('container', ''),
                row.get('volume', ''),
                row.get('issue', ''),
                row.get('pages', ''),
                row.get('publisher', ''),
                row.get('issn', ''),
                row.get('source_path', ''),
                row.get('meta_title', ''),
                row.get('meta_author', ''),
                row.get('web_url_guess', ''),
                row.get('domain_guess', ''),
                row.get('doc_summary', ''),
                row.get('doc_keywords', ''),
                int(row.get('highlight_count', 0)) if row.get('highlight_count') and str(row.get('highlight_count')).isdigit() else 0
            ))

            book_id = cursor.lastrowid

            # Create mapping for linking with extracts using source_path
            source_path = row.get('source_path', '')
            if source_path:
                # Extract filename from path for matching
                filename = Path(source_path).stem
                book_mapping[filename] = book_id

                # Also map by full path
                book_mapping[source_path] = book_id

            # Also map by title for fallback matching
            title = row.get('title', '').strip()
            if title:
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

            # Extract book identifier from filename or path in JSON
            json_stem = extract_filename_from_json(json_file.name)
            json_source_path = data.get('file', '')

            # Try to find matching book using multiple strategies
            book_id = None

            # Strategy 1: Match by source_path from JSON file content to CSV source_path
            if json_source_path and json_source_path in book_mapping:
                book_id = book_mapping[json_source_path]

            # Strategy 2: Match by filename extracted from JSON source_path to CSV source_path filename
            elif json_source_path:
                json_filename = Path(json_source_path).stem
                if json_filename in book_mapping:
                    book_id = book_mapping[json_filename]

            # Strategy 3: Direct filename match from JSON filename
            elif json_stem in book_mapping:
                book_id = book_mapping[json_stem]

            # Strategy 4: Fuzzy matching on available book titles and paths
            if not book_id:
                for book_key, mapped_id in book_mapping.items():
                    # Try matching against various parts of the paths and titles
                    if (book_key.lower() in json_stem.lower() or
                        json_stem.lower() in book_key.lower() or
                        (json_source_path and book_key.lower() in json_source_path.lower())):
                        book_id = mapped_id
                        break

            if not book_id:
                # Create placeholder book entry for books not found in CSV
                cursor = conn.cursor()

                # Extract title from the file path in JSON if available
                source_path = data.get('file', json_stem)
                title = Path(source_path).stem if source_path else json_stem

                cursor.execute("""
                INSERT INTO books (title, source_path)
                VALUES (?, ?)
                """, (title, source_path))

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

            # Load data - Use the actual CSV file that exists
            biblio_path = os.path.join(args.data_dir, "biblio", "bibliography.final.with_annots.flat.csv")
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