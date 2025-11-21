"""
Search endpoint for The Library API.
Handles quote search with FTS5 + BM25 scoring.
"""

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import os

from api.services.parser import parser
from api.services.scorer import scorer
from api.models.scoring_config import tuning_manager

router = APIRouter()

class QuoteResult(BaseModel):
    id: int
    quote_text: str
    page: Optional[int]
    keywords: Optional[str]
    score: float
    score_breakdown: Optional[Dict[str, Any]] = None

class BookResult(BaseModel):
    id: int
    title: str
    authors: Optional[str]
    year: Optional[int]
    publisher: Optional[str]
    journal: Optional[str]
    doi: Optional[str]
    isbn: Optional[str]
    type: Optional[str]
    themes: Optional[str]
    keywords: Optional[str]
    summary: Optional[str]
    iso690: Optional[str]

class SearchResultItem(BaseModel):
    book: BookResult
    hits_count: int
    top_quotes: List[QuoteResult]
    total_book_quotes: Optional[int] = None

class SearchResponse(BaseModel):
    results: List[SearchResultItem]
    total: int
    offset: int
    limit: int
    query: str

@router.get("", response_model=SearchResponse)
async def search_quotes(
    request: Request,
    q: str = Query(..., description="Search query with support for quoted phrases, boolean operators, and prefix matching"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(20, ge=1, le=100, description="Number of results per page")
):
    """
    Search for quotes across the library.

    Rate limit: 100 requests per minute per IP address.

    Supports:
    - Quoted phrases: "exact phrase" (gets phrase bonus in scoring)
    - Boolean operators: term1 AND term2, term1 OR term2, NOT term3
    - Prefix matching: term*
    - Combined: "Black Mountain College" AND education*

    Returns book-grouped results with expandable quotes.
    """
    # Apply rate limiting
    limiter = request.app.state.limiter
    # await limiter.hit("100/minute", request=request)

    if not q or not q.strip():
        raise HTTPException(status_code=400, detail="Query parameter 'q' is required")

    # Validate query
    if not parser.validate_query(q):
        raise HTTPException(status_code=400, detail="Invalid query format")

    # Parse query
    parsed_query = parser.parse(q)

    if not parsed_query.fts_query:
        raise HTTPException(status_code=400, detail="Query could not be parsed")

    # Check if database exists
    db_path = "index/library.db"
    if not os.path.exists(db_path):
        raise HTTPException(status_code=503, detail="Search index not found. Please run the indexer first.")

    try:
        # Update scorer with current tuning configuration
        current_config = tuning_manager.get_current_config()
        current_overrides = tuning_manager.get_current_overrides()
        scorer.update_config(current_config, current_overrides)

        # Search and score with detailed breakdown (now fixed!)
        results = scorer.search_with_breakdown(
            db_path=db_path,
            fts_query=parsed_query.fts_query,
            exact_phrase=parsed_query.exact_phrase,
            limit=1000  # Get more results for proper ranking before pagination
        )

        # Apply pagination to the sorted results
        paginated_results = results["results"][offset:offset + limit]
        results["results"] = paginated_results
        results["offset"] = offset
        results["limit"] = limit

        # Convert to response format
        search_results = []
        for item in results["results"]:
            book_data = item["book"]

            # Book data is read directly from database
            book_result = BookResult(
                id=book_data.get("id", 0),
                title=book_data.get("title", ""),
                authors=book_data.get("authors"),
                year=book_data.get("year"),
                publisher=book_data.get("publisher"),
                journal=book_data.get("container"),  # Map container -> journal
                doi=book_data.get("doi"),
                isbn=book_data.get("issn"),  # Map issn -> isbn
                type=book_data.get("entry_type"),  # Map entry_type -> type (article, book, etc.)
                themes=book_data.get("container"),  # Map container -> themes (publication/journal as theme)
                keywords=book_data.get("doc_keywords"),  # Map doc_keywords -> keywords
                summary=book_data.get("doc_summary"),  # Map doc_summary -> summary
                iso690=None  # Not implemented yet
            )

            quote_results = []
            for quote in item["top_quotes"]:
                # Convert ScoringBreakdown object to dict if present
                score_breakdown = quote.get("score_breakdown")
                if score_breakdown and hasattr(score_breakdown, 'dict'):
                    score_breakdown = score_breakdown.dict()

                quote_results.append(QuoteResult(
                    id=quote["id"],
                    quote_text=quote["quote_text"],
                    page=quote["page"],
                    keywords=quote["keywords"],
                    score=quote["score"],
                    score_breakdown=score_breakdown
                ))

            search_results.append(SearchResultItem(
                book=book_result,
                hits_count=item["hits_count"],
                top_quotes=quote_results,
                total_book_quotes=item.get("total_book_quotes")
            ))

        return SearchResponse(
            results=search_results,
            total=results["total"],
            offset=results["offset"],
            limit=results["limit"],
            query=parsed_query.original_query
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search error: {str(e)}")

@router.get("/debug")
async def debug_search(q: str = Query(..., description="Query to debug")):
    """
    Debug endpoint to see how queries are parsed.
    Useful for development and troubleshooting.
    """
    parsed_query = parser.parse(q)

    return {
        "original_query": parsed_query.original_query,
        "fts_query": parsed_query.fts_query,
        "exact_phrase": parsed_query.exact_phrase,
        "is_valid": parser.validate_query(q)
    }