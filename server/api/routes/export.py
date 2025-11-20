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
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from api.services.editor import editor

router = APIRouter()


@router.get("/export")
async def export_database():
    """
    Export the complete database with all edits applied.

    Returns a ZIP file containing:
    - biblio/FINAL_BIBLIO_ATLANTA.csv (all books with edits)
    - extracts/*.json (one file per book with quotes and edits)
    """

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
            # Connect to database
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
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

            # Fetch all books
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
                book_id = book_row['id']
                book_dict = dict(book_row)

                # Apply edits to book
                book_with_edits = editor.apply_edits('book', book_id, book_dict)

                # Write book row to CSV
                csv_writer.writerow([
                    book_id,
                    book_with_edits.get('authors', ''),
                    book_with_edits.get('container', ''),
                    book_with_edits.get('doi', ''),
                    book_with_edits.get('entry_type', ''),
                    book_with_edits.get('issn', ''),  # Using issn as isbn
                    book_with_edits.get('issue', ''),
                    book_with_edits.get('container', ''),  # Using container as journal
                    '',  # match_strategy - not in DB
                    '',  # notes - not in DB
                    book_with_edits.get('pages', ''),
                    '',  # place - not in DB
                    book_with_edits.get('publisher', ''),
                    book_with_edits.get('doi', ''),  # Using doi as source_doi
                    book_with_edits.get('source_path', ''),
                    book_with_edits.get('meta_title', ''),
                    book_with_edits.get('title', ''),
                    '',  # url - not in DB
                    book_with_edits.get('volume', ''),
                    book_with_edits.get('year', ''),
                    'exported',  # data_source
                    book_with_edits.get('doc_summary', ''),
                    book_with_edits.get('doc_keywords', '')
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

                # Get all quotes for this book
                cursor.execute("""
                    SELECT id, quote_text, page, section, keywords
                    FROM quotes
                    WHERE book_id = ?
                    ORDER BY page, id
                """, (book_id,))

                quotes_rows = cursor.fetchall()

                if not quotes_rows:
                    continue

                # Apply edits to each quote
                highlights = []
                for quote_row in quotes_rows:
                    quote_dict = dict(quote_row)
                    quote_with_edits = editor.apply_edits('quote', quote_row['id'], quote_dict)

                    highlights.append({
                        'text': quote_with_edits['quote_text'],
                        'page': quote_with_edits.get('page'),
                        'keywords': quote_with_edits.get('keywords', '')
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
