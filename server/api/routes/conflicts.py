"""
Conflict resolution endpoints for The Library API.
Manages conflicts between database edits and source files detected during reindexing.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import sqlite3
import os

from api.db import get_optimized_connection

router = APIRouter()

DB_PATH = "index/library.db"


class Conflict(BaseModel):
    """Conflict model"""
    id: int
    entity_type: str
    entity_id: int
    field_name: str
    db_value: Optional[str]
    source_value: Optional[str]
    source_file: Optional[str]
    detected_at: str


class ResolveConflictRequest(BaseModel):
    """Request to resolve a conflict"""
    resolution: str  # 'keep_db', 'use_source', or 'merge'
    notes: Optional[str] = None


@router.get("/conflicts", response_model=List[Conflict])
async def list_conflicts(resolved: bool = False):
    """
    List all conflicts.

    - **resolved=false**: Only unresolved conflicts (default)
    - **resolved=true**: Only resolved conflicts
    """
    try:
        conn = get_optimized_connection(DB_PATH)
        conn.row_factory = sqlite3.Row
        try:
            if resolved:
                sql = "SELECT * FROM conflicts WHERE resolved_at IS NOT NULL ORDER BY detected_at DESC"
            else:
                sql = "SELECT * FROM conflicts WHERE resolved_at IS NULL ORDER BY detected_at DESC"

            cursor = conn.cursor()
            cursor.execute(sql)
            rows = cursor.fetchall()

            return [Conflict(**dict(row)) for row in rows]
        finally:
            conn.close()

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/conflicts/{conflict_id}")
async def get_conflict(conflict_id: int):
    """Get details of a specific conflict"""
    try:
        conn = get_optimized_connection(DB_PATH)
        conn.row_factory = sqlite3.Row
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM conflicts WHERE id = ?", (conflict_id,))
            row = cursor.fetchone()

            if not row:
                raise HTTPException(status_code=404, detail="Conflict not found")

            return dict(row)
        finally:
            conn.close()

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/conflicts/{conflict_id}/resolve")
async def resolve_conflict(conflict_id: int, request: ResolveConflictRequest):
    """
    Resolve a conflict.

    - **keep_db**: Keep the database value (ignore source)
    - **use_source**: Use the source file value (overwrite DB)
    - **merge**: Manual merge (requires manual intervention)
    """
    if request.resolution not in ['keep_db', 'use_source', 'merge']:
        raise HTTPException(
            status_code=400,
            detail="Invalid resolution. Must be 'keep_db', 'use_source', or 'merge'"
        )

    try:
        conn = get_optimized_connection(DB_PATH)
        try:
            cursor = conn.cursor()

            # Get conflict details
            cursor.execute("SELECT * FROM conflicts WHERE id = ?", (conflict_id,))
            conflict = cursor.fetchone()

            if not conflict:
                raise HTTPException(status_code=404, detail="Conflict not found")

            # Mark as resolved
            cursor.execute("""
                UPDATE conflicts
                SET resolved_at = CURRENT_TIMESTAMP,
                    resolution = ?,
                    notes = ?
                WHERE id = ?
            """, (request.resolution, request.notes, conflict_id))

            conn.commit()

            return {
                "success": True,
                "conflict_id": conflict_id,
                "resolution": request.resolution,
                "message": f"Conflict resolved as '{request.resolution}'"
            }
        finally:
            conn.close()

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/conflicts/stats")
async def conflict_stats():
    """Get statistics about conflicts"""
    try:
        conn = get_optimized_connection(DB_PATH)
        try:
            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) FROM conflicts WHERE resolved_at IS NULL")
            unresolved = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM conflicts WHERE resolved_at IS NOT NULL")
            resolved = cursor.fetchone()[0]

            cursor.execute("""
                SELECT entity_type, COUNT(*) as count
                FROM conflicts
                WHERE resolved_at IS NULL
                GROUP BY entity_type
            """)
            by_type = {row[0]: row[1] for row in cursor.fetchall()}

            return {
                "unresolved": unresolved,
                "resolved": resolved,
                "total": unresolved + resolved,
                "by_type": by_type
            }
        finally:
            conn.close()

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
