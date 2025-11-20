"""
Edit service for The Library.
Handles overlay edits without modifying source CSV/JSON files.
"""

import sqlite3
from typing import Dict, Any, List, Optional
from datetime import datetime


class EditorService:
    """
    Service for managing edits with overlay approach.
    Edits are stored in separate table and merged on read.
    """

    def __init__(self, db_path: str = "index/library.db"):
        self.db_path = db_path

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection with row factory"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def apply_edits(self, entity_type: str, entity_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply edits to entity by merging base data with active edits.
        This is the core overlay function used by search/get endpoints.
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            # Get active edits for this entity
            cursor.execute("""
                SELECT field_name, new_value
                FROM edits
                WHERE entity_type = ? AND entity_id = ? AND status = 'active'
            """, (entity_type, entity_id))

            edits = cursor.fetchall()

            # Apply edits as overlay
            result = dict(data)
            for edit in edits:
                field_name = edit['field_name']
                new_value = edit['new_value']

                # Convert string to appropriate type based on field
                if field_name in ['year', 'page']:
                    try:
                        result[field_name] = int(new_value) if new_value else None
                    except (ValueError, TypeError):
                        result[field_name] = new_value
                else:
                    result[field_name] = new_value

            return result

        finally:
            conn.close()

    def save_edit(
        self,
        entity_type: str,
        entity_id: int,
        field_name: str,
        new_value: Any,
        edited_by: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Save an edit to the edits table.
        Uses REPLACE to handle updates to existing edits.
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            # Get current value from base table
            if entity_type == 'book':
                cursor.execute(f"SELECT {field_name} FROM books WHERE id = ?", (entity_id,))
            elif entity_type == 'quote':
                cursor.execute(f"SELECT {field_name} FROM quotes WHERE id = ?", (entity_id,))
            else:
                raise ValueError(f"Invalid entity_type: {entity_type}")

            row = cursor.fetchone()
            if not row:
                raise ValueError(f"{entity_type} with id {entity_id} not found")

            old_value = row[0]

            # Check if edit already exists
            cursor.execute("""
                SELECT id, old_value FROM edits
                WHERE entity_type = ? AND entity_id = ? AND field_name = ? AND status = 'active'
            """, (entity_type, entity_id, field_name))

            existing_edit = cursor.fetchone()

            if existing_edit:
                # Update existing edit
                cursor.execute("""
                    UPDATE edits
                    SET new_value = ?, edited_at = CURRENT_TIMESTAMP, edited_by = ?
                    WHERE id = ?
                """, (str(new_value) if new_value is not None else None, edited_by, existing_edit['id']))
                edit_id = existing_edit['id']
            else:
                # Insert new edit
                cursor.execute("""
                    INSERT INTO edits (entity_type, entity_id, field_name, old_value, new_value, edited_by)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    entity_type,
                    entity_id,
                    field_name,
                    str(old_value) if old_value is not None else None,
                    str(new_value) if new_value is not None else None,
                    edited_by
                ))
                edit_id = cursor.lastrowid

            # Update last_modified timestamp on entity
            if entity_type == 'book':
                cursor.execute("""
                    UPDATE books SET last_modified = CURRENT_TIMESTAMP WHERE id = ?
                """, (entity_id,))
            elif entity_type == 'quote':
                cursor.execute("""
                    UPDATE quotes SET last_modified = CURRENT_TIMESTAMP WHERE id = ?
                """, (entity_id,))

            conn.commit()

            return {
                "edit_id": edit_id,
                "entity_type": entity_type,
                "entity_id": entity_id,
                "field_name": field_name,
                "old_value": old_value,
                "new_value": new_value,
                "status": "active"
            }

        finally:
            conn.close()

    def save_multiple_edits(
        self,
        entity_type: str,
        entity_id: int,
        updates: Dict[str, Any],
        edited_by: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Save multiple field edits at once.
        More efficient than calling save_edit multiple times.
        """
        results = []
        for field_name, new_value in updates.items():
            try:
                result = self.save_edit(entity_type, entity_id, field_name, new_value, edited_by)
                results.append(result)
            except Exception as e:
                results.append({
                    "field_name": field_name,
                    "error": str(e)
                })

        return results

    def get_active_edits(self, entity_type: str, entity_id: int) -> List[Dict[str, Any]]:
        """Get all active edits for an entity"""
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT id, field_name, old_value, new_value, edited_at, edited_by
                FROM edits
                WHERE entity_type = ? AND entity_id = ? AND status = 'active'
                ORDER BY edited_at DESC
            """, (entity_type, entity_id))

            return [dict(row) for row in cursor.fetchall()]

        finally:
            conn.close()

    def revert_edit(self, edit_id: int) -> Dict[str, Any]:
        """Revert an edit by marking it as reverted"""
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                UPDATE edits SET status = 'reverted' WHERE id = ?
            """, (edit_id,))

            if cursor.rowcount == 0:
                raise ValueError(f"Edit {edit_id} not found")

            conn.commit()

            return {"edit_id": edit_id, "status": "reverted"}

        finally:
            conn.close()

    def get_entity_with_edits(self, entity_type: str, entity_id: int) -> Optional[Dict[str, Any]]:
        """
        Get entity data with all active edits applied.
        Returns None if entity not found.
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            # Get base entity data
            if entity_type == 'book':
                cursor.execute("SELECT * FROM books WHERE id = ?", (entity_id,))
            elif entity_type == 'quote':
                cursor.execute("SELECT * FROM quotes WHERE id = ?", (entity_id,))
            else:
                raise ValueError(f"Invalid entity_type: {entity_type}")

            row = cursor.fetchone()
            if not row:
                return None

            base_data = dict(row)

            # Apply edits overlay
            result = self.apply_edits(entity_type, entity_id, base_data)

            return result

        finally:
            conn.close()


# Singleton instance
editor = EditorService()
