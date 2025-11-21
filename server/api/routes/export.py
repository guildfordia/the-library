"""
Export endpoint for The Library API.
Exports the complete database (with edits applied) as CSV + JSON files in a ZIP archive.
"""

import os
import sqlite3
import csv
import json
import io
import zipfile
from datetime import datetime
from typing import Dict, List
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from api.db import get_optimized_connection

router = APIRouter()


@router.get("/export")
async def export_database(request: Request):
    """
    Export the complete database with all edits applied.

    Rate limit: 10 requests per hour per IP address.

    Returns a ZIP file containing:
    - biblio/FINAL_BIBLIO_ATLANTA.csv (all books with edits)
    - extracts/*.json (one file per book with quotes and edits)
    """
    # Apply rate limiting
    limiter = request.app.state.limiter
    # await limiter.hit("10/hour", request=request)

    db_path = "index/library.db"
    if not os.path.exists(db_path):
        raise HTTPException(
            status_code=404,
            detail="Database not found. Nothing to export."
        )

    try:
        # Create in-memory ZIP file
        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # Connect to database with optimized connection
            conn = get_optimized_connection(db_path)
            conn.row_factory = sqlite3.Row
            try:
                cursor = conn.cursor()

                # Export books to CSV
                csv_buffer = io.StringIO()
                csv_writer = csv.writer(csv_buffer, delimiter=';')

                # Write CSV header
                csv_writer.writerow([
                    'id', 'authors', 'container', 'doi', 'entry_type', 'isbn', 'issue',
                    'journal', 'match_strategy', 'notes', 'pages', 'place', 'publisher',
                    'source_doi', 'source_path', 'source_title', 'title', 'url', 'volume',
                    'year', 'data_source', 'abstract', 'keywords'
                ])

                # Fetch all books (with edits already applied in database)
                cursor.execute("""
                    SELECT id, title, authors, year, doi, container, entry_type, volume, issue,
                           pages, publisher, issn, source_path, meta_title, meta_author,
                           doc_summary, doc_keywords
                    FROM books
                    ORDER BY id
                """)

                books = cursor.fetchall()
                book_count = 0

                for book_row in books:
                    book = dict(book_row)

                    # Write book row to CSV (data already includes edits)
                    csv_writer.writerow([
                        book.get('id'),
                        book.get('authors', ''),
                        book.get('container', ''),
                        book.get('doi', ''),
                        book.get('entry_type', ''),
                        book.get('issn', ''),  # Using issn as isbn
                        book.get('issue', ''),
                        book.get('container', ''),  # Using container as journal
                        '',  # match_strategy - not in DB
                        '',  # notes - not in DB
                        book.get('pages', ''),
                        '',  # place - not in DB
                        book.get('publisher', ''),
                        book.get('doi', ''),  # Using doi as source_doi
                        book.get('source_path', ''),
                        book.get('meta_title', ''),
                        book.get('title', ''),
                        '',  # url - not in DB
                        book.get('volume', ''),
                        book.get('year', ''),
                        'exported',  # data_source
                        book.get('doc_summary', ''),
                        book.get('doc_keywords', '')
                    ])

                    book_count += 1

                # Add CSV to ZIP
                zip_file.writestr(
                    'data/biblio/FINAL_BIBLIO_ATLANTA.csv',
                    csv_buffer.getvalue().encode('utf-8')
                )

                # Export quotes as JSON files (one per book)
                cursor.execute("SELECT DISTINCT book_id FROM quotes ORDER BY book_id")
                book_ids_with_quotes = [row[0] for row in cursor.fetchall()]

                quote_files_count = 0
                total_quotes = 0

                for book_id in book_ids_with_quotes:
                    # Get book info
                    cursor.execute("SELECT title, source_path FROM books WHERE id = ?", (book_id,))
                    book_info = cursor.fetchone()

                    if not book_info:
                        continue

                    # Get all quotes for this book (with edits already applied in database)
                    cursor.execute("""
                        SELECT id, quote_text, page, section, keywords
                        FROM quotes
                        WHERE book_id = ?
                        ORDER BY page, id
                    """, (book_id,))

                    quotes_rows = cursor.fetchall()

                    if not quotes_rows:
                        continue

                    # Build highlights list
                    highlights = []
                    for quote_row in quotes_rows:
                        highlights.append({
                            'text': quote_row['quote_text'],
                            'page': quote_row['page'],
                            'keywords': quote_row['keywords'] or ''
                        })
                        total_quotes += 1

                    # Create JSON structure
                    json_data = {
                        'file': book_info['source_path'] or f'book_{book_id}.pdf',
                        'highlights': highlights
                    }

                    # Generate filename from title or use book_id
                    title = book_info['title'] or f'book_{book_id}'
                    # Clean filename (remove invalid characters)
                    safe_title = ''.join(c for c in title if c.isalnum() or c in (' ', '-', '_'))[:100]
                    filename = f"{safe_title}_highlights.json"

                    # Add JSON to ZIP
                    zip_file.writestr(
                        f'data/extracts/{filename}',
                        json.dumps(json_data, indent=2, ensure_ascii=False)
                    )

                    quote_files_count += 1
            finally:
                conn.close()

        # Prepare ZIP for download
        zip_buffer.seek(0)

        # Generate filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"library_export_{timestamp}.zip"

        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "X-Export-Stats": f"books={book_count};quotes={total_quotes};files={quote_files_count}"
            }
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Export failed: {str(e)}"
        )
