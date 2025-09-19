import React, { useState, useEffect, useRef } from 'react';
import './index.css';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

function App() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [total, setTotal] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [expandedBooks, setExpandedBooks] = useState({});
  const [quoteLimits, setQuoteLimits] = useState({});
  const searchInputRef = useRef(null);

  const BOOKS_PER_PAGE = 10;
  const QUOTES_PER_EXPAND = 10;

  useEffect(() => {
    // Setup keyboard navigation
    const handleKeyDown = (e) => {
      if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
        e.preventDefault();
        navigateFocus(e.key === 'ArrowDown' ? 1 : -1);
      }
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, []);

  const navigateFocus = (direction) => {
    const focusableElements = Array.from(
      document.querySelectorAll('input, button, [tabindex="0"]')
    );
    const currentIndex = focusableElements.indexOf(document.activeElement);
    const nextIndex = currentIndex + direction;
    if (nextIndex >= 0 && nextIndex < focusableElements.length) {
      focusableElements[nextIndex].focus();
    }
  };

  const handleSearch = async (e) => {
    e?.preventDefault();
    if (!query.trim()) return;

    setLoading(true);
    setCurrentPage(1);

    try {
      const offset = 0;
      const response = await fetch(
        `${API_URL}/search?q=${encodeURIComponent(query)}&offset=${offset}&limit=${BOOKS_PER_PAGE}`
      );
      const data = await response.json();

      if (response.ok) {
        setResults(data.results || []);
        setTotal(data.total || 0);
        setExpandedBooks({});
        setQuoteLimits({});
      } else {
        setResults([]);
        setTotal(0);
      }
    } catch (error) {
      console.error('Search error:', error);
      setResults([]);
      setTotal(0);
    } finally {
      setLoading(false);
    }
  };

  const handlePageChange = async (newPage) => {
    setLoading(true);
    setCurrentPage(newPage);

    const offset = (newPage - 1) * BOOKS_PER_PAGE;
    try {
      const response = await fetch(
        `${API_URL}/search?q=${encodeURIComponent(query)}&offset=${offset}&limit=${BOOKS_PER_PAGE}`
      );
      const data = await response.json();

      if (response.ok) {
        setResults(data.results || []);
        setExpandedBooks({});
        setQuoteLimits({});
      }
    } catch (error) {
      console.error('Pagination error:', error);
    } finally {
      setLoading(false);
    }
  };

  const toggleBookExpanded = (bookId) => {
    setExpandedBooks(prev => ({
      ...prev,
      [bookId]: !prev[bookId]
    }));
    if (!quoteLimits[bookId]) {
      setQuoteLimits(prev => ({
        ...prev,
        [bookId]: QUOTES_PER_EXPAND
      }));
    }
  };

  const expandMoreQuotes = (bookId) => {
    setQuoteLimits(prev => ({
      ...prev,
      [bookId]: (prev[bookId] || QUOTES_PER_EXPAND) + QUOTES_PER_EXPAND
    }));
  };

  const copyQuote = (quote, book) => {
    const text = `"${quote.quote_text}" — ${book.title}, ${book.authors || 'Unknown'} (${book.year || 'n.d.'}), p. ${quote.page || 'n/a'}`;
    navigator.clipboard.writeText(text);
  };

  const totalPages = Math.ceil(total / BOOKS_PER_PAGE);

  return (
    <div className="min-h-screen bg-white text-black font-mono p-4 max-w-6xl mx-auto">
      {/* Header */}
      <div className="mb-8 pb-6 border-b-2 border-black">
        <h1 className="text-2xl font-bold mb-2">THE LIBRARY</h1>
        <p className="text-gray-600 italic">Semantic Quote Search Server</p>
      </div>

      {/* Search Form */}
      <form onSubmit={handleSearch} className="mb-8">
        <div className="mb-4">
          <label className="block text-sm font-bold uppercase tracking-wide mb-2">Search Query</label>
          <div className="flex flex-col sm:flex-row gap-3">
            <input
              ref={searchInputRef}
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Enter search terms..."
              className="flex-1 border-2 border-gray-300 p-3 bg-white focus:border-black transition-colors"
              disabled={loading}
            />
            <button
              type="submit"
              disabled={loading || !query.trim()}
              className="px-6 py-3 bg-black text-white font-bold hover:bg-gray-800 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
            >
              {loading ? 'SEARCHING...' : 'SEARCH'}
            </button>
          </div>
          <p className="text-sm text-gray-500 mt-2 italic">
            Tip: Use "quotes" for exact phrase matching
          </p>
        </div>
      </form>

      {/* Results */}
      {!loading && results.length === 0 && query && (
        <div className="text-center py-12">
          <p className="text-lg text-gray-600">No matches found</p>
          <p className="text-sm text-gray-500 mt-2 italic">Try using "quotes" for exact phrase matching</p>
        </div>
      )}

      {results.length > 0 && (
        <>
          <div className="mb-6 pb-2 border-b border-gray-300">
            <span className="font-bold">{total}</span>
            <span className="text-gray-600"> result{total !== 1 ? 's' : ''} found</span>
            {totalPages > 1 && (
              <span className="text-gray-500 float-right">
                Page <span className="font-bold">{currentPage}</span> of {totalPages}
              </span>
            )}
          </div>

          <div className="space-y-4">
            {results.map((result) => (
              <div key={result.book.id} className="border-l-4 border-gray-900 mb-4 shadow-sm hover:shadow-md transition-shadow bg-white">
                {/* Book Header */}
                <div className="p-4 hover:bg-gray-50 transition-colors cursor-pointer"
                     onClick={() => toggleBookExpanded(result.book.id)}>
                  <div className="flex items-start">
                    <button
                      className="mr-3 text-gray-500 hover:text-black transition-colors"
                      aria-expanded={expandedBooks[result.book.id]}
                      aria-label={`Toggle quotes for ${result.book.title}`}
                    >
                      {expandedBooks[result.book.id] ? '▼' : '▶'}
                    </button>
                    <div className="flex-1">
                      <h3 className="font-bold text-lg underline decoration-gray-300 underline-offset-2">
                        {result.book.title || 'Untitled'}
                      </h3>
                      {result.book.authors && (
                        <p className="text-gray-700 mt-1">
                          <span className="text-gray-500">by</span> {result.book.authors}
                        </p>
                      )}
                      {result.book.year && (
                        <span className="text-sm text-gray-500">({result.book.year})</span>
                      )}
                      <p className="text-sm mt-2">
                        <span className="font-bold text-black">{result.hits_count}</span>
                        <span className="text-gray-600"> relevant quote{result.hits_count !== 1 ? 's' : ''}</span>
                      </p>
                    </div>
                  </div>
                </div>

                {/* Quotes */}
                {expandedBooks[result.book.id] && (
                  <div className="border-t border-gray-300">
                    {result.top_quotes
                      .slice(0, quoteLimits[result.book.id] || QUOTES_PER_EXPAND)
                      .map((quote, idx) => (
                      <div key={quote.id} className="p-4 border-b border-gray-100 last:border-b-0 hover:bg-gray-50">
                        <div className="flex items-start">
                          <div className="flex-1 pr-3">
                            <blockquote className="text-gray-800 mb-2">
                              <span className="text-2xl text-gray-300 mr-1">"</span>
                              <span className="italic">{quote.quote_text}</span>
                              <span className="text-2xl text-gray-300 ml-1">"</span>
                            </blockquote>
                            {(quote.page || quote.section) && (
                              <div className="text-sm text-gray-500">
                                {quote.page && (
                                  <span className="font-semibold">p. {quote.page}</span>
                                )}
                                {quote.page && quote.section && ' • '}
                                {quote.section && `${quote.section}`}
                              </div>
                            )}
                          </div>
                          <button
                            onClick={(e) => { e.stopPropagation(); copyQuote(quote, result.book); }}
                            className="text-sm text-gray-600 hover:text-black underline transition-colors"
                            aria-label="Copy quote with citation"
                          >
                            copy
                          </button>
                        </div>
                      </div>
                    ))}

                    {result.top_quotes.length > (quoteLimits[result.book.id] || QUOTES_PER_EXPAND) && (
                      <div className="p-4 text-center border-t border-gray-200">
                        <button
                          onClick={(e) => { e.stopPropagation(); expandMoreQuotes(result.book.id); }}
                          className="text-sm font-bold text-gray-600 hover:text-black underline transition-colors"
                        >
                          Show {Math.min(
                            QUOTES_PER_EXPAND,
                            result.top_quotes.length - (quoteLimits[result.book.id] || QUOTES_PER_EXPAND)
                          )} more quotes
                        </button>
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="mt-8 pt-6 border-t border-gray-300 flex justify-center items-center gap-4">
              <button
                onClick={() => handlePageChange(currentPage - 1)}
                disabled={currentPage === 1}
                className="font-bold text-gray-700 hover:text-black disabled:text-gray-400 disabled:cursor-not-allowed transition-colors"
              >
                ← Previous
              </button>

              <span className="px-4 py-2 bg-gray-100 font-bold">
                {currentPage} / {totalPages}
              </span>

              <button
                onClick={() => handlePageChange(currentPage + 1)}
                disabled={currentPage === totalPages}
                className="font-bold text-gray-700 hover:text-black disabled:text-gray-400 disabled:cursor-not-allowed transition-colors"
              >
                Next →
              </button>
            </div>
          )}
        </>
      )}

      {/* Footer */}
      <div className="mt-16 pt-6 border-t-2 border-gray-200">
        <p className="text-sm text-gray-500 text-center italic">
          Optimized for Raspberry Pi 4 • Monospace Typography
        </p>
      </div>
    </div>
  );
}

export default App;