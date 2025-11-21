"""Expert mode endpoints for advanced functionality."""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from api.services.indexer import indexer
from api.db import get_optimized_connection

logger = logging.getLogger(__name__)

router = APIRouter()


class ReindexRequest(BaseModel):
    """Request model for reindexing operation."""
    csv_path: Optional[str] = None
    json_folder: Optional[str] = None


class ReindexResponse(BaseModel):
    """Response model for reindexing operation."""
    status: str
    books_processed: int
    quotes_processed: int
    elapsed_seconds: float
    database_path: str
    message: str


@router.post("/reindex", response_model=ReindexResponse)
async def reindex_database(request: ReindexRequest):
    """
    Reindex the search database from CSV and/or JSON files.

    This endpoint rebuilds the entire search index:
    - Drops existing tables (books, quotes, quotes_fts)
    - Recreates schema
    - Imports data from CSV (books) and/or JSON folder (quotes)
    - Rebuilds FTS5 search index

    Args:
        request: Contains csv_path and/or json_folder paths

    Returns:
        ReindexResponse with processing statistics

    Raises:
        HTTPException: If files not found or processing fails
    """
    logger.info(f"Reindex request: csv_path={request.csv_path}, json_folder={request.json_folder}")

    # Validate input
    if not request.csv_path and not request.json_folder:
        raise HTTPException(
            status_code=400,
            detail="At least one of csv_path or json_folder must be provided"
        )

    try:
        # Perform reindexing
        result = indexer.reindex_from_files(
            csv_path=request.csv_path,
            json_folder=request.json_folder
        )

        # Create success response
        message_parts = []
        if request.csv_path:
            message_parts.append(f"CSV: {result['books_processed']} books")
        if request.json_folder:
            message_parts.append(f"JSON: {result['quotes_processed']} quotes")

        message = f"Successfully reindexed {', '.join(message_parts)} in {result['elapsed_seconds']}s"

        return ReindexResponse(
            status=result["status"],
            books_processed=result["books_processed"],
            quotes_processed=result["quotes_processed"],
            elapsed_seconds=result["elapsed_seconds"],
            database_path=result["database_path"],
            message=message
        )

    except FileNotFoundError as e:
        logger.error(f"File not found: {str(e)}")
        raise HTTPException(status_code=404, detail=str(e))

    except ValueError as e:
        logger.error(f"Invalid input: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        logger.error(f"Reindexing failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Reindexing failed: {str(e)}"
        )


@router.get("/status")
async def get_expert_status():
    """Get status of the expert mode system."""
    try:
        import os

        db_path = "index/library.db"

        if not os.path.exists(db_path):
            return {
                "database_exists": False,
                "message": "No database found. Use /expert/reindex to create one."
            }

        conn = get_optimized_connection(db_path)
        try:
            cursor = conn.cursor()

            # Get table counts
            cursor.execute("SELECT COUNT(*) FROM books")
            books_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM quotes")
            quotes_count = cursor.fetchone()[0]

            # Get database file size
            db_size = os.path.getsize(db_path)

            return {
                "database_exists": True,
                "database_path": db_path,
                "database_size_mb": round(db_size / (1024 * 1024), 2),
                "books_count": books_count,
                "quotes_count": quotes_count,
                "message": f"Database ready with {books_count} books and {quotes_count} quotes"
            }
        finally:
            conn.close()

    except Exception as e:
        logger.error(f"Failed to get expert status: {str(e)}")
        return {
            "database_exists": False,
            "error": str(e),
            "message": "Failed to check database status"
        }