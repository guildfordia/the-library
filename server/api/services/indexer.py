"""Indexing service for rebuilding the search database from CSV and JSON files."""

import json
import logging
import os
import sqlite3
import time
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

import pandas as pd

logger = logging.getLogger(__name__)


class IndexerService:
    """Service for rebuilding the search index from source files."""

    def __init__(self, db_path: str = "index/library.db"):
        self.db_path = db_path
        self.ensure_index_dir()

    def ensure_index_dir(self):
        """Ensure the index directory exists."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

    def reindex_from_files(self, csv_path: Optional[str] = None,
                          json_folder: Optional[str] = None) -> Dict[str, Any]:
        """
        Rebuild the search index from CSV (books) and JSON folder (quotes).

        Args:
            csv_path: Path to CSV file with book metadata
            json_folder: Path to folder containing JSON files with quotes

        Returns:
            Dict with status, counts, and timing info
        """
        start_time = time.time()

        # Validate inputs
        if not csv_path and not json_folder:
            raise ValueError("At least one of csv_path or json_folder must be provided")

        if csv_path and not os.path.exists(csv_path):
            raise FileNotFoundError(f"CSV file not found: {csv_path}")

        if json_folder and not os.path.exists(json_folder):
            raise FileNotFoundError(f"JSON folder not found: {json_folder}")

        logger.info("Starting reindexing process...")

        try:
            with sqlite3.connect(self.db_path) as conn:
                # Create schema
                self._create_schema(conn)

                books_count = 0
                quotes_count = 0

                # Process CSV file (books)
                if csv_path:
                    books_count = self._process_csv(conn, csv_path)
                    logger.info(f"Processed {books_count} books from CSV")

                # Process JSON folder (quotes)
                if json_folder:
                    quotes_count = self._process_json_folder(conn, json_folder)
                    logger.info(f"Processed {quotes_count} quotes from JSON files")

                # Rebuild FTS5 index
                self._rebuild_fts_index(conn)
                logger.info("Rebuilt FTS5 search index")

                elapsed_time = time.time() - start_time

                result = {
                    "status": "success",
                    "books_processed": books_count,
                    "quotes_processed": quotes_count,
                    "elapsed_seconds": round(elapsed_time, 2),
                    "database_path": self.db_path
                }

                logger.info(f"Reindexing completed in {elapsed_time:.2f}s")
                return result

        except Exception as e:
            logger.error(f"Reindexing failed: {str(e)}")
            raise

    def _create_schema(self, conn: sqlite3.Connection):
        """Create database schema, dropping existing tables if they exist."""
        cursor = conn.cursor()

        # Drop existing tables
        cursor.execute("DROP TABLE IF EXISTS quotes_fts")
        cursor.execute("DROP TABLE IF EXISTS quotes")
        cursor.execute("DROP TABLE IF EXISTS books")

        # Create books table
        cursor.execute("""
            CREATE TABLE books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
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
                file_path TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create quotes table
        cursor.execute("""
            CREATE TABLE quotes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                book_id INTEGER,
                quote_text TEXT NOT NULL,
                page INTEGER,
                section TEXT,
                keywords TEXT,
                source_file TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (book_id) REFERENCES books (id)
            )
        """)

        # Create FTS5 virtual table for quotes
        cursor.execute("""
            CREATE VIRTUAL TABLE quotes_fts USING fts5(
                quote_text,
                keywords,
                content='quotes',
                content_rowid='id'
            )
        """)

        # Create indexes for performance
        cursor.execute("CREATE INDEX idx_quotes_book_id ON quotes(book_id)")
        cursor.execute("CREATE INDEX idx_books_title ON books(title)")
        cursor.execute("CREATE INDEX idx_books_authors ON books(authors)")

        conn.commit()
        logger.info("Database schema created successfully")

    def _process_csv(self, conn: sqlite3.Connection, csv_path: str) -> int:
        """Process CSV file and insert books into database."""
        try:
            df = pd.read_csv(csv_path)
            logger.info(f"Loaded CSV with {len(df)} rows")

            cursor = conn.cursor()
            books_inserted = 0

            for _, row in df.iterrows():
                try:
                    # Map CSV columns to database fields
                    book_data = {
                        'title': self._safe_get(row, 'title'),
                        'authors': self._safe_get(row, 'authors'),
                        'year': self._safe_get_int(row, 'year'),
                        'publisher': self._safe_get(row, 'publisher'),
                        'journal': self._safe_get(row, 'journal'),
                        'doi': self._safe_get(row, 'doi'),
                        'isbn': self._safe_get(row, 'isbn'),
                        'themes': self._safe_get(row, 'themes'),
                        'keywords': self._safe_get(row, 'keywords'),
                        'summary': self._safe_get(row, 'summary'),
                        'iso690': self._safe_get(row, 'iso690'),
                        'source_file': os.path.basename(csv_path),
                        'file_path': csv_path
                    }

                    cursor.execute("""
                        INSERT INTO books (
                            title, authors, year, publisher, journal, doi, isbn,
                            themes, keywords, summary, iso690, source_file, file_path
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, tuple(book_data.values()))

                    books_inserted += 1

                except Exception as e:
                    logger.warning(f"Failed to insert book row {books_inserted}: {str(e)}")
                    continue

            conn.commit()
            return books_inserted

        except Exception as e:
            logger.error(f"Failed to process CSV file: {str(e)}")
            raise

    def _process_json_folder(self, conn: sqlite3.Connection, json_folder: str) -> int:
        """Process JSON folder and insert quotes into database."""
        json_files = list(Path(json_folder).glob("*.json"))
        logger.info(f"Found {len(json_files)} JSON files")

        cursor = conn.cursor()
        quotes_inserted = 0

        for json_file in json_files:
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # Get or create book for this file
                book_id = self._get_or_create_book_for_json(conn, json_file, data)

                # Process quotes from JSON
                quotes = data.get('quotes', [])
                if isinstance(quotes, dict):
                    quotes = [quotes]

                for quote_data in quotes:
                    try:
                        cursor.execute("""
                            INSERT INTO quotes (
                                book_id, quote_text, page, section, keywords, source_file
                            ) VALUES (?, ?, ?, ?, ?, ?)
                        """, (
                            book_id,
                            quote_data.get('text', ''),
                            self._safe_get_int_from_dict(quote_data, 'page'),
                            quote_data.get('section'),
                            quote_data.get('keywords'),
                            json_file.name
                        ))
                        quotes_inserted += 1

                    except Exception as e:
                        logger.warning(f"Failed to insert quote from {json_file}: {str(e)}")
                        continue

            except Exception as e:
                logger.warning(f"Failed to process JSON file {json_file}: {str(e)}")
                continue

        conn.commit()
        return quotes_inserted

    def _get_or_create_book_for_json(self, conn: sqlite3.Connection,
                                   json_file: Path, data: dict) -> int:
        """Get or create a book record for a JSON file."""
        cursor = conn.cursor()

        # Extract book metadata from JSON
        metadata = data.get('metadata', {})
        title = metadata.get('title', json_file.stem)

        # Check if book already exists
        cursor.execute("SELECT id FROM books WHERE title = ? AND source_file = ?",
                      (title, json_file.name))
        result = cursor.fetchone()

        if result:
            return result[0]

        # Create new book record
        cursor.execute("""
            INSERT INTO books (
                title, authors, year, themes, keywords, source_file, file_path
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            title,
            metadata.get('authors'),
            self._safe_get_int_from_dict(metadata, 'year'),
            metadata.get('themes'),
            metadata.get('keywords'),
            json_file.name,
            str(json_file)
        ))

        return cursor.lastrowid

    def _rebuild_fts_index(self, conn: sqlite3.Connection):
        """Rebuild the FTS5 search index."""
        cursor = conn.cursor()

        # Populate FTS5 table with quote data
        cursor.execute("""
            INSERT INTO quotes_fts(rowid, quote_text, keywords)
            SELECT id, quote_text, COALESCE(keywords, '')
            FROM quotes
        """)

        conn.commit()

    def _safe_get(self, row, column: str) -> Optional[str]:
        """Safely get string value from pandas row."""
        try:
            value = row.get(column)
            if pd.isna(value):
                return None
            return str(value).strip() if value else None
        except:
            return None

    def _safe_get_int(self, row, column: str) -> Optional[int]:
        """Safely get integer value from pandas row."""
        try:
            value = row.get(column)
            if pd.isna(value):
                return None
            return int(value) if value else None
        except:
            return None

    def _safe_get_int_from_dict(self, data: dict, key: str) -> Optional[int]:
        """Safely get integer value from dictionary."""
        try:
            value = data.get(key)
            return int(value) if value is not None else None
        except:
            return None


# Global indexer instance
indexer = IndexerService()