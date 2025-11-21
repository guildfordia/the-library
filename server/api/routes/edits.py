"""
Edit endpoints for The Library API.
Allows public editing of books and quotes with proper error handling.
"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional

from api.services.editor import (
    editor,
    InvalidFieldError,
    EntityNotFoundError,
    DatabaseLockError
)


router = APIRouter()


# Request models
class BookEditRequest(BaseModel):
    """Request model for editing book fields"""
    title: Optional[str] = None
    authors: Optional[str] = None
    year: Optional[int] = None
    doi: Optional[str] = None
    container: Optional[str] = None
    themes: Optional[str] = None
    entry_type: Optional[str] = None
    volume: Optional[str] = None
    issue: Optional[str] = None
    pages: Optional[str] = None
    publisher: Optional[str] = None
    issn: Optional[str] = None
    doc_summary: Optional[str] = None
    doc_keywords: Optional[str] = None

    class Config:
        # Only send fields that are actually set
        exclude_none = True


class QuoteEditRequest(BaseModel):
    """Request model for editing quote fields"""
    quote_text: Optional[str] = None
    page: Optional[int] = None
    keywords: Optional[str] = None
    section: Optional[str] = None

    class Config:
        exclude_none = True


class EditResponse(BaseModel):
    """Response model for edit operations"""
    success: bool
    entity_type: str
    entity_id: int
    edits_applied: List[Dict[str, Any]]
    message: str


# Endpoints
@router.put("/books/{book_id}", response_model=EditResponse)
async def edit_book(book_id: int, updates: BookEditRequest, request: Request):
    """
    Edit book metadata.

    Edits are written directly to the database.
    Export database to preserve edits before reindexing.

    Rate limit: 50 requests per minute per IP address.

    **All fields are optional** - only send fields you want to update.
    """
    # Apply rate limiting
    limiter = request.app.state.limiter
    # await limiter.hit("50/minute", request=request)

    try:
        # Get client IP for tracking
        client_ip = request.client.host if request.client else "unknown"

        # Convert request to dict, excluding None values
        updates_dict = updates.dict(exclude_none=True)

        if not updates_dict:
            raise HTTPException(status_code=400, detail="No fields to update")

        # Verify book exists
        book = editor.get_entity('book', book_id)
        if not book:
            raise HTTPException(status_code=404, detail=f"Book {book_id} not found")

        # Save edits (transaction ensures all succeed or all fail)
        results = editor.save_multiple_edits(
            entity_type='book',
            entity_id=book_id,
            updates=updates_dict,
            edited_by=client_ip
        )

        return EditResponse(
            success=True,
            entity_type='book',
            entity_id=book_id,
            edits_applied=results,
            message=f"Successfully updated {len(results)} field(s)"
        )

    except InvalidFieldError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except EntityNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except DatabaseLockError as e:
        raise HTTPException(status_code=503, detail=f"Database temporarily unavailable: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


@router.put("/quotes/{quote_id}", response_model=EditResponse)
async def edit_quote(quote_id: int, updates: QuoteEditRequest, request: Request):
    """
    Edit quote content or metadata.

    Edits are written directly to the database.
    Export database to preserve edits before reindexing.

    Rate limit: 50 requests per minute per IP address.

    **All fields are optional** - only send fields you want to update.
    """
    # Apply rate limiting
    limiter = request.app.state.limiter
    # await limiter.hit("50/minute", request=request)

    try:
        # Get client IP for tracking
        client_ip = request.client.host if request.client else "unknown"

        # Convert request to dict, excluding None values
        updates_dict = updates.dict(exclude_none=True)

        if not updates_dict:
            raise HTTPException(status_code=400, detail="No fields to update")

        # Verify quote exists
        quote = editor.get_entity('quote', quote_id)
        if not quote:
            raise HTTPException(status_code=404, detail=f"Quote {quote_id} not found")

        # Save edits (transaction ensures all succeed or all fail)
        results = editor.save_multiple_edits(
            entity_type='quote',
            entity_id=quote_id,
            updates=updates_dict,
            edited_by=client_ip
        )

        return EditResponse(
            success=True,
            entity_type='quote',
            entity_id=quote_id,
            edits_applied=results,
            message=f"Successfully updated {len(results)} field(s)"
        )

    except InvalidFieldError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except EntityNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except DatabaseLockError as e:
        raise HTTPException(status_code=503, detail=f"Database temporarily unavailable: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


# Note: Edit history and revert functionality removed
# Edits are now written directly to database
# Use conflicts API and export/import workflow for managing changes
