.PHONY: test test-unit test-integration test-performance test-coverage install clean help

# Default target
help:
	@echo "The Library - Test Commands"
	@echo "============================"
	@echo "make install            - Install dependencies including test tools"
	@echo "make test               - Run all tests"
	@echo "make test-unit          - Run unit tests only"
	@echo "make test-integration   - Run integration tests only"
	@echo "make test-performance   - Run performance benchmarks"
	@echo "make test-coverage      - Run tests with coverage report"
	@echo "make clean              - Clean test artifacts"

# Install dependencies
install:
	pip install -r requirements.txt

# Run all tests
test:
	pytest tests/ -v

# Run unit tests only (editor, parser)
test-unit:
	pytest tests/test_editor.py tests/test_parser.py -v

# Run integration tests only
test-integration:
	pytest tests/test_api_integration.py -v

# Run performance benchmarks
test-performance:
	pytest tests/test_performance.py -v -m benchmark --benchmark-only

# Run tests with coverage report
test-coverage:
	pytest tests/ --cov=api --cov-report=term-missing --cov-report=html
	@echo "Coverage report generated in htmlcov/index.html"

# Clean test artifacts
clean:
	rm -rf .pytest_cache
	rm -rf htmlcov
	rm -rf .coverage
	rm -f *.db
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
