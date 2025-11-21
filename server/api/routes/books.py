"""
Books endpoint for The Library API.
Handles book-specific operations including fetching quotes.
"""

from fastapi import APIRouter, HTTPException, Query, Path
from pydantic import BaseModel
from typing import List, Optional
import os

from api.services.scorer import scorer
from api.services.editor import editor
from api.db import get_optimized_connection

router = APIRouter()

class Quote(BaseModel):
    id: int
    page: Optional[int]
    section: Optional[str]
    quote_text: str
    keywords: Optional[str]

class BookQuotesResponse(BaseModel):
    book_id: int
    relevant: bool
    offset: int
    quotes: List[Quote]
    has_more: bool
    total_count: int

@router.get("/{book_id}/quotes", response_model=BookQuotesResponse)
async def get_book_quotes(
    book_id: int = Path(..., description="Book ID"),
    relevant: bool = Query(False, description="Filter quotes by relevance to query"),
    q: str = Query("", description="Search query for relevant filtering"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(10, ge=1, le=50, description="Number of quotes per page")
):
    """
    Get quotes for a specific book.

    - **relevant=true**: Only return quotes matching the search query
    - **relevant=false**: Return all quotes for the book
    """

    # Check if database exists
    db_path = "index/library.db"
    if not os.path.exists(db_path):
        raise HTTPException(status_code=503, detail="Search index not found. Please run the indexer first.")

    try:
        conn = get_optimized_connection(db_path)
        conn.row_factory = __import__('sqlite3').Row
        try:
            # Base query to get quotes for this book
            if relevant and q.strip():
                # Get relevant quotes using FTS search
                sql = """
                SELECT
                    q.id, q.quote_text, q.page, q.section, q.keywords,
                    fts.rank as bm25_score
                FROM quotes_fts fts
                JOIN quotes q ON q.id = fts.rowid
                WHERE q.book_id = ? AND quotes_fts MATCH ?
                ORDER BY fts.rank
                """
                cursor = conn.cursor()
                cursor.execute(sql, (book_id, q.strip()))
            else:
                # Get all quotes for this book
                sql = """
                SELECT id, quote_text, page, section, keywords
                FROM quotes
                WHERE book_id = ?
                ORDER BY page, id
                """
                cursor = conn.cursor()
                cursor.execute(sql, (book_id,))

            all_quotes = cursor.fetchall()
            total_count = len(all_quotes)

            # Apply pagination
            paginated_quotes = all_quotes[offset:offset + limit]
            has_more = (offset + limit) < total_count

            # Format response
            quotes = []
            for row in paginated_quotes:
                # Convert Row to dict to use .get()
                row_dict = dict(row)
                quotes.append(Quote(
                    id=row_dict['id'],
                    page=row_dict.get('page'),
                    section=row_dict.get('section'),
                    quote_text=row_dict['quote_text'],
                    keywords=row_dict.get('keywords')
                ))

            return BookQuotesResponse(
                book_id=book_id,
                relevant=relevant,
                offset=offset,
                quotes=quotes,
                has_more=has_more,
                total_count=total_count
            )
        finally:
            conn.close()

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching quotes: {str(e)}")

@router.get("/{book_id}/citation")
async def get_book_citation(
    book_id: int = Path(..., description="Book ID")
):
    """
    Get formatted citation for a book.
    Returns plain text for download.
    """

    db_path = "index/library.db"
    if not os.path.exists(db_path):
        raise HTTPException(status_code=503, detail="Search index not found.")

    try:
        conn = get_optimized_connection(db_path)
        conn.row_factory = __import__('sqlite3').Row
        try:
            cursor = conn.cursor()
            cursor.execute("""
            SELECT title, authors, year, publisher, container, doi, issn, source_path
            FROM books WHERE id = ?
            """, (book_id,))

            book_row = cursor.fetchone()

            if not book_row:
                raise HTTPException(status_code=404, detail="Book not found")

            book = dict(book_row)
        finally:
            conn.close()

        # Generate basic citation
        parts = []
        if book.get('authors'):
            parts.append(book['authors'])
        if book.get('title'):
            parts.append(f'"{book["title"]}"')
        if book.get('container'):
            parts.append(f"<i>{book['container']}</i>")
        elif book.get('publisher'):
            parts.append(book['publisher'])
        if book.get('year'):
            parts.append(str(book['year']))
        if book.get('doi'):
            parts.append(f"DOI: {book['doi']}")

        citation = ". ".join(parts) + "." if parts else "Citation unavailable"

        return {"citation": citation}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching citation: {str(e)}")