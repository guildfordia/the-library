"""Performance benchmarks for The Library"""
import pytest
import sqlite3
import tempfile
import os
import time
from api.services.scorer import QuoteScorer
from api.services.editor import EditorService


@pytest.fixture
def large_test_db():
    """Create a test database with substantial data for performance testing"""
    fd, path = tempfile.mkstemp(suffix='.db')
    conn = sqlite3.connect(path)

    # Create schema
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
            source_file TEXT
        )
    ''')

    conn.execute('''
        CREATE VIRTUAL TABLE quotes_fts USING fts5(
            quote_text,
            keywords,
            content='quotes',
            content_rowid='id'
        )
    ''')

    # Insert 100 books
    books_data = [
        (i, f'Book Title {i}', f'Author {i % 10}', 2000 + (i % 25), f'Publisher {i % 5}', f'education, topic{i % 20}')
        for i in range(1, 101)
    ]
    conn.executemany(
        "INSERT INTO books (id, title, authors, year, publisher, doc_keywords) VALUES (?, ?, ?, ?, ?, ?)",
        books_data
    )

    # Insert 1000 quotes (10 per book)
    quotes_data = []
    for book_id in range(1, 101):
        for quote_idx in range(1, 11):
            quote_id = (book_id - 1) * 10 + quote_idx
            quote_text = f'This is quote {quote_idx} from book {book_id} about education and learning. ' \
                        f'It discusses important topics like pedagogy, teaching, and knowledge transfer.'
            quotes_data.append((quote_id, book_id, quote_text, quote_idx * 5, f'keyword{quote_idx % 5}'))

    conn.executemany(
        "INSERT INTO quotes (id, book_id, quote_text, page, keywords) VALUES (?, ?, ?, ?, ?)",
        quotes_data
    )

    # Populate FTS
    conn.execute("""
        INSERT INTO quotes_fts (rowid, quote_text, keywords)
        SELECT id, quote_text, keywords FROM quotes
    """)

    conn.commit()
    conn.close()

    yield path

    # Cleanup
    os.close(fd)
    os.unlink(path)


@pytest.mark.benchmark
def test_search_performance_simple_query(large_test_db, benchmark):
    """Benchmark simple single-term search"""
    scorer = QuoteScorer()

    def run_search():
        return scorer.search_and_score(
            db_path=large_test_db,
            fts_query='education',
            offset=0,
            limit=20
        )

    result = benchmark(run_search)

    # Verify results are returned
    assert result['total'] > 0
    assert len(result['results']) > 0


@pytest.mark.benchmark
def test_search_performance_exact_phrase(large_test_db, benchmark):
    """Benchmark exact phrase search"""
    scorer = QuoteScorer()

    def run_search():
        return scorer.search_and_score(
            db_path=large_test_db,
            fts_query='"education and learning"',
            exact_phrase='education and learning',
            offset=0,
            limit=20
        )

    result = benchmark(run_search)
    assert result['total'] > 0


@pytest.mark.benchmark
def test_search_performance_complex_query(large_test_db, benchmark):
    """Benchmark complex multi-term query"""
    scorer = QuoteScorer()

    def run_search():
        return scorer.search_and_score(
            db_path=large_test_db,
            fts_query='education AND pedagogy OR teaching',
            offset=0,
            limit=20
        )

    result = benchmark(run_search)
    assert result['total'] >= 0


@pytest.mark.benchmark
def test_edit_performance_single_field(large_test_db, benchmark):
    """Benchmark single field edit operation"""
    editor = EditorService(large_test_db)

    def run_edit():
        return editor.save_edit(
            entity_type='book',
            entity_id=1,
            field_name='title',
            new_value=f'Updated Title {time.time()}'
        )

    result = benchmark(run_edit)
    assert result['status'] == 'success'


@pytest.mark.benchmark
def test_edit_performance_multiple_fields(large_test_db, benchmark):
    """Benchmark multiple field edit operation"""
    editor = EditorService(large_test_db)

    def run_edit():
        return editor.save_multiple_edits(
            entity_type='book',
            entity_id=1,
            updates={
                'title': f'Title {time.time()}',
                'authors': f'Author {time.time()}',
                'year': 2025
            }
        )

    results = benchmark(run_edit)
    assert len(results) == 3


@pytest.mark.benchmark
def test_get_quote_performance(large_test_db, benchmark):
    """Benchmark single quote retrieval"""
    scorer = QuoteScorer()

    def get_quote():
        return scorer.get_quote_by_id(large_test_db, 50)

    result = benchmark(get_quote)
    assert result is not None
    assert result['id'] == 50


def test_search_response_time_target(large_test_db):
    """Test that searches complete within acceptable time"""
    scorer = QuoteScorer()

    start = time.time()
    result = scorer.search_and_score(
        db_path=large_test_db,
        fts_query='education',
        offset=0,
        limit=20
    )
    elapsed = time.time() - start

    # Target: sub-second response time for 1000 quotes
    assert elapsed < 1.0, f"Search took {elapsed:.3f}s, target is <1.0s"
    assert result['total'] > 0


def test_edit_response_time_target(large_test_db):
    """Test that edits complete within acceptable time"""
    editor = EditorService(large_test_db)

    start = time.time()
    result = editor.save_edit(
        entity_type='book',
        entity_id=1,
        field_name='title',
        new_value='Updated Title'
    )
    elapsed = time.time() - start

    # Target: sub-100ms response time for single edit
    assert elapsed < 0.1, f"Edit took {elapsed:.3f}s, target is <0.1s"
    assert result['status'] == 'success'


def test_concurrent_search_performance(large_test_db):
    """Test search performance under concurrent load"""
    import concurrent.futures

    scorer = QuoteScorer()

    def run_search(query_num):
        return scorer.search_and_score(
            db_path=large_test_db,
            fts_query=f'education keyword{query_num % 5}',
            offset=0,
            limit=20
        )

    start = time.time()

    # Simulate 10 concurrent searches
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(run_search, i) for i in range(10)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]

    elapsed = time.time() - start

    # All searches should complete successfully
    assert len(results) == 10
    assert all(r['total'] >= 0 for r in results)

    # Target: 10 concurrent searches in < 5 seconds
    assert elapsed < 5.0, f"Concurrent searches took {elapsed:.3f}s, target is <5.0s"
