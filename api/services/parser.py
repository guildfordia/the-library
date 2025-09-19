"""Query parsing service handling quoted phrases, boolean operators, and prefix matching."""

import re
from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass
class ParsedQuery:
    """Structured representation of a parsed search query."""
    fts_query: str
    exact_phrase: Optional[str]
    original_query: str


class QueryParser:
    """Parse user queries into FTS5-compatible format."""

    def __init__(self):
        self.quoted_phrase_pattern = r'"([^"]+)"'
        self.prefix_pattern = r'\b(\w+)\*'
        self.boolean_pattern = r'\b(AND|OR|NOT)\b'

    def parse(self, query: str) -> ParsedQuery:
        """Parse user query into FTS5 format with support for phrases, operators, and prefix matching."""
        if not query or not query.strip():
            return ParsedQuery(fts_query="", exact_phrase=None, original_query=query)

        original_query = query.strip()
        exact_phrase = self._extract_first_quoted_phrase(query)
        fts_query = self._convert_to_fts(query)

        return ParsedQuery(
            fts_query=fts_query,
            exact_phrase=exact_phrase,
            original_query=original_query
        )

    def _extract_first_quoted_phrase(self, query: str) -> Optional[str]:
        """Extract the first quoted phrase from the query."""
        matches = re.findall(self.quoted_phrase_pattern, query, re.IGNORECASE)
        return matches[0] if matches else None

    def _convert_to_fts(self, query: str) -> str:
        """Convert user query to FTS5 MATCH syntax."""
        fts_query = query

        # Normalize boolean operators to uppercase
        fts_query = re.sub(r'\band\b', 'AND', fts_query, flags=re.IGNORECASE)
        fts_query = re.sub(r'\bor\b', 'OR', fts_query, flags=re.IGNORECASE)
        fts_query = re.sub(r'\bnot\b', 'NOT', fts_query, flags=re.IGNORECASE)

        # Clean up extra whitespace
        fts_query = re.sub(r'\s+', ' ', fts_query).strip()

        # Ensure we have valid content to search
        if not fts_query or fts_query in ['AND', 'OR', 'NOT']:
            return ""

        return fts_query

    def extract_field_filters(self, query: str) -> Tuple[str, dict]:
        """Extract field filters from query (future feature)."""
        # TODO: Implement field filtering for post-MVP
        return query, {}

    def validate_query(self, query: str) -> bool:
        """Validate that a query is safe and reasonable."""
        if not query or not query.strip():
            return False

        if len(query) > 1000:
            return False

        # Check for balanced quotes
        quote_count = query.count('"')
        if quote_count % 2 != 0:
            return False

        # Check for reasonable characters
        if re.search(r'[^\w\s\'"*()AND|OR|NOT-]', query):
            return False

        return True


# Global parser instance
parser = QueryParser()