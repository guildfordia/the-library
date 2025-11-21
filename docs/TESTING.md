# Testing Guide for The Library

Comprehensive guide to running and writing tests for The Library.

## Quick Start

```bash
cd server

# Install test dependencies
pip install -r requirements.txt

# Run all tests
make test

# Run specific test suites
make test-unit           # Editor and parser tests
make test-integration    # API integration tests
make test-performance    # Performance benchmarks
make test-coverage       # Generate coverage report
```

## Test Organization

```
server/tests/
├── __init__.py
├── test_editor.py         # EditorService unit tests
├── test_parser.py         # QueryParser unit tests
├── test_api_integration.py # Full API integration tests
└── test_performance.py    # Performance benchmarks
```

## Test Suites

### Unit Tests

Unit tests cover individual services and components in isolation.

**Editor Service** (`test_editor.py`):
- ✅ Save single field edits
- ✅ Save multiple field edits atomically
- ✅ Field whitelist validation
- ✅ Entity type validation
- ✅ Entity not found handling
- ✅ Get entity by ID

**Parser Service** (`test_parser.py`):
- ✅ Extract quoted phrases
- ✅ Boolean operators (AND/OR/NOT)
- ✅ Prefix matching with *
- ✅ Query validation
- ✅ Combined queries

```bash
# Run unit tests only
make test-unit

# Or with pytest directly
pytest tests/test_editor.py tests/test_parser.py -v
```

### Integration Tests

Integration tests validate the full API stack including routes, services, and database interactions.

**Coverage** (`test_api_integration.py`):
- Search endpoints (basic, exact phrase, pagination)
- Quote retrieval by ID
- Edit operations (single, multiple, validation)
- Statistics and health checks
- Error handling

```bash
# Run integration tests
make test-integration

# Or with pytest directly
pytest tests/test_api_integration.py -v
```

### Performance Benchmarks

Performance tests measure response times and throughput under various conditions.

**Benchmarks** (`test_performance.py`):
- Simple search (single term)
- Exact phrase search
- Complex multi-term queries
- Single field edits
- Multiple field edits
- Quote retrieval
- Concurrent search load

**Performance Targets:**
- Simple search: < 1.0s for 1000 quotes
- Single edit: < 0.1s
- 10 concurrent searches: < 5.0s

```bash
# Run performance benchmarks
make test-performance

# Run with detailed benchmark output
pytest tests/test_performance.py -v -m benchmark --benchmark-verbose
```

## Code Coverage

Generate HTML coverage reports to identify untested code:

```bash
# Generate coverage report
make test-coverage

# Open report in browser
open server/htmlcov/index.html
```

**Current Coverage:**
- Editor service: 86%
- Parser service: 78%
- Total: 11% (API routes not yet covered by integration tests)

## Writing Tests

### Unit Test Template

```python
"""Tests for my_service"""
import pytest
from api.services.my_service import MyService

@pytest.fixture
def test_setup():
    """Create test fixtures"""
    # Setup code
    yield test_data
    # Cleanup code

def test_my_feature(test_setup):
    """Test description"""
    service = MyService()

    result = service.do_something(test_setup)

    assert result['status'] == 'success'
    assert result['data'] is not None
```

### Integration Test Template

```python
"""Integration tests for my_endpoint"""
import pytest
from fastapi.testclient import TestClient
from api.main import app

@pytest.fixture
def client():
    return TestClient(app)

def test_my_endpoint(client):
    """Test endpoint behavior"""
    response = client.get('/my-endpoint')

    assert response.status_code == 200
    data = response.json()
    assert 'expected_field' in data
```

### Performance Test Template

```python
"""Performance tests for my_feature"""
import pytest

@pytest.mark.benchmark
def test_my_feature_performance(benchmark):
    """Benchmark my feature"""
    def run_operation():
        return my_service.expensive_operation()

    result = benchmark(run_operation)

    # Verify correctness
    assert result is not None
```

## Running Specific Tests

```bash
# Run single test file
pytest tests/test_editor.py -v

# Run single test function
pytest tests/test_editor.py::test_editor_save_book_edit -v

# Run tests matching pattern
pytest tests/ -k "edit" -v

# Run tests with specific marker
pytest tests/ -m benchmark -v

# Show stdout (useful for debugging)
pytest tests/ -v -s

# Stop on first failure
pytest tests/ -x

# Run last failed tests
pytest tests/ --lf
```

## Test Configuration

Configuration is defined in `pytest.ini`:

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts =
    -v                      # Verbose output
    --tb=short              # Short traceback format
    --cov=api               # Coverage for api package
    --cov-report=term-missing  # Show missing lines
    --cov-report=html       # Generate HTML report
    --asyncio-mode=auto     # Auto-detect async tests
```

## Continuous Integration

Tests run automatically on:
- Every commit to main branch
- Pull request creation
- Manual workflow dispatch

**CI Configuration:**
- GitHub Actions workflow: `.github/workflows/test.yml`
- Runs on Python 3.11+
- Includes coverage reporting
- Fails build on test failures

## Test Data

### Fixtures

Tests use pytest fixtures for setup/teardown:

```python
@pytest.fixture
def test_db():
    """Create temporary test database"""
    fd, path = tempfile.mkstemp(suffix='.db')
    # Create schema and test data
    yield path
    # Cleanup
    os.close(fd)
    os.unlink(path)
```

### Mock Data

- **Books**: 100 test books with varied metadata
- **Quotes**: 1000 test quotes (10 per book)
- **FTS Index**: Populated from test quotes

## Debugging Tests

### Print Debug Info

```python
def test_my_feature():
    result = my_service.operation()
    print(f"Result: {result}")  # Will show with -s flag
    assert result['status'] == 'success'
```

### Use pytest debugger

```bash
# Drop into debugger on failure
pytest tests/ --pdb

# Drop into debugger at start of test
pytest tests/ --trace
```

### Check SQL Queries

```python
def test_with_sql_logging():
    import sqlite3
    sqlite3.enable_callback_tracebacks(True)
    # Test code with SQL debugging
```

## Common Issues

### Import Errors

**Problem**: `ModuleNotFoundError: No module named 'api'`

**Solution**: Run tests from `server/` directory:
```bash
cd server
pytest tests/
```

### Database Locked

**Problem**: `sqlite3.OperationalError: database is locked`

**Solution**: Tests create temporary databases. If tests are interrupted, orphaned DB files may remain:
```bash
find /tmp -name "*.db" -delete
```

### Async Test Failures

**Problem**: `RuntimeWarning: coroutine 'test_async' was never awaited`

**Solution**: Mark async tests with `@pytest.mark.asyncio`:
```python
@pytest.mark.asyncio
async def test_async_operation():
    result = await async_function()
    assert result is not None
```

## Best Practices

1. **One assertion per test**: Focus each test on a single behavior
2. **Use fixtures**: Share setup code via fixtures, not global variables
3. **Test edge cases**: Empty strings, nulls, large inputs, etc.
4. **Mock external services**: Don't depend on network/filesystem
5. **Descriptive names**: `test_editor_rejects_invalid_field` not `test_1`
6. **Arrange-Act-Assert**: Structure tests clearly
7. **Clean up resources**: Use fixtures with cleanup code
8. **Test error paths**: Verify exceptions and error messages
9. **Avoid test interdependence**: Each test should run independently
10. **Keep tests fast**: Use small datasets, mock expensive operations

## Performance Testing

### Benchmarking

pytest-benchmark automatically measures:
- Min/max/mean/median execution time
- Standard deviation
- Iterations per second

```python
@pytest.mark.benchmark
def test_performance(benchmark):
    result = benchmark(expensive_function)
    assert result is not None
```

### Load Testing

For API load testing, use dedicated tools:

```bash
# Apache Bench
ab -n 1000 -c 10 http://localhost:8000/search?q=education

# wrk
wrk -t12 -c400 -d30s http://localhost:8000/search?q=education

# Locust
locust -f tests/locustfile.py
```

## Contributing

When adding features:

1. **Write tests first** (TDD)
2. **Ensure tests pass**: `make test`
3. **Check coverage**: `make test-coverage`
4. **Add integration tests** for API changes
5. **Update documentation** if test patterns change

## Resources

- [pytest documentation](https://docs.pytest.org/)
- [pytest-cov documentation](https://pytest-cov.readthedocs.io/)
- [pytest-benchmark documentation](https://pytest-benchmark.readthedocs.io/)
- [FastAPI testing](https://fastapi.tiangolo.com/tutorial/testing/)
