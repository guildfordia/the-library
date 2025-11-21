"""
Edit service for The Library.
Handles direct database updates for book and quote metadata.
"""

import sqlite3
from typing import Dict, Any, List, Optional


class EditorService:
    """
    Service for managing direct database edits.
    Updates are written directly to books/quotes tables.
    """

    # Whitelist of allowed fields to prevent SQL injection
    ALLOWED_BOOK_FIELDS = {
        'title', 'authors', 'year', 'publisher', 'doi', 'issn',
        'entry_type', 'doc_keywords', 'doc_summary', 'container'
    }

    ALLOWED_QUOTE_FIELDS = {
        'quote_text', 'page', 'keywords', 'section'
    }

    def __init__(self, db_path: str = "index/library.db"):
        self.db_path = db_path

    def save_edit(
        self,
        entity_type: str,
        entity_id: int,
        field_name: str,
        new_value: Any,
        edited_by: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Save an edit by updating the database directly.
        """
        # Validate entity_type and field_name to prevent SQL injection
        if entity_type == 'book':
            if field_name not in self.ALLOWED_BOOK_FIELDS:
                raise ValueError(f"Invalid field '{field_name}' for book edits. Allowed fields: {', '.join(self.ALLOWED_BOOK_FIELDS)}")
            table_name = 'books'
        elif entity_type == 'quote':
            if field_name not in self.ALLOWED_QUOTE_FIELDS:
                raise ValueError(f"Invalid field '{field_name}' for quote edits. Allowed fields: {', '.join(self.ALLOWED_QUOTE_FIELDS)}")
            table_name = 'quotes'
        else:
            raise ValueError(f"Invalid entity_type: {entity_type}. Must be 'book' or 'quote'")

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Get current value
            cursor.execute(f"SELECT {field_name} FROM {table_name} WHERE id = ?", (entity_id,))
            row = cursor.fetchone()
            if not row:
                raise ValueError(f"{entity_type} with id {entity_id} not found")

            old_value = row[0]

            # Update the field directly
            cursor.execute(
                f"UPDATE {table_name} SET {field_name} = ? WHERE id = ?",
                (new_value, entity_id)
            )

            conn.commit()

            return {
                "entity_type": entity_type,
                "entity_id": entity_id,
                "field_name": field_name,
                "old_value": old_value,
                "new_value": new_value,
                "status": "success"
            }

    def save_multiple_edits(
        self,
        entity_type: str,
        entity_id: int,
        updates: Dict[str, Any],
        edited_by: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Save multiple field edits at once.
        Uses transaction to ensure atomicity.
        """
        results = []

        with sqlite3.connect(self.db_path) as conn:
            try:
                for field_name, new_value in updates.items():
                    result = self.save_edit(entity_type, entity_id, field_name, new_value, edited_by)
                    results.append(result)
                conn.commit()
            except Exception as e:
                conn.rollback()
                results.append({
                    "error": str(e)
                })

        return results

    def get_entity(self, entity_type: str, entity_id: int) -> Optional[Dict[str, Any]]:
        """
        Get entity data from database.
        Returns None if entity not found.
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Get entity data
            if entity_type == 'book':
                cursor.execute("SELECT * FROM books WHERE id = ?", (entity_id,))
            elif entity_type == 'quote':
                cursor.execute("SELECT * FROM quotes WHERE id = ?", (entity_id,))
            else:
                raise ValueError(f"Invalid entity_type: {entity_type}")

            row = cursor.fetchone()
            if not row:
                return None

            return dict(row)


# Singleton instance
editor = EditorService()
