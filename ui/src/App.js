import React, { useState, useCallback, useEffect } from 'react';
import './index.css';

const API_URL = process.env.REACT_APP_API_URL || '/api';

// Helper function to highlight search terms in text
const highlightSearchTerms = (text, query) => {
  if (!query || !text) return text;

  // Extract terms from query, removing quotes and operators
  const terms = query
    .replace(/["']/g, '')
    .split(/\s+AND\s+|\s+OR\s+|\s+NOT\s+|\s+/i)
    .filter(term => term.length > 1 && !['AND', 'OR', 'NOT'].includes(term.toUpperCase()))
    .map(term => term.replace(/[*]/g, ''));

  if (terms.length === 0) return text;

  // Create regex pattern for all terms
  const pattern = new RegExp(`(${terms.map(term => term.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|')})`, 'gi');

  // Split text and wrap matches in bold
  const parts = text.split(pattern);
  return parts.map((part, index) => {
    if (terms.some(term => part.toLowerCase().includes(term.toLowerCase()))) {
      return <strong key={index} className="bg-yellow-200">{part}</strong>;
    }
    return part;
  });
};

// Debug: Show what API URL is being used
console.log('API_URL being used:', API_URL);
console.log('Environment variable:', process.env.REACT_APP_API_URL);

// Components
const SpinnerAscii = () => <span className="text-gray-500">[ .... ]</span>;

const Toast = ({ message, visible }) => {
  if (!visible) return null;
  return (
    <div className="fixed bottom-4 right-4 bg-black text-white px-3 py-2 rounded text-sm">
      {message}
    </div>
  );
};

const SearchBar = ({ query, setQuery, onSearch, loading }) => {
  const handleSubmit = (e) => {
    e.preventDefault();
    onSearch();
  };

  return (
    <div className="mb-8">
      <div className="mb-4">
        <label className="block text-sm font-bold uppercase tracking-wide mb-2">Search Query</label>
        <form onSubmit={handleSubmit} className="flex flex-col sm:flex-row gap-3">
          <input
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
        </form>
        <p className="text-sm text-gray-500 mt-2 italic">
          Tip: Use "quotes" for exact phrase matching
        </p>
      </div>
    </div>
  );
};

const DetailsPanel = ({ book, onCopyCitation, query }) => (
  <div className="mt-4 p-4 bg-gray-50 rounded-lg">
    <h4 className="font-bold mb-3">Book Details</h4>
    <div className="space-y-2 text-sm">
      <div>
        <span className="font-semibold text-gray-600">Author:</span> {highlightSearchTerms((book.authors || "Unknown author").replace(/;/g, ', '), query)}
      </div>
      <div>
        <span className="font-semibold text-gray-600">Title:</span> {highlightSearchTerms(book.title || "Unknown title", query)}
      </div>
      <div>
        <span className="font-semibold text-gray-600">Edition:</span> {highlightSearchTerms(book.publisher || "Unknown edition", query)}
      </div>
      <div>
        <span className="font-semibold text-gray-600">City:</span> Unknown city
      </div>
      <div>
        <span className="font-semibold text-gray-600">Publisher:</span> {highlightSearchTerms(book.publisher || "Unknown publisher", query)}
      </div>
      <div>
        <span className="font-semibold text-gray-600">Date:</span> {highlightSearchTerms(book.year?.toString() || "Unknown date", query)}
      </div>
      <div>
        <span className="font-semibold text-gray-600">ISBN:</span> {highlightSearchTerms(book.isbn || "Unknown ISBN", query)}
      </div>
      <div>
        <span className="font-semibold text-gray-600">Summary:</span>
        <div className="text-gray-800 mt-1">{highlightSearchTerms(book.summary || "Unknown summary", query)}</div>
      </div>
      <div>
        <span className="font-semibold text-gray-600">Keywords:</span> {highlightSearchTerms(book.keywords || "No keywords", query)}
      </div>
      <div>
        <span className="font-semibold text-gray-600">Journal:</span> {highlightSearchTerms(book.journal || "N/A", query)}
      </div>
      <div>
        <span className="font-semibold text-gray-600">DOI:</span> {highlightSearchTerms(book.doi || "N/A", query)}
      </div>
      <div>
        <span className="font-semibold text-gray-600">Total quotes in database:</span> {book.total_quotes || "Unknown"}
      </div>
    </div>
    <div className="flex justify-between items-center mt-3">
      <div></div>
      <button
        onClick={() => onCopyCitation(book)}
        className="text-sm text-gray-600 hover:text-black underline transition-colors"
      >
        [copy citation]
      </button>
    </div>
  </div>
);

const QuotesPanel = ({ bookId, relevant, query, onCopy, onCountUpdate }) => {
  const [quotes, setQuotes] = useState([]);
  const [loading, setLoading] = useState(false);
  const [offset, setOffset] = useState(0);
  const [hasMore, setHasMore] = useState(false);
  const [totalCount, setTotalCount] = useState(0);

  const loadQuotes = useCallback(async (newOffset) => {
    setLoading(true);
    try {
      const params = new URLSearchParams({
        relevant: relevant.toString(),
        offset: newOffset.toString(),
        limit: '10'
      });
      if (relevant && query) {
        params.set('q', query);
      }

      const response = await fetch(`${API_URL}/books/${bookId}/quotes?${params}`);
      const data = await response.json();

      if (newOffset === 0) {
        setQuotes(data.quotes);
      } else {
        setQuotes(prev => [...prev, ...data.quotes]);
      }

      setHasMore(data.has_more);
      setTotalCount(data.total_count);
      setOffset(newOffset);

      // Update parent component with accurate count
      if (onCountUpdate && relevant) {
        onCountUpdate(data.total_count);
      }
    } catch (error) {
      console.error('Error loading quotes:', error);
    } finally {
      setLoading(false);
    }
  }, [bookId, relevant, query]);

  useEffect(() => {
    loadQuotes(0); // Reset and load from beginning
  }, [loadQuotes]);

  const handleExpand = () => {
    loadQuotes(offset + 10);
  };

  return (
    <div className="mt-4 p-4 bg-gray-50 rounded-lg">
      <h4 className="font-bold mb-3">
        {relevant ? `Relevant Quotes (${totalCount})` : `All Quotes (${totalCount})`}
      </h4>

      {loading && offset === 0 ? (
        <SpinnerAscii />
      ) : (
        <div className="space-y-4">
          {quotes.map((quote, idx) => (
            <div key={quote.id} className="border-b border-gray-200 pb-3 last:border-b-0">
              <blockquote className="text-gray-800 mb-2">
                <span className="text-2xl text-gray-300 mr-1">"</span>
                <span className="italic">{highlightSearchTerms(quote.quote_text, query)}</span>
                <span className="text-2xl text-gray-300 ml-1">"</span>
              </blockquote>
              <div className="flex justify-between items-center">
                {(quote.page || quote.section) && (
                  <div className="text-sm text-gray-500">
                    {quote.page && <span className="font-semibold">p. {quote.page}</span>}
                    {quote.page && quote.section && ' • '}
                    {quote.section && quote.section}
                  </div>
                )}
                <button
                  onClick={() => onCopy(quote)}
                  className="text-sm text-gray-600 hover:text-black underline transition-colors"
                >
                  [copy]
                </button>
              </div>
            </div>
          ))}

          {hasMore && (
            <div className="text-center pt-2">
              <button
                onClick={handleExpand}
                disabled={loading}
                className="text-sm font-bold text-gray-600 hover:text-black underline transition-colors disabled:opacity-50"
              >
                {loading ? <SpinnerAscii /> : 'expand (+10 more)'}
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

const ScorePanel = ({ book, query, bookPosition, searchResult }) => {
  const [scoreData, setScoreData] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const fetchScoreData = async () => {
      if (!query.trim()) return;

      setLoading(true);
      try {
        // Get current tuning configuration
        const configResponse = await fetch(`${API_URL}/tuning/config`);
        const configData = await configResponse.json();

        // Use the search result passed as prop if available
        let bookResult = searchResult;

        // If not available, fetch it
        if (!bookResult) {
          const response = await fetch(
            `${API_URL}/search?q=${encodeURIComponent(query)}&offset=0&limit=100`
          );
          const searchData = await response.json();

          // Find this book in the search results
          bookResult = searchData.results?.find(result =>
            result.book.id === book.id
          );
        }

        if (bookResult && bookResult.top_quotes && bookResult.top_quotes.length > 0) {
          // Get the top quote's score breakdown
          const topQuote = bookResult.top_quotes[0];
          const topQuoteScore = topQuote.score_breakdown || {};

          setScoreData({
            book: bookResult.book,
            hitsCount: bookResult.hits_count,
            topQuotes: bookResult.top_quotes,
            totalBookQuotes: bookResult.total_book_quotes || 0,
            position: bookPosition,
            config: configData.config,
            scoreBreakdown: topQuoteScore,
            topQuoteScore: topQuote.score || 0
          });
        } else {
          setScoreData(null);
        }
      } catch (error) {
        console.error('Error fetching score data:', error);
        setScoreData(null);
      } finally {
        setLoading(false);
      }
    };

    fetchScoreData();
  }, [book, query, bookPosition, searchResult]);

  if (loading) {
    return (
      <div className="mt-4 p-4 bg-gray-50 rounded-lg">
        <h4 className="font-bold mb-3">Score Breakdown</h4>
        <div className="text-sm text-gray-500">Loading score data...</div>
      </div>
    );
  }

  if (!scoreData) {
    return (
      <div className="mt-4 p-4 bg-gray-50 rounded-lg">
        <h4 className="font-bold mb-3">Score Breakdown</h4>
        <div className="text-sm text-gray-500">No score data available for this query.</div>
      </div>
    );
  }

  return (
    <div className="mt-4 p-4 bg-gray-50 rounded-lg">
      <h4 className="font-bold mb-3">Why This Book Ranked Here</h4>
      <div className="space-y-4 text-sm">

        {/* Book Ranking Position */}
        <div className="bg-black text-white p-3 rounded">
          <div className="text-center">
            <div className="text-lg font-bold">Position #{scoreData.position || 'Unknown'}</div>
            <div className="text-sm">in search results</div>
          </div>
        </div>

        {/* Detailed Score Breakdown */}
        {scoreData.scoreBreakdown && (
          <div className="bg-white p-3 rounded border">
            <h5 className="font-semibold mb-3 text-gray-700">Score Calculation Details</h5>

            {/* Book Performance Metrics */}
            <div className="mb-3 pb-2 border-b">
              <div className="font-semibold text-gray-600 mb-2">Book Performance</div>
              <div className="grid grid-cols-2 gap-4 text-xs">
                <div>
                  <span className="text-gray-500">Total Quotes:</span>
                  <div className=" font-bold">{scoreData.totalBookQuotes || 'N/A'}</div>
                </div>
                <div>
                  <span className="text-gray-500">Relevant Quotes:</span>
                  <div className=" font-bold">{scoreData.hitsCount || 0}</div>
                </div>
                <div>
                  <span className="text-gray-500">Top Quote Score:</span>
                  <div className=" font-bold">{scoreData.topQuoteScore?.toFixed(4) || '0.0000'}</div>
                </div>
                <div>
                  <span className="text-gray-500">Match Rate:</span>
                  <div className=" font-bold">
                    {scoreData.totalBookQuotes > 0
                      ? `${((scoreData.hitsCount / scoreData.totalBookQuotes) * 100).toFixed(1)}%`
                      : 'N/A'}
                  </div>
                </div>
              </div>
            </div>

            {/* BM25 Score */}
            <div className="mb-3 pb-2 border-b">
              <div className="font-semibold text-gray-600 mb-1">BM25 Text Relevance</div>
              <div className="text-xs">
                <span className="text-gray-500">Score (×{scoreData.config?.bm25_weight || 1.0}):</span>
                <span className=" font-bold text-blue-600 ml-2">{scoreData.scoreBreakdown.bm25_normalized?.toFixed(4) || '0.0000'}</span>
              </div>
            </div>

            {/* Field Scores */}
            <div className="mb-3 pb-2 border-b">
              <div className="font-semibold text-gray-600 mb-1">Field Matching Score</div>
              <div className="text-xs">
                <span className="text-gray-500">Total weighted:</span>
                <span className=" font-bold ml-2">{scoreData.scoreBreakdown.field_score?.toFixed(4) || '0.0000'}</span>
              </div>

              {/* Field Matches Breakdown */}
              {scoreData.scoreBreakdown?.field_matches && Object.keys(scoreData.scoreBreakdown.field_matches).length > 0 ? (
                <div className="mt-2 p-2 bg-green-50 rounded">
                  <div className="text-xs font-semibold text-green-700 mb-1">Fields That Matched:</div>
                  <div className="space-y-1">
                    {Object.entries(scoreData.scoreBreakdown.field_matches).map(([field, weightedValue]) => (
                      <div key={field} className="flex justify-between text-xs">
                        <span className="text-gray-700 font-medium">{field.replace(/_/g, ' ')}:</span>
                        <span className=" font-bold text-green-700">+{weightedValue?.toFixed(3)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <div className="mt-2 p-2 bg-gray-100 rounded">
                  <div className="text-xs text-gray-500">No field matches for this query</div>
                </div>
              )}
            </div>

            {/* Phrase Bonus */}
            <div className="mb-3 pb-2 border-b">
              <div className="font-semibold text-gray-600 mb-1">Phrase Match Bonus</div>
              <div className="text-xs">
                <span className="text-gray-500">Weighted Value:</span>
                <span className=" font-bold ml-2">
                  {scoreData.scoreBreakdown.phrase_bonus > 0
                    ? <span className="text-orange-600">+{scoreData.scoreBreakdown.phrase_bonus?.toFixed(4)}</span>
                    : <span className="text-gray-400">0.0000</span>}
                </span>
              </div>
            </div>

            {/* Final Score Calculation */}
            <div className="mt-3 pt-2 bg-gray-50 p-2 rounded">
              <div className="text-center">
                <div className="text-xs text-gray-600 mb-2">Score Components</div>
                <div className="text-xs  space-y-1">
                  <div>BM25: {scoreData.scoreBreakdown.bm25_normalized?.toFixed(4) || '0.0000'}</div>
                  <div>Fields: {scoreData.scoreBreakdown.field_score?.toFixed(4) || '0.0000'}</div>
                  {scoreData.scoreBreakdown.phrase_bonus > 0 && (
                    <div>Phrase: {scoreData.scoreBreakdown.phrase_bonus?.toFixed(4) || '0.0000'}</div>
                  )}
                  <div className="border-t pt-1 mt-1"></div>
                </div>
                <div className="text-2xl font-bold text-black">
                  Total: {scoreData.scoreBreakdown.final_score?.toFixed(4) || '0.0000'}
                </div>
              </div>
            </div>
          </div>
        )}

      </div>
    </div>
  );
};

const BookCard = ({
  book,
  hitsCount,
  topQuotes,
  query,
  expandedBookId,
  expandedPanel,
  onPanelToggle,
  onCopy,
  onExportCitation,
  onCopyCitation,
  expertMode
}) => {
  const isExpanded = expandedBookId === book.id;
  const [totalQuoteCount, setTotalQuoteCount] = useState(null);
  const [relevantQuoteCount, setRelevantQuoteCount] = useState(hitsCount);

  // Fetch total quote count for this book
  useEffect(() => {
    const fetchTotalCount = async () => {
      try {
        const response = await fetch(`${API_URL}/books/${book.id}/quotes?relevant=false&limit=1`);
        const data = await response.json();
        setTotalQuoteCount(data.total_count);
      } catch (error) {
        console.error('Error fetching total quote count:', error);
      }
    };

    fetchTotalCount();
  }, [book.id]);

  const handlePanelToggle = (panel) => {
    if (isExpanded && expandedPanel === panel) {
      // Close if same panel is clicked
      onPanelToggle(null, null);
    } else {
      // Open this panel (closes any other open panel)
      onPanelToggle(book.id, panel);
    }
  };

  return (
    <div className="border border-gray-200 rounded-2xl p-4 shadow-sm hover:shadow-md transition-shadow bg-white">
      {/* Header */}
      <div className="mb-3">
        <h3 className="font-bold text-lg underline decoration-gray-300 underline-offset-2">
          {book.title || 'Unknown title'}
        </h3>
        <p className="text-gray-700">
          {(book.authors || 'Unknown author').replace(/;/g, ',')}
        </p>
        <div className="text-sm text-gray-600 mt-1">
          <div>
            {book.themes || 'Unknown theme'} — {book.type || 'Unknown type'} — {book.year || 'Unknown date'}
          </div>
        </div>
      </div>


      {/* Action buttons */}
      <div className="flex flex-wrap gap-2 mb-2">
        <button
          onClick={() => handlePanelToggle('details')}
          className="text-xs px-3 py-1 border border-gray-200 rounded-2xl hover:bg-gray-50 focus:ring-2 focus:ring-gray-300 transition-colors"
          aria-label={`Show details for ${book.title}`}
        >
          Details
        </button>
        <button
          onClick={() => handlePanelToggle('relevant')}
          className="text-xs px-3 py-1 border border-gray-200 rounded-2xl hover:bg-gray-50 focus:ring-2 focus:ring-gray-300 transition-colors"
          aria-label={`Show relevant quotes for ${book.title}`}
        >
          Relevant quotes ({relevantQuoteCount})
        </button>
        <button
          onClick={() => handlePanelToggle('all')}
          className="text-xs px-3 py-1 border border-gray-200 rounded-2xl hover:bg-gray-50 focus:ring-2 focus:ring-gray-300 transition-colors"
          aria-label={`Show all quotes for ${book.title}`}
        >
          All quotes {totalQuoteCount !== null ? `(${totalQuoteCount})` : '(loading...)'}
        </button>
        {expertMode && (
          <button
            onClick={() => handlePanelToggle('score')}
            className="text-xs px-3 py-1 bg-black text-white rounded-2xl hover:bg-gray-800 focus:ring-2 focus:ring-gray-300 transition-colors"
            aria-label={`Show score breakdown for ${book.title}`}
          >
            Score
          </button>
        )}
      </div>

      {/* Expanded panels */}
      {isExpanded && expandedPanel === 'details' && (
        <DetailsPanel book={book} onCopyCitation={onCopyCitation} query={query} />
      )}

      {isExpanded && expandedPanel === 'relevant' && (
        <QuotesPanel
          bookId={book.id}
          relevant={true}
          query={query}
          onCopy={(quote) => onCopy(quote, book)}
          onCountUpdate={setRelevantQuoteCount}
        />
      )}

      {isExpanded && expandedPanel === 'all' && (
        <QuotesPanel
          bookId={book.id}
          relevant={false}
          query={query}
          onCopy={(quote) => onCopy(quote, book)}
        />
      )}

      {isExpanded && expandedPanel === 'score' && (
        <ScorePanel book={book} query={query} bookPosition={book.position} searchResult={book.searchResult} />
      )}
    </div>
  );
};

const ResultsList = ({
  results,
  total,
  currentPage,
  totalPages,
  onPageChange,
  query,
  expandedBookId,
  expandedPanel,
  onPanelToggle,
  onCopy,
  onExportCitation,
  onCopyCitation,
  expertMode
}) => {
  if (results.length === 0) {
    return (
      <div className="text-center py-12">
        <p className="text-lg text-gray-600">No matches found</p>
        <p className="text-sm text-gray-500 mt-2 italic">
          Try using "quotes" for exact phrase matching
        </p>
      </div>
    );
  }

  return (
    <>
      {/* Results header */}
      <div className="mb-6 pb-2 border-b border-gray-300">
        <span className="font-bold">{total}</span>
        <span className="text-gray-600"> result{total !== 1 ? 's' : ''} found</span>
        {totalPages > 1 && (
          <span className="text-gray-500 float-right">
            Page <span className="font-bold">{currentPage}</span> of {totalPages}
          </span>
        )}
      </div>

      {/* Book cards */}
      <div className="space-y-6">
        {results.map((result, index) => (
          <BookCard
            key={result.book.id}
            book={{...result.book, position: (currentPage - 1) * 10 + index + 1, searchResult: result}}
            hitsCount={result.hits_count}
            topQuotes={result.top_quotes}
            query={query}
            expandedBookId={expandedBookId}
            expandedPanel={expandedPanel}
            onPanelToggle={onPanelToggle}
            onCopy={onCopy}
            onExportCitation={onExportCitation}
            onCopyCitation={onCopyCitation}
            expertMode={expertMode}
          />
        ))}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="mt-8 pt-6 border-t border-gray-300 flex justify-center items-center gap-4">
          <button
            onClick={() => onPageChange(currentPage - 1)}
            disabled={currentPage === 1}
            className="font-bold text-gray-700 hover:text-black disabled:text-gray-400 disabled:cursor-not-allowed transition-colors"
          >
            [prev]
          </button>

          <span className="px-4 py-2 bg-gray-100 font-bold">
            {currentPage} / {totalPages}
          </span>

          <button
            onClick={() => onPageChange(currentPage + 1)}
            disabled={currentPage === totalPages}
            className="font-bold text-gray-700 hover:text-black disabled:text-gray-400 disabled:cursor-not-allowed transition-colors"
          >
            [next]
          </button>
        </div>
      )}
    </>
  );
};

function App() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [total, setTotal] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [expandedBookId, setExpandedBookId] = useState(null);
  const [expandedPanel, setExpandedPanel] = useState(null);
  const [toast, setToast] = useState({ message: '', visible: false });
  const [expertMode, setExpertMode] = useState(false);
  const [clickSequence, setClickSequence] = useState([]);

  // Expert mode activation: Click on title 5 times within 3 seconds
  const handleTitleClick = () => {
    const now = Date.now();
    const newSequence = [...clickSequence, now].filter(timestamp => now - timestamp < 3000);
    setClickSequence(newSequence);

    // Debug log
    console.log('Title clicked, sequence length:', newSequence.length);

    if (newSequence.length >= 5) {
      setExpertMode(!expertMode);
      setToast({
        message: expertMode ? '[expert mode disabled]' : '[expert mode enabled]',
        visible: true
      });
      setTimeout(() => setToast({ message: '', visible: false }), 2000);
      setClickSequence([]);
    }
  };

  const BOOKS_PER_PAGE = 10;
  const totalPages = Math.ceil(total / BOOKS_PER_PAGE);

  const handleSearch = async () => {
    if (!query.trim()) return;

    setLoading(true);
    setCurrentPage(1);
    setExpandedBookId(null);
    setExpandedPanel(null);

    try {
      const offset = 0;
      const response = await fetch(
        `${API_URL}/search?q=${encodeURIComponent(query)}&offset=${offset}&limit=${BOOKS_PER_PAGE}`
      );
      const data = await response.json();

      if (response.ok) {
        setResults(data.results || []);
        setTotal(data.total || 0);
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
    setExpandedBookId(null);
    setExpandedPanel(null);

    const offset = (newPage - 1) * BOOKS_PER_PAGE;
    try {
      const response = await fetch(
        `${API_URL}/search?q=${encodeURIComponent(query)}&offset=${offset}&limit=${BOOKS_PER_PAGE}`
      );
      const data = await response.json();

      if (response.ok) {
        setResults(data.results || []);
      }
    } catch (error) {
      console.error('Pagination error:', error);
    } finally {
      setLoading(false);
    }
  };

  const handlePanelToggle = (bookId, panel) => {
    setExpandedBookId(bookId);
    setExpandedPanel(panel);
  };

  const handleCopy = async (quote, book) => {
    const authors = (book.authors || 'Unknown').replace(/;/g, ',');
    const text = `"${quote.quote_text}" — ${book.title}, ${authors} (${book.year || 'n.d.'}), p. ${quote.page || 'n/a'}`;

    try {
      // Try modern clipboard API first
      if (navigator.clipboard && navigator.clipboard.writeText) {
        await navigator.clipboard.writeText(text);
        setToast({ message: '[copied]', visible: true });
        setTimeout(() => setToast({ message: '', visible: false }), 1500);
        return;
      }

      // Fallback method for older browsers or HTTPS issues
      const textArea = document.createElement('textarea');
      textArea.value = text;
      textArea.style.position = 'fixed';
      textArea.style.left = '-999999px';
      textArea.style.top = '-999999px';
      document.body.appendChild(textArea);
      textArea.focus();
      textArea.select();

      try {
        document.execCommand('copy');
        setToast({ message: '[copied via fallback]', visible: true });
        setTimeout(() => setToast({ message: '', visible: false }), 1500);
      } catch (fallbackError) {
        console.error('Fallback copy failed:', fallbackError);
        setToast({ message: '[copy failed]', visible: true });
        setTimeout(() => setToast({ message: '', visible: false }), 2000);
      } finally {
        document.body.removeChild(textArea);
      }
    } catch (error) {
      console.error('Copy error:', error);
      setToast({ message: '[copy failed]', visible: true });
      setTimeout(() => setToast({ message: '', visible: false }), 2000);
    }
  };

  const handleExportCitation = async (book) => {
    try {
      const response = await fetch(`${API_URL}/books/${book.id}/citation`);
      const data = await response.json();

      const blob = new Blob([data.citation], { type: 'text/plain' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `citation_${book.id}.txt`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);

      setToast({ message: '[exported]', visible: true });
      setTimeout(() => setToast({ message: '', visible: false }), 1500);
    } catch (error) {
      console.error('Export error:', error);
    }
  };

  const handleCopyCitation = async (book) => {
    try {
      const response = await fetch(`${API_URL}/books/${book.id}/citation`);
      const data = await response.json();

      // Try modern clipboard API first
      if (navigator.clipboard && navigator.clipboard.writeText) {
        try {
          await navigator.clipboard.writeText(data.citation);
          setToast({ message: '[citation copied]', visible: true });
          setTimeout(() => setToast({ message: '', visible: false }), 1500);
          return;
        } catch (clipboardError) {
          console.warn('Clipboard API failed, trying fallback:', clipboardError);
        }
      }

      // Fallback method for older browsers or HTTPS issues
      const textArea = document.createElement('textarea');
      textArea.value = data.citation;
      textArea.style.position = 'fixed';
      textArea.style.left = '-999999px';
      textArea.style.top = '-999999px';
      document.body.appendChild(textArea);
      textArea.focus();
      textArea.select();

      try {
        document.execCommand('copy');
        setToast({ message: '[citation copied via fallback]', visible: true });
        setTimeout(() => setToast({ message: '', visible: false }), 1500);
      } catch (fallbackError) {
        console.error('Fallback copy failed:', fallbackError);
        setToast({ message: '[copy failed - please copy manually]', visible: true });
        setTimeout(() => setToast({ message: '', visible: false }), 3000);
      } finally {
        document.body.removeChild(textArea);
      }
    } catch (error) {
      console.error('Copy citation error:', error);
      setToast({ message: '[copy failed - API error]', visible: true });
      setTimeout(() => setToast({ message: '', visible: false }), 1500);
    }
  };

  const handleImportTuning = () => {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.json';
    input.onchange = async (e) => {
      const file = e.target.files[0];
      if (!file) return;

      try {
        const text = await file.text();
        const tuningData = JSON.parse(text);

        // Validate the tuning data structure
        if (!tuningData.config || !tuningData.config.field_weights) {
          throw new Error('Invalid tuning file format');
        }

        // Apply the tuning configuration
        await fetch(`${API_URL}/tuning/config`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(tuningData.config)
        });

        setToast({ message: '[tuning imported]', visible: true });
        setTimeout(() => setToast({ message: '', visible: false }), 2000);
      } catch (error) {
        console.error('Import error:', error);
        setToast({ message: '[import failed]', visible: true });
        setTimeout(() => setToast({ message: '', visible: false }), 2000);
      }
    };
    input.click();
  };


  return (
    <div className="min-h-screen bg-white text-black  p-4 max-w-6xl mx-auto">
      {/* Header */}
      <div className="mb-8 pb-6 border-b-2 border-black">
        <div className="flex justify-between items-start">
          <div>
            <h1
              className="text-2xl font-bold mb-2 cursor-pointer select-none hover:text-gray-700 transition-colors"
              onClick={handleTitleClick}
              title={`Click 5 times quickly to toggle expert mode (${clickSequence.length}/5)`}
              style={{ userSelect: 'none' }}
            >
              THE LIBRARY {clickSequence.length > 0 && clickSequence.length < 5 && (
                <span className="text-xs text-gray-400">({clickSequence.length}/5)</span>
              )}
            </h1>
            <p className="text-gray-600 italic">A Black Mountain Retcon Tool</p>
            {expertMode && <p className="text-xs text-red-600 ">API: {API_URL} - UPDATED</p>}
          </div>

          <div className="flex flex-col sm:flex-row items-start sm:items-center gap-2 sm:gap-3">
            {expertMode && (
              <div className="flex flex-wrap gap-2">
                <a
                  href="/tuning"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm px-3 py-1 border border-blue-300 rounded hover:bg-blue-50 transition-colors text-blue-700"
                >
                  Tuning
                </a>
                <button
                  onClick={handleImportTuning}
                  className="text-sm px-3 py-1 border border-gray-300 rounded hover:bg-gray-50 transition-colors"
                >
                  Import
                </button>
                <a
                  href="/reload"
                  className="text-sm px-3 py-1 border border-purple-300 bg-purple-50 text-purple-700 rounded hover:bg-purple-100 transition-colors"
                >
                  Reload Data
                </a>
              </div>
            )}

          </div>
        </div>
      </div>

      {/* Search */}
      <SearchBar
        query={query}
        setQuery={setQuery}
        onSearch={handleSearch}
        loading={loading}
      />


      {/* Results */}
      {loading ? (
        <div className="text-center py-8">
          <SpinnerAscii />
        </div>
      ) : (
        <ResultsList
          results={results}
          total={total}
          currentPage={currentPage}
          totalPages={totalPages}
          onPageChange={handlePageChange}
          query={query}
          expandedBookId={expandedBookId}
          expandedPanel={expandedPanel}
          onPanelToggle={handlePanelToggle}
          onCopy={handleCopy}
          onExportCitation={handleExportCitation}
          onCopyCitation={handleCopyCitation}
          expertMode={expertMode}
        />
      )}

      {/* Footer */}
      <div className="mt-16 pt-6 border-t-2 border-gray-200">
        <p className="text-sm text-gray-500 text-center italic">
          Retcon Black Mountain
        </p>
      </div>

      {/* Toast */}
      <Toast message={toast.message} visible={toast.visible} />
    </div>
  );
}

export default App;