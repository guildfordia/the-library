"""
Edit endpoints for The Library API.
Allows public editing of books and quotes using overlay approach.
"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional

from api.services.editor import editor


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

    Uses overlay approach - edits stored separately, merged on read.
    Source CSV files remain unchanged until admin exports edits.

    **All fields are optional** - only send fields you want to update.
    """
    try:
        # Get client IP for tracking
        client_ip = request.client.host if request.client else "unknown"

        # Convert request to dict, excluding None values
        updates_dict = updates.dict(exclude_none=True)

        if not updates_dict:
            raise HTTPException(status_code=400, detail="No fields to update")

        # Verify book exists
        book = editor.get_entity_with_edits('book', book_id)
        if not book:
            raise HTTPException(status_code=404, detail=f"Book {book_id} not found")

        # Save edits
        results = editor.save_multiple_edits(
            entity_type='book',
            entity_id=book_id,
            updates=updates_dict,
            edited_by=client_ip
        )

        # Check for errors
        errors = [r for r in results if 'error' in r]
        if errors:
            raise HTTPException(
                status_code=400,
                detail=f"Some edits failed: {errors}"
            )

        return EditResponse(
            success=True,
            entity_type='book',
            entity_id=book_id,
            edits_applied=results,
            message=f"Successfully updated {len(results)} field(s)"
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Edit failed: {str(e)}")


@router.put("/quotes/{quote_id}", response_model=EditResponse)
async def edit_quote(quote_id: int, updates: QuoteEditRequest, request: Request):
    """
    Edit quote content or metadata.

    Uses overlay approach - edits stored separately, merged on read.
    Source JSON files remain unchanged until admin exports edits.

    **All fields are optional** - only send fields you want to update.
    """
    try:
        # Get client IP for tracking
        client_ip = request.client.host if request.client else "unknown"

        # Convert request to dict, excluding None values
        updates_dict = updates.dict(exclude_none=True)

        if not updates_dict:
            raise HTTPException(status_code=400, detail="No fields to update")

        # Verify quote exists
        quote = editor.get_entity_with_edits('quote', quote_id)
        if not quote:
            raise HTTPException(status_code=404, detail=f"Quote {quote_id} not found")

        # Save edits
        results = editor.save_multiple_edits(
            entity_type='quote',
            entity_id=quote_id,
            updates=updates_dict,
            edited_by=client_ip
        )

        # Check for errors
        errors = [r for r in results if 'error' in r]
        if errors:
            raise HTTPException(
                status_code=400,
                detail=f"Some edits failed: {errors}"
            )

        return EditResponse(
            success=True,
            entity_type='quote',
            entity_id=quote_id,
            edits_applied=results,
            message=f"Successfully updated {len(results)} field(s)"
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Edit failed: {str(e)}")


@router.get("/books/{book_id}/edits")
async def get_book_edits(book_id: int):
    """
    Get all active edits for a book.
    Useful for showing edit history or detecting conflicts.
    """
    try:
        edits = editor.get_active_edits('book', book_id)
        return {
            "book_id": book_id,
            "active_edits": edits,
            "count": len(edits)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/quotes/{quote_id}/edits")
async def get_quote_edits(quote_id: int):
    """
    Get all active edits for a quote.
    Useful for showing edit history or detecting conflicts.
    """
    try:
        edits = editor.get_active_edits('quote', quote_id)
        return {
            "quote_id": quote_id,
            "active_edits": edits,
            "count": len(edits)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/edits/{edit_id}")
async def revert_edit(edit_id: int):
    """
    Revert a specific edit.
    Marks edit as 'reverted' - original value will be shown again.
    """
    try:
        result = editor.revert_edit(edit_id)
        return {
            "success": True,
            "edit_id": edit_id,
            "status": result['status'],
            "message": f"Edit {edit_id} reverted successfully"
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
