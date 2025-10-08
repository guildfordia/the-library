"""Scoring service implementing BM25 + phrase bonus algorithm with configurable weights."""

import re
import sqlite3
from typing import Dict, Any, List, Optional


class QuoteScorer:
    """Score quotes using BM25 + phrase bonus algorithm with configurable weights."""

    def __init__(self, phrase_bonus: float = 2.0):
        self.phrase_bonus = phrase_bonus
        self.scoring_config = None
        self.local_overrides = None

    def update_config(self, scoring_config=None, local_overrides=None):
        """Update scoring configuration and local overrides."""
        if scoring_config:
            self.scoring_config = scoring_config
            self.phrase_bonus = scoring_config.phrase_bonus
        if local_overrides:
            self.local_overrides = local_overrides

    def search_and_score(self, db_path: str, fts_query: str, exact_phrase: Optional[str] = None,
                        offset: int = 0, limit: int = 20) -> Dict[str, Any]:
        """Search quotes using FTS5 and return book-grouped results."""
        with sqlite3.connect(db_path) as conn:
            conn.row_factory = sqlite3.Row

            quotes = self._search_quotes(conn, fts_query, exact_phrase)
            book_results = self._group_by_book(conn, quotes, fts_query)

            sorted_books = sorted(
                book_results.values(),
                key=lambda x: (x['top_quotes'][0]['score'] if x['top_quotes'] else 0),
                reverse=True
            )

            total = len(sorted_books)
            paginated_books = sorted_books[offset:offset + limit]

            return {
                "results": paginated_books,
                "total": total,
                "offset": offset,
                "limit": limit
            }

    def search_with_breakdown(self, db_path: str, fts_query: str, exact_phrase: Optional[str] = None,
                             limit: int = 20) -> Dict[str, Any]:
        """Search with detailed score breakdown for tuning purposes."""
        with sqlite3.connect(db_path) as conn:
            conn.row_factory = sqlite3.Row

            quotes = self._search_quotes_with_breakdown(conn, fts_query, exact_phrase)
            book_results = self._group_by_book_with_breakdown(conn, quotes, fts_query)

            sorted_books = sorted(
                book_results.values(),
                key=lambda x: (x['top_quotes'][0]['score'] if x['top_quotes'] else 0),
                reverse=True
            )

            return {
                "results": sorted_books[:limit],
                "total": len(sorted_books)
            }

    def get_quote_by_id(self, db_path: str, quote_id: int) -> Optional[Dict[str, Any]]:
        """Get a single quote by ID with full book metadata."""
        with sqlite3.connect(db_path) as conn:
            conn.row_factory = sqlite3.Row

            sql = """
            SELECT
                q.id, q.quote_text, q.page, q.section, q.keywords, q.source_file,
                b.id as book_id, b.title, b.authors, b.year, b.publisher,
                b.journal, b.doi, b.isbn, b.themes, b.summary, b.iso690
            FROM quotes q
            JOIN books b ON q.book_id = b.id
            WHERE q.id = ?
            """

            cursor = conn.cursor()
            cursor.execute(sql, (quote_id,))
            row = cursor.fetchone()

            if not row:
                return None

            return {
                "id": row['id'],
                "quote_text": row['quote_text'],
                "page": row['page'],
                "section": row['section'],
                "keywords": row['keywords'],
                "book": {
                    "id": row['book_id'],
                    "title": row['title'],
                    "authors": row['authors'],
                    "year": row['year'],
                    "publisher": row['publisher'],
                    "journal": row['journal'],
                    "doi": row['doi'],
                    "isbn": row['isbn'],
                    "themes": row['themes'],
                    "summary": row['summary']
                },
                "citation": row['iso690'] or self._generate_basic_citation(row)
            }

    def _search_quotes(self, conn: sqlite3.Connection, fts_query: str,
                      exact_phrase: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search quotes using FTS5 and calculate scores."""
        if not fts_query:
            return []

        sql = """
        SELECT
            q.id, q.book_id, q.quote_text, q.page, q.keywords, q.source_file,
            fts.rank as bm25_score
        FROM quotes_fts fts
        JOIN quotes q ON q.id = fts.rowid
        WHERE quotes_fts MATCH ?
        ORDER BY fts.rank
        LIMIT 1000
        """

        cursor = conn.cursor()
        cursor.execute(sql, (fts_query,))
        rows = cursor.fetchall()

        quotes = []
        for row in rows:
            quote_data = dict(row)

            phrase_bonus = 0.0
            if exact_phrase and self._contains_exact_phrase(quote_data['quote_text'], exact_phrase):
                phrase_bonus = self.phrase_bonus

            # BM25 scores from FTS5 are negative (lower is better), negate for higher = better
            base_score = -quote_data['bm25_score']
            final_score = base_score + phrase_bonus

            quote_data['score'] = final_score
            quote_data['phrase_bonus'] = phrase_bonus
            quote_data['base_score'] = base_score
            quotes.append(quote_data)

        quotes.sort(key=lambda x: x['score'], reverse=True)
        return quotes

    def _search_quotes_with_breakdown(self, conn: sqlite3.Connection, fts_query: str,
                                     exact_phrase: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search quotes with detailed score breakdown using weighted field search."""
        if not fts_query:
            return []

        field_weights = self.scoring_config.field_weights if self.scoring_config else None

        sql = """
        SELECT
            q.id, q.book_id, q.quote_text, q.page, q.keywords as quote_keywords, q.source_file,
            fts.rank as base_bm25_score,
            b.title as book_title, b.authors as book_authors, b.doc_keywords as book_keywords,
            b.doc_summary as summary, b.publisher, b.container,
            CASE
                WHEN b.container IS NOT NULL AND b.container != '' THEN 'journal'
                WHEN b.publisher IS NOT NULL AND b.publisher != '' THEN 'book'
                ELSE 'unknown'
            END as book_type
        FROM quotes_fts fts
        JOIN quotes q ON q.id = fts.rowid
        JOIN books b ON q.book_id = b.id
        WHERE quotes_fts MATCH ?
        ORDER BY fts.rank
        LIMIT 1000
        """

        cursor = conn.cursor()
        cursor.execute(sql, (fts_query,))
        rows = cursor.fetchall()

        quotes = []
        for row in rows:
            quote_data = dict(row)

            # Calculate BM25 score
            bm25_raw = quote_data['base_bm25_score']
            bm25_normalized = -bm25_raw if bm25_raw < 0 else bm25_raw
            bm25_weight = self.scoring_config.bm25_weight if self.scoring_config else 1.0
            bm25_weighted = bm25_normalized * bm25_weight

            # Calculate field bonuses
            field_score, field_matches = self._calculate_field_scores(quote_data, fts_query, field_weights)

            # Calculate phrase bonus
            phrase_bonus = 0.0
            if exact_phrase and self._contains_exact_phrase(quote_data['quote_text'], exact_phrase):
                phrase_bonus = self.phrase_bonus

            final_score = bm25_weighted + field_score + phrase_bonus

            # Create score breakdown
            from api.models.scoring_config import ScoringBreakdown
            breakdown = ScoringBreakdown(
                quote_id=quote_data['id'],
                bm25_raw=bm25_raw,
                bm25_normalized=bm25_normalized,
                field_score=field_score,
                field_matches=field_matches,
                phrase_bonus=phrase_bonus,
                final_score=final_score
            )

            quote_data['score'] = final_score
            quote_data['score_breakdown'] = breakdown
            quotes.append(quote_data)

        quotes.sort(key=lambda x: x['score'], reverse=True)
        return quotes

    def _calculate_field_scores(self, quote_data: Dict[str, Any], query: str, field_weights) -> tuple[float, Dict[str, float]]:
        """Calculate field-specific bonuses for a quote."""
        if not field_weights or not query:
            return 0.0, {}

        field_score = 0.0
        field_matches = {}
        query_lower = query.lower()

        # Field mappings for cleaner code
        field_mappings = [
            ('book_title', 'book_title'),
            ('book_authors', 'book_authors'),
            ('quote_keywords', 'quote_keywords'),
            ('book_keywords', 'book_keywords'),
            ('themes', 'themes'),
            ('summary', 'summary'),
            ('book_type', 'type'),
            ('publisher', 'publisher'),
            ('journal', 'journal')
        ]

        for data_field, weight_field in field_mappings:
            if (quote_data.get(data_field) and
                query_lower in quote_data[data_field].lower()):
                weight = getattr(field_weights, weight_field, 0)
                field_score += weight
                field_matches[weight_field] = weight

        return field_score, field_matches

    def _contains_exact_phrase(self, text: str, phrase: str) -> bool:
        """Check if text contains the exact phrase (case-insensitive)."""
        if not text or not phrase:
            return False

        escaped_phrase = re.escape(phrase)
        pattern = r'\b' + escaped_phrase + r'\b'
        return bool(re.search(pattern, text, re.IGNORECASE))

    def _group_by_book(self, conn: sqlite3.Connection, quotes: List[Dict[str, Any]],
                      original_query: str = None) -> Dict[int, Dict[str, Any]]:
        """Group quotes by book and prepare book-level results."""
        book_results = {}
        book_ids = list(set(quote['book_id'] for quote in quotes))

        if not book_ids:
            return {}

        # Fetch book metadata with total quotes count
        placeholders = ','.join('?' * len(book_ids))
        book_sql = f"""
        SELECT b.id, b.title, b.authors, b.year, b.publisher, b.container, b.doi, b.issn,
               b.doc_keywords, b.doc_summary, b.source_path,
               COUNT(q.id) as total_quotes
        FROM books b
        LEFT JOIN quotes q ON b.id = q.book_id
        WHERE b.id IN ({placeholders})
        GROUP BY b.id, b.title, b.authors, b.year, b.publisher, b.container, b.doi, b.issn,
                 b.doc_keywords, b.doc_summary, b.source_path
        """

        cursor = conn.cursor()
        cursor.execute(book_sql, book_ids)
        book_rows = cursor.fetchall()
        books_lookup = {row['id']: dict(row) for row in book_rows}

        # Group quotes by book
        for quote in quotes:
            book_id = quote['book_id']

            if book_id not in book_results:
                book_metadata = books_lookup.get(book_id, {})
                book_results[book_id] = {
                    "book": book_metadata,
                    "hits_count": 0,
                    "top_quotes": [],
                    "total_book_quotes": book_metadata.get('total_quotes', 0)
                }

            book_results[book_id]["hits_count"] += 1

            # Keep only top 5 quotes per book
            if len(book_results[book_id]["top_quotes"]) < 5:
                quote_response = {
                    "id": quote['id'],
                    "quote_text": quote['quote_text'],
                    "page": quote['page'],
                    "keywords": quote['keywords'],
                    "score": round(quote['score'], 2)
                }
                book_results[book_id]["top_quotes"].append(quote_response)

        return book_results

    def _group_by_book_with_breakdown(self, conn: sqlite3.Connection, quotes: List[Dict[str, Any]],
                                     original_query: str = None) -> Dict[int, Dict[str, Any]]:
        """Group quotes by book with score breakdown."""
        book_results = {}
        book_ids = list(set(quote['book_id'] for quote in quotes))

        if not book_ids:
            return {}

        # Fetch book metadata
        placeholders = ','.join('?' * len(book_ids))
        book_sql = f"""
        SELECT b.id, b.title, b.authors, b.year, b.publisher, b.container, b.doi, b.issn,
               b.doc_keywords, b.doc_summary, b.source_path,
               COUNT(q.id) as total_quotes
        FROM books b
        LEFT JOIN quotes q ON b.id = q.book_id
        WHERE b.id IN ({placeholders})
        GROUP BY b.id, b.title, b.authors, b.year, b.publisher, b.container, b.doi, b.issn,
                 b.doc_keywords, b.doc_summary, b.source_path
        """

        cursor = conn.cursor()
        cursor.execute(book_sql, book_ids)
        book_rows = cursor.fetchall()
        books_lookup = {row['id']: dict(row) for row in book_rows}

        # Group quotes by book
        for quote in quotes:
            book_id = quote['book_id']

            if book_id not in book_results:
                book_metadata = books_lookup.get(book_id, {})
                book_results[book_id] = {
                    "book": book_metadata,
                    "hits_count": 0,
                    "top_quotes": [],
                    "total_book_quotes": book_metadata.get('total_quotes', 0)
                }

            book_results[book_id]["hits_count"] += 1

            # Keep only top 5 quotes per book
            if len(book_results[book_id]["top_quotes"]) < 5:
                breakdown = quote['score_breakdown']
                breakdown.final_score = quote['score']

                quote_response = {
                    "id": quote['id'],
                    "quote_text": quote['quote_text'],
                    "page": quote['page'],
                    "keywords": quote['quote_keywords'],
                    "score": round(breakdown.final_score, 2),
                    "score_breakdown": breakdown
                }
                book_results[book_id]["top_quotes"].append(quote_response)

        return book_results

    def _generate_basic_citation(self, row: sqlite3.Row) -> str:
        """Generate a basic citation if ISO690 is not available."""
        parts = []

        if row['authors']:
            parts.append(row['authors'])
        if row['title']:
            parts.append(f'"{row["title"]}"')
        if row['journal']:
            parts.append(f"<i>{row['journal']}</i>")
        elif row['publisher']:
            parts.append(row['publisher'])
        if row['year']:
            parts.append(str(row['year']))
        if row['page']:
            parts.append(f"p. {row['page']}")

        return ". ".join(parts) + "." if parts else "Citation unavailable"


# Global scorer instance
scorer = QuoteScorer()