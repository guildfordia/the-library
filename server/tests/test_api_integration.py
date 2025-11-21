"""Integration tests for The Library API"""
import pytest
import sqlite3
import tempfile
import os
from fastapi.testclient import TestClient
from api.main import app


@pytest.fixture
def test_db_with_data():
    """Create a test database with sample data"""
    fd, path = tempfile.mkstemp(suffix='.db')
    conn = sqlite3.connect(path)

    # Create full schema
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
            container TEXT,
            source_path TEXT
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
            source_file TEXT,
            FOREIGN KEY (book_id) REFERENCES books(id)
        )
    ''')

    # Create FTS table
    conn.execute('''
        CREATE VIRTUAL TABLE quotes_fts USING fts5(
            quote_text,
            keywords,
            content='quotes',
            content_rowid='id'
        )
    ''')

    # Insert test data
    conn.execute("""
        INSERT INTO books (id, title, authors, year, publisher, doc_keywords)
        VALUES
            (1, 'Black Mountain College', 'Harris, Mary Emma', 2003, 'Test Publisher', 'education, art'),
            (2, 'Learning Through Making', 'Smith, Jane', 2020, 'Another Publisher', 'pedagogy, craft')
    """)

    conn.execute("""
        INSERT INTO quotes (id, book_id, quote_text, page, keywords)
        VALUES
            (1, 1, 'Black Mountain College was an experimental institution', 10, 'education, experimental'),
            (2, 1, 'The college emphasized learning by doing', 25, 'pedagogy, practice'),
            (3, 2, 'Making is a form of thinking', 5, 'craft, cognition')
    """)

    # Populate FTS
    conn.execute("""
        INSERT INTO quotes_fts (rowid, quote_text, keywords)
        SELECT id, quote_text, keywords FROM quotes
    """)

    conn.commit()
    conn.close()

    # Store original DB path and swap
    original_db = os.environ.get('TEST_DB_PATH')
    os.environ['TEST_DB_PATH'] = path

    yield path

    # Cleanup
    if original_db:
        os.environ['TEST_DB_PATH'] = original_db
    else:
        os.environ.pop('TEST_DB_PATH', None)

    os.close(fd)
    os.unlink(path)


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


def test_search_endpoint_basic(client, test_db_with_data, monkeypatch):
    """Test basic search functionality"""
    # Monkeypatch the database path
    monkeypatch.setenv('DB_PATH', test_db_with_data)

    response = client.get('/search?q=Black Mountain')

    assert response.status_code == 200
    data = response.json()
    assert 'results' in data
    assert 'total' in data


def test_search_endpoint_exact_phrase(client, test_db_with_data, monkeypatch):
    """Test search with exact phrase matching"""
    monkeypatch.setenv('DB_PATH', test_db_with_data)

    response = client.get('/search?q="Black Mountain College"')

    assert response.status_code == 200
    data = response.json()
    assert data['total'] > 0


def test_search_endpoint_pagination(client, test_db_with_data, monkeypatch):
    """Test search pagination"""
    monkeypatch.setenv('DB_PATH', test_db_with_data)

    response = client.get('/search?q=education&offset=0&limit=1')

    assert response.status_code == 200
    data = response.json()
    assert data['offset'] == 0
    assert data['limit'] == 1


def test_search_endpoint_empty_query(client):
    """Test that empty queries are rejected"""
    response = client.get('/search?q=')

    assert response.status_code == 400


def test_get_quote_by_id(client, test_db_with_data, monkeypatch):
    """Test retrieving a specific quote"""
    monkeypatch.setenv('DB_PATH', test_db_with_data)

    response = client.get('/quotes/1')

    assert response.status_code == 200
    data = response.json()
    assert data['id'] == 1
    assert 'quote_text' in data
    assert 'book' in data


def test_get_quote_not_found(client, test_db_with_data, monkeypatch):
    """Test that non-existent quotes return 404"""
    monkeypatch.setenv('DB_PATH', test_db_with_data)

    response = client.get('/quotes/999')

    assert response.status_code == 404


def test_health_endpoint(client):
    """Test health check endpoint"""
    response = client.get('/health')

    assert response.status_code == 200
    data = response.json()
    assert data['status'] == 'ok'


def test_stats_endpoint(client, test_db_with_data, monkeypatch):
    """Test database statistics endpoint"""
    monkeypatch.setenv('DB_PATH', test_db_with_data)

    response = client.get('/quotes/stats')

    assert response.status_code == 200
    data = response.json()
    assert 'books' in data
    assert 'quotes' in data


def test_edit_book_field(client, test_db_with_data, monkeypatch):
    """Test editing a book field"""
    monkeypatch.setenv('DB_PATH', test_db_with_data)

    payload = {
        'entity_type': 'book',
        'entity_id': 1,
        'field_name': 'title',
        'new_value': 'Updated Title'
    }

    response = client.post('/edits/save', json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data['status'] == 'success'


def test_edit_invalid_field(client, test_db_with_data, monkeypatch):
    """Test that invalid fields are rejected"""
    monkeypatch.setenv('DB_PATH', test_db_with_data)

    payload = {
        'entity_type': 'book',
        'entity_id': 1,
        'field_name': 'malicious_field',
        'new_value': 'value'
    }

    response = client.post('/edits/save', json=payload)

    assert response.status_code == 400
