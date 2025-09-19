"""
Books endpoint for The Library API.
Handles book-specific operations including fetching quotes.
"""

from fastapi import APIRouter, HTTPException, Query, Path
from pydantic import BaseModel
from typing import List, Optional
import os

from api.services.scorer import scorer

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
        import sqlite3

        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row

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
        quotes = [
            Quote(
                id=row['id'],
                page=row['page'],
                section=row['section'] if 'section' in row.keys() else None,
                quote_text=row['quote_text'],
                keywords=row['keywords']
            )
            for row in paginated_quotes
        ]

        conn.close()

        return BookQuotesResponse(
            book_id=book_id,
            relevant=relevant,
            offset=offset,
            quotes=quotes,
            has_more=has_more,
            total_count=total_count
        )

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
        import sqlite3

        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row

        cursor = conn.cursor()
        cursor.execute("""
        SELECT title, authors, year, publisher, journal, doi, isbn, iso690
        FROM books WHERE id = ?
        """, (book_id,))

        book = cursor.fetchone()
        conn.close()

        if not book:
            raise HTTPException(status_code=404, detail="Book not found")

        # Use ISO690 if available, otherwise generate basic citation
        if book['iso690']:
            citation = book['iso690']
        else:
            parts = []
            if book['authors']:
                parts.append(book['authors'])
            if book['title']:
                parts.append(f'"{book["title"]}"')
            if book['journal']:
                parts.append(f"<i>{book['journal']}</i>")
            elif book['publisher']:
                parts.append(book['publisher'])
            if book['year']:
                parts.append(str(book['year']))
            if book['doi']:
                parts.append(f"DOI: {book['doi']}")

            citation = ". ".join(parts) + "." if parts else "Citation unavailable"

        return {"citation": citation}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching citation: {str(e)}")