"""
Edit service for The Library.
Handles direct database updates for book and quote metadata.
"""

import sqlite3
import time
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class DatabaseLockError(Exception):
    """Raised when database is locked after retries."""
    pass


class EntityNotFoundError(Exception):
    """Raised when entity (book/quote) is not found."""
    pass


class InvalidFieldError(Exception):
    """Raised when attempting to edit a non-whitelisted field."""
    pass


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

    def __init__(self, db_path: str = "index/library.db", max_retries: int = 3):
        self.db_path = db_path
        self.max_retries = max_retries

    def _retry_on_lock(self, operation, *args, **kwargs):
        """
        Retry an operation if SQLite database is locked.

        SQLite can return SQLITE_BUSY if another process has the database locked.
        This is common in WAL mode with concurrent readers/writers.
        """
        last_error = None

        for attempt in range(self.max_retries):
            try:
                return operation(*args, **kwargs)
            except sqlite3.OperationalError as e:
                if "database is locked" in str(e).lower():
                    last_error = e
                    if attempt < self.max_retries - 1:
                        # Exponential backoff: 0.1s, 0.2s, 0.4s
                        wait_time = 0.1 * (2 ** attempt)
                        logger.warning(f"Database locked, retrying in {wait_time}s (attempt {attempt + 1}/{self.max_retries})")
                        time.sleep(wait_time)
                        continue
                else:
                    # Not a lock error, re-raise immediately
                    raise

        # All retries exhausted
        raise DatabaseLockError(f"Database locked after {self.max_retries} retries") from last_error

    def _validate_field(self, entity_type: str, field_name: str) -> str:
        """
        Validate entity type and field name, return table name.
        Raises InvalidFieldError if validation fails.
        """
        if entity_type == 'book':
            if field_name not in self.ALLOWED_BOOK_FIELDS:
                raise InvalidFieldError(
                    f"Invalid field '{field_name}' for book edits. "
                    f"Allowed fields: {', '.join(sorted(self.ALLOWED_BOOK_FIELDS))}"
                )
            return 'books'
        elif entity_type == 'quote':
            if field_name not in self.ALLOWED_QUOTE_FIELDS:
                raise InvalidFieldError(
                    f"Invalid field '{field_name}' for quote edits. "
                    f"Allowed fields: {', '.join(sorted(self.ALLOWED_QUOTE_FIELDS))}"
                )
            return 'quotes'
        else:
            raise InvalidFieldError(f"Invalid entity_type: {entity_type}. Must be 'book' or 'quote'")

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

        Raises:
            InvalidFieldError: If field is not whitelisted
            EntityNotFoundError: If entity does not exist
            DatabaseLockError: If database is locked after retries
        """
        table_name = self._validate_field(entity_type, field_name)

        def _perform_edit():
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                # Get current value
                cursor.execute(f"SELECT {field_name} FROM {table_name} WHERE id = ?", (entity_id,))
                row = cursor.fetchone()
                if not row:
                    raise EntityNotFoundError(f"{entity_type} with id {entity_id} not found")

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

        return self._retry_on_lock(_perform_edit)

    def save_multiple_edits(
        self,
        entity_type: str,
        entity_id: int,
        updates: Dict[str, Any],
        edited_by: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Save multiple field edits at once.
        Uses transaction to ensure atomicity - all edits succeed or all fail.

        Raises:
            InvalidFieldError: If any field is not whitelisted
            EntityNotFoundError: If entity does not exist
            DatabaseLockError: If database is locked after retries
        """
        # Validate all fields first before starting transaction
        table_name = None
        for field_name in updates.keys():
            table_name = self._validate_field(entity_type, field_name)

        def _perform_multiple_edits():
            results = []

            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                try:
                    # Verify entity exists first
                    cursor.execute(f"SELECT id FROM {table_name} WHERE id = ?", (entity_id,))
                    if not cursor.fetchone():
                        raise EntityNotFoundError(f"{entity_type} with id {entity_id} not found")

                    # Process all edits in a single transaction
                    for field_name, new_value in updates.items():
                        # Get current value
                        cursor.execute(f"SELECT {field_name} FROM {table_name} WHERE id = ?", (entity_id,))
                        row = cursor.fetchone()
                        old_value = row[0] if row else None

                        # Update the field
                        cursor.execute(
                            f"UPDATE {table_name} SET {field_name} = ? WHERE id = ?",
                            (new_value, entity_id)
                        )

                        results.append({
                            "entity_type": entity_type,
                            "entity_id": entity_id,
                            "field_name": field_name,
                            "old_value": old_value,
                            "new_value": new_value,
                            "status": "success"
                        })

                    # Commit transaction - all edits succeed together
                    conn.commit()
                    logger.info(f"Successfully saved {len(results)} edits for {entity_type} {entity_id}")

                except Exception as e:
                    # Rollback transaction on any error
                    conn.rollback()
                    logger.error(f"Failed to save edits for {entity_type} {entity_id}: {e}")
                    raise

            return results

        return self._retry_on_lock(_perform_multiple_edits)

    def get_entity(self, entity_type: str, entity_id: int) -> Optional[Dict[str, Any]]:
        """
        Get entity data from database.

        Returns:
            Dict of entity data or None if not found

        Raises:
            InvalidFieldError: If entity_type is invalid
            DatabaseLockError: If database is locked after retries
        """
        if entity_type not in ('book', 'quote'):
            raise InvalidFieldError(f"Invalid entity_type: {entity_type}. Must be 'book' or 'quote'")

        def _get_entity():
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                # Get entity data
                if entity_type == 'book':
                    cursor.execute("SELECT * FROM books WHERE id = ?", (entity_id,))
                else:  # quote
                    cursor.execute("SELECT * FROM quotes WHERE id = ?", (entity_id,))

                row = cursor.fetchone()
                if not row:
                    return None

                return dict(row)

        return self._retry_on_lock(_get_entity)


# Singleton instance
editor = EditorService()
