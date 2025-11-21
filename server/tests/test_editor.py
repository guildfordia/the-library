"""Tests for editor service"""
import pytest
import sqlite3
import tempfile
import os
from api.services.editor import EditorService


@pytest.fixture
def test_db():
    """Create a temporary test database"""
    fd, path = tempfile.mkstemp(suffix='.db')
    conn = sqlite3.connect(path)

    # Create minimal schema
    conn.execute('''
        CREATE TABLE books (
            id INTEGER PRIMARY KEY,
            title TEXT,
            authors TEXT,
            year INTEGER
        )
    ''')

    conn.execute('''
        CREATE TABLE edits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entity_type TEXT NOT NULL,
            entity_id INTEGER NOT NULL,
            field_name TEXT NOT NULL,
            old_value TEXT,
            new_value TEXT,
            edited_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            edited_by TEXT,
            status TEXT DEFAULT 'active'
        )
    ''')

    # Insert test book
    conn.execute("INSERT INTO books (id, title, authors, year) VALUES (1, 'Test Book', 'Test Author', 2020)")
    conn.commit()
    conn.close()

    yield path

    # Cleanup
    os.close(fd)
    os.unlink(path)


def test_editor_save_edit(test_db):
    """Test saving an edit"""
    editor = EditorService(test_db)

    result = editor.save_edit(
        entity_type='book',
        entity_id=1,
        field_name='title',
        new_value='Updated Title'
    )

    assert result['success'] == True
    assert result['edit_id'] is not None


def test_editor_apply_edits(test_db):
    """Test applying edits overlay"""
    editor = EditorService(test_db)

    # Save an edit first
    editor.save_edit(
        entity_type='book',
        entity_id=1,
        field_name='title',
        new_value='Updated Title'
    )

    # Apply edits
    original_data = {'id': 1, 'title': 'Test Book', 'authors': 'Test Author'}
    result = editor.apply_edits('book', 1, original_data)

    assert result['title'] == 'Updated Title'
    assert result['authors'] == 'Test Author'  # Unchanged


def test_editor_field_whitelist_book(test_db):
    """Test that invalid book fields are rejected"""
    editor = EditorService(test_db)

    with pytest.raises(ValueError) as exc_info:
        editor.save_edit(
            entity_type='book',
            entity_id=1,
            field_name='malicious_field',  # Not in whitelist
            new_value='value'
        )

    assert 'Invalid field' in str(exc_info.value)


def test_editor_invalid_entity_type(test_db):
    """Test that invalid entity types are rejected"""
    editor = EditorService(test_db)

    with pytest.raises(ValueError) as exc_info:
        editor.save_edit(
            entity_type='invalid_type',
            entity_id=1,
            field_name='title',
            new_value='value'
        )

    assert 'Invalid entity_type' in str(exc_info.value)
