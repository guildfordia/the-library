"""Tests for editor service"""
import pytest
import sqlite3
import tempfile
import os
from api.services.editor import EditorService, InvalidFieldError, EntityNotFoundError


@pytest.fixture
def test_db():
    """Create a temporary test database"""
    fd, path = tempfile.mkstemp(suffix='.db')
    conn = sqlite3.connect(path)

    # Create schema matching actual database
    conn.execute('''
        CREATE TABLE books (
            id INTEGER PRIMARY KEY,
            title TEXT,
            authors TEXT,
            year INTEGER,
            publisher TEXT,
            doi TEXT,
            issn TEXT,
            entry_type TEXT,
            doc_keywords TEXT,
            doc_summary TEXT,
            container TEXT
        )
    ''')

    conn.execute('''
        CREATE TABLE quotes (
            id INTEGER PRIMARY KEY,
            book_id INTEGER,
            quote_text TEXT,
            page INTEGER,
            keywords TEXT,
            section TEXT,
            FOREIGN KEY (book_id) REFERENCES books(id)
        )
    ''')

    # Insert test data
    conn.execute("""
        INSERT INTO books (id, title, authors, year, publisher)
        VALUES (1, 'Test Book', 'Test Author', 2020, 'Test Publisher')
    """)
    conn.execute("""
        INSERT INTO quotes (id, book_id, quote_text, page, keywords)
        VALUES (1, 1, 'Test quote text', 42, 'test, keywords')
    """)
    conn.commit()
    conn.close()

    yield path

    # Cleanup
    os.close(fd)
    os.unlink(path)


def test_editor_save_book_edit(test_db):
    """Test saving a book field edit"""
    editor = EditorService(test_db)

    result = editor.save_edit(
        entity_type='book',
        entity_id=1,
        field_name='title',
        new_value='Updated Title'
    )

    assert result['status'] == 'success'
    assert result['old_value'] == 'Test Book'
    assert result['new_value'] == 'Updated Title'
    assert result['field_name'] == 'title'


def test_editor_save_quote_edit(test_db):
    """Test saving a quote field edit"""
    editor = EditorService(test_db)

    result = editor.save_edit(
        entity_type='quote',
        entity_id=1,
        field_name='quote_text',
        new_value='Updated quote text'
    )

    assert result['status'] == 'success'
    assert result['old_value'] == 'Test quote text'
    assert result['new_value'] == 'Updated quote text'


def test_editor_save_multiple_edits(test_db):
    """Test saving multiple fields at once"""
    editor = EditorService(test_db)

    updates = {
        'title': 'New Title',
        'authors': 'New Author',
        'year': 2025
    }

    results = editor.save_multiple_edits(
        entity_type='book',
        entity_id=1,
        updates=updates
    )

    assert len(results) == 3
    assert all(r['status'] == 'success' for r in results)

    # Verify changes were applied
    conn = sqlite3.connect(test_db)
    cursor = conn.cursor()
    cursor.execute("SELECT title, authors, year FROM books WHERE id = 1")
    row = cursor.fetchone()
    conn.close()

    assert row[0] == 'New Title'
    assert row[1] == 'New Author'
    assert row[2] == 2025


def test_editor_field_whitelist_book(test_db):
    """Test that invalid book fields are rejected"""
    editor = EditorService(test_db)

    with pytest.raises(InvalidFieldError) as exc_info:
        editor.save_edit(
            entity_type='book',
            entity_id=1,
            field_name='malicious_field',
            new_value='value'
        )

    assert 'Invalid field' in str(exc_info.value)
    assert 'malicious_field' in str(exc_info.value)


def test_editor_field_whitelist_quote(test_db):
    """Test that invalid quote fields are rejected"""
    editor = EditorService(test_db)

    with pytest.raises(InvalidFieldError) as exc_info:
        editor.save_edit(
            entity_type='quote',
            entity_id=1,
            field_name='malicious_field',
            new_value='value'
        )

    assert 'Invalid field' in str(exc_info.value)


def test_editor_invalid_entity_type(test_db):
    """Test that invalid entity types are rejected"""
    editor = EditorService(test_db)

    with pytest.raises(InvalidFieldError) as exc_info:
        editor.save_edit(
            entity_type='invalid_type',
            entity_id=1,
            field_name='title',
            new_value='value'
        )

    assert 'Invalid entity_type' in str(exc_info.value)


def test_editor_entity_not_found(test_db):
    """Test that missing entities raise appropriate error"""
    editor = EditorService(test_db)

    with pytest.raises(EntityNotFoundError) as exc_info:
        editor.save_edit(
            entity_type='book',
            entity_id=999,  # Non-existent ID
            field_name='title',
            new_value='value'
        )

    assert 'not found' in str(exc_info.value)


def test_editor_get_entity_book(test_db):
    """Test retrieving a book entity"""
    editor = EditorService(test_db)

    book = editor.get_entity('book', 1)

    assert book is not None
    assert book['title'] == 'Test Book'
    assert book['authors'] == 'Test Author'
    assert book['year'] == 2020


def test_editor_get_entity_quote(test_db):
    """Test retrieving a quote entity"""
    editor = EditorService(test_db)

    quote = editor.get_entity('quote', 1)

    assert quote is not None
    assert quote['quote_text'] == 'Test quote text'
    assert quote['page'] == 42


def test_editor_get_entity_not_found(test_db):
    """Test that get_entity returns None for missing entity"""
    editor = EditorService(test_db)

    book = editor.get_entity('book', 999)

    assert book is None
