"""
Quotes endpoint for The Library API.
Handles individual quote retrieval with full citation.
"""

from fastapi import APIRouter, HTTPException, Path, Request
from pydantic import BaseModel
from typing import Optional
import os

from api.services.scorer import scorer
from api.db import get_optimized_connection

router = APIRouter()

class BookInfo(BaseModel):
    id: int
    title: str
    authors: Optional[str]
    year: Optional[int]
    publisher: Optional[str]
    journal: Optional[str]
    doi: Optional[str]
    isbn: Optional[str]
    themes: Optional[str]
    summary: Optional[str]

class QuoteDetail(BaseModel):
    id: int
    quote_text: str
    page: Optional[int]
    section: Optional[str]
    keywords: Optional[str]
    book: BookInfo
    citation: str

@router.get("/{quote_id}", response_model=QuoteDetail)
async def get_quote(
    quote_id: int = Path(..., description="Quote ID", ge=1)
):
    """
    Get a single quote by ID with full book metadata and citation.

    Returns the complete quote information including:
    - Quote text and metadata (page, keywords)
    - Full book information
    - Formatted citation (ISO 690 or generated)
    """

    # Check if database exists
    db_path = "index/library.db"
    if not os.path.exists(db_path):
        raise HTTPException(status_code=503, detail="Search index not found. Please run the indexer first.")

    try:
        # Get quote with book information
        quote_data = scorer.get_quote_by_id(db_path, quote_id)

        if not quote_data:
            raise HTTPException(status_code=404, detail="Quote not found")

        # Convert to response format
        book_info = BookInfo(
            id=quote_data["book"]["id"],
            title=quote_data["book"]["title"],
            authors=quote_data["book"]["authors"],
            year=quote_data["book"]["year"],
            publisher=quote_data["book"]["publisher"],
            journal=quote_data["book"]["journal"],
            doi=quote_data["book"]["doi"],
            isbn=quote_data["book"]["isbn"],
            themes=quote_data["book"]["themes"],
            summary=quote_data["book"]["summary"]
        )

        return QuoteDetail(
            id=quote_data["id"],
            quote_text=quote_data["quote_text"],
            page=quote_data["page"],
            section=quote_data["section"],
            keywords=quote_data["keywords"],
            book=book_info,
            citation=quote_data["citation"]
        )

    except Exception as e:
        if "Quote not found" in str(e):
            raise
        raise HTTPException(status_code=500, detail=f"Error retrieving quote: {str(e)}")

@router.post("/admin/reindex")
async def reindex(request: Request):
    """
    Administrative endpoint to rebuild the search index.
    Triggers the indexer to rebuild from CSV and JSON sources.

    Rate limit: 5 requests per hour per IP address.
    """
    # Apply rate limiting
    limiter = request.app.state.limiter
    await limiter.hit("5/hour", request=request)

    try:
        import subprocess
        import sys

        # Run the indexer script
        result = subprocess.run([
            sys.executable, "-m", "indexer.build_index"
        ], capture_output=True, text=True, check=True)

        # Parse output for stats (basic implementation)
        output_lines = result.stdout.split('\n')
        stats = {"status": "success", "output": result.stdout}

        # Try to extract book and quote counts from output
        for line in output_lines:
            if "Books:" in line:
                try:
                    stats["indexed_books"] = int(line.split("Books:")[1].strip())
                except:
                    pass
            elif "Quotes:" in line:
                try:
                    stats["indexed_quotes"] = int(line.split("Quotes:")[1].strip())
                except:
                    pass

        return stats

    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"Indexing failed: {e.stderr}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Indexing error: {str(e)}")

@router.get("/admin/stats")
async def get_stats():
    """
    Get database statistics.
    """
    # Check if database exists
    db_path = "index/library.db"
    if not os.path.exists(db_path):
        raise HTTPException(status_code=503, detail="Search index not found. Please run the indexer first.")

    try:
        conn = get_optimized_connection(db_path)
        try:
            cursor = conn.cursor()

            # Get table counts
            cursor.execute("SELECT COUNT(*) FROM books")
            book_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM quotes")
            quote_count = cursor.fetchone()[0]

            # Get FTS stats
            cursor.execute("SELECT COUNT(*) FROM quotes_fts")
            fts_count = cursor.fetchone()[0]
        finally:
            conn.close()

        # Get database file size (outside connection)
        db_size = os.path.getsize(db_path)

        return {
            "books": book_count,
            "quotes": quote_count,
            "fts_entries": fts_count,
            "database_size_bytes": db_size,
            "database_path": db_path
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting stats: {str(e)}")