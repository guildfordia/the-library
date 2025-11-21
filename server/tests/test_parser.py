"""Tests for query parser service"""
import pytest
from api.services.parser import QueryParser


def test_parser_quoted_phrase():
    """Test that quoted phrases are extracted correctly"""
    parser = QueryParser()
    result = parser.parse('"Black Mountain College"')

    # Exact phrase extracted for phrase bonus scoring
    assert result.exact_phrase == "Black Mountain College"
    # FTS query uses OR'd terms for broader matching with BM25 ranking
    assert 'Black OR Mountain OR College' in result.fts_query


def test_parser_boolean_and():
    """Test AND operator parsing"""
    parser = QueryParser()
    result = parser.parse('education AND art')

    assert 'education' in result.fts_query
    assert 'art' in result.fts_query
    assert result.original_query == 'education AND art'


def test_parser_validates_invalid_query():
    """Test that invalid queries are caught"""
    parser = QueryParser()

    # Empty query should be invalid
    assert not parser.validate_query('')
    assert not parser.validate_query('   ')


def test_parser_prefix_matching():
    """Test prefix matching with asterisk"""
    parser = QueryParser()
    result = parser.parse('educat*')

    assert 'educat*' in result.fts_query


def test_parser_combined_query():
    """Test complex query with multiple features"""
    parser = QueryParser()
    result = parser.parse('"Black Mountain" AND education*')

    assert result.exact_phrase == "Black Mountain"
    assert 'education*' in result.fts_query
