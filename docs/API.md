# The Library API Documentation

Complete API reference for The Library quote search system.

## Base URL

```
Local development: http://localhost:8000
Production: https://your-domain.com
```

## Authentication

Currently, the API does not require authentication. All endpoints are publicly accessible.

## Core Concepts

- **Books**: Bibliographic metadata for sources (title, authors, year, publisher, etc.)
- **Quotes**: Text excerpts extracted from books with page numbers and keywords
- **Searches**: FTS5-powered full-text search with BM25 ranking
- **Edits**: Direct database updates for correcting metadata

---

## Search Endpoints

### Search Quotes

Search for quotes using full-text search with BM25 ranking.

```http
GET /search
```

**Query Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `q` | string | Yes | - | Search query. Supports quoted phrases, AND/OR/NOT, prefix matching (*) |
| `offset` | integer | No | 0 | Pagination offset |
| `limit` | integer | No | 20 | Number of results per page (max 100) |

**Query Syntax:**

- **Exact phrases**: `"Black Mountain College"`
- **Boolean operators**: `education AND art`, `teaching OR learning`, `NOT obsolete`
- **Prefix matching**: `educat*` matches education, educational, educator
- **Combined**: `"Black Mountain" AND education*`

**Example Request:**

```bash
curl "http://localhost:8000/search?q=\"Black%20Mountain%20College\"&limit=10"
```

**Response:**

```json
{
  "results": [
    {
      "book": {
        "id": 42,
        "title": "Black Mountain College: Experiment in Art",
        "authors": "Harris, Mary Emma",
        "year": 2003,
        "publisher": "MIT Press",
        "journal": null,
        "doi": "10.1234/example",
        "isbn": "978-0-262-08313-7",
        "entry_type": "book",
        "doc_keywords": "education, art, experimental pedagogy",
        "doc_summary": "History of Black Mountain College...",
        "total_quotes": 247
      },
      "hits_count": 12,
      "top_quotes": [
        {
          "id": 1523,
          "quote_text": "Black Mountain College was an experimental...",
          "page": 45,
          "keywords": "experimental, pedagogy",
          "score": 15.3
        }
      ],
      "total_book_quotes": 247
    }
  ],
  "total": 3,
  "offset": 0,
  "limit": 20
}
```

**Status Codes:**

- `200 OK`: Search completed successfully
- `400 Bad Request`: Invalid query or parameters
- `503 Service Unavailable`: Search index not available

---

### Search with Score Breakdown

Get detailed scoring information for debugging/tuning.

```http
GET /search/breakdown
```

**Query Parameters:**

Same as `/search`, plus optional scoring configuration.

**Example Request:**

```bash
curl "http://localhost:8000/search/breakdown?q=education&limit=5"
```

**Response:**

Includes `score_breakdown` for each quote with:
- `bm25_raw`: Raw BM25 score from FTS5
- `bm25_normalized`: Normalized BM25 score
- `field_score`: Bonus points from field matches
- `field_matches`: Which fields matched (title, authors, keywords, etc.)
- `phrase_bonus`: Bonus for exact phrase match
- `final_score`: Total score used for ranking

---

## Quote Endpoints

### Get Quote by ID

Retrieve a single quote with full book metadata.

```http
GET /quotes/{quote_id}
```

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `quote_id` | integer | Quote ID |

**Example Request:**

```bash
curl "http://localhost:8000/quotes/1523"
```

**Response:**

```json
{
  "id": 1523,
  "quote_text": "Black Mountain College was an experimental...",
  "page": 45,
  "section": "Chapter 2",
  "keywords": "experimental, pedagogy",
  "book": {
    "id": 42,
    "title": "Black Mountain College: Experiment in Art",
    "authors": "Harris, Mary Emma",
    "year": 2003,
    "publisher": "MIT Press",
    "doi": "10.1234/example",
    "isbn": "978-0-262-08313-7"
  },
  "citation": "Harris, Mary Emma. \"Black Mountain College: Experiment in Art\". MIT Press. 2003. p. 45."
}
```

**Status Codes:**

- `200 OK`: Quote found
- `404 Not Found`: Quote ID does not exist

---

### Get Database Statistics

Get counts and metadata about the search index.

```http
GET /quotes/stats
```

**Example Request:**

```bash
curl "http://localhost:8000/quotes/stats"
```

**Response:**

```json
{
  "books": 1247,
  "quotes": 18532,
  "fts_entries": 18532,
  "database_size_mb": 45.7,
  "indexed_at": "2025-01-15T10:30:00Z"
}
```

---

## Book Endpoints

### Get Book Quotes

Retrieve all quotes from a specific book.

```http
GET /books/{book_id}/quotes
```

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `book_id` | integer | Book ID |

**Query Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `relevant` | boolean | No | false | If true, filter to relevant quotes based on query |
| `q` | string | No | - | Search query (required if relevant=true) |
| `offset` | integer | No | 0 | Pagination offset |
| `limit` | integer | No | 10 | Number of quotes per page |

**Example Request:**

```bash
# Get all quotes
curl "http://localhost:8000/books/42/quotes?limit=20"

# Get relevant quotes
curl "http://localhost:8000/books/42/quotes?relevant=true&q=experimental"
```

**Response:**

```json
{
  "book_id": 42,
  "relevant": false,
  "offset": 0,
  "quotes": [
    {
      "id": 1523,
      "page": 45,
      "section": "Chapter 2",
      "quote_text": "Black Mountain College was...",
      "keywords": "experimental, pedagogy"
    }
  ],
  "has_more": true,
  "total_count": 247
}
```

---

### Get Book Citation

Get formatted citation for a book.

```http
GET /books/{book_id}/citation
```

**Response:**

Plain text citation in ISO 690 format (or basic format if unavailable).

---

## Edit Endpoints

### Save Single Edit

Update a single field on a book or quote.

```http
POST /edits/save
```

**Request Body:**

```json
{
  "entity_type": "book",
  "entity_id": 42,
  "field_name": "title",
  "new_value": "Updated Title",
  "edited_by": "user@example.com"
}
```

**Allowed Fields:**

**Books:**
- `title`, `authors`, `year`, `publisher`, `doi`, `issn`
- `entry_type`, `doc_keywords`, `doc_summary`, `container`

**Quotes:**
- `quote_text`, `page`, `keywords`, `section`

**Response:**

```json
{
  "entity_type": "book",
  "entity_id": 42,
  "field_name": "title",
  "old_value": "Original Title",
  "new_value": "Updated Title",
  "status": "success"
}
```

**Status Codes:**

- `200 OK`: Edit saved successfully
- `400 Bad Request`: Invalid field or parameters
- `404 Not Found`: Entity not found

---

### Save Multiple Edits

Update multiple fields on an entity at once (atomic transaction).

```http
POST /edits/save-multiple
```

**Request Body:**

```json
{
  "entity_type": "book",
  "entity_id": 42,
  "updates": {
    "title": "New Title",
    "authors": "New Author",
    "year": 2025
  },
  "edited_by": "user@example.com"
}
```

**Response:**

```json
{
  "results": [
    {
      "entity_type": "book",
      "entity_id": 42,
      "field_name": "title",
      "old_value": "Old Title",
      "new_value": "New Title",
      "status": "success"
    }
  ],
  "total_edits": 3
}
```

---

## Export Endpoints

### Export Database

Export the complete database with all edits applied.

```http
GET /export
```

**Response:**

ZIP file containing:
- `biblio.csv`: Book metadata
- `data/extracts/*.json`: Quote files

**Headers:**

- `Content-Type: application/zip`
- `Content-Disposition: attachment; filename="library_export_YYYYMMDD_HHMMSS.zip"`
- `X-Export-Stats: books=1247;quotes=18532;files=1247`

---

## Expert Mode Endpoints

### Reindex Database

Rebuild the entire search index from source files (requires expert mode).

```http
POST /expert/reindex
```

**Request Body:**

```json
{
  "csv_path": "data/FINAL_BIBLIO.csv",
  "json_folder": "data/extracts"
}
```

**Response:**

```json
{
  "status": "success",
  "books_processed": 1247,
  "quotes_processed": 18532,
  "elapsed_seconds": 12.5,
  "database_path": "index/library.db",
  "message": "Successfully reindexed CSV: 1247 books, JSON: 18532 quotes in 12.5s"
}
```

---

### Get Expert Status

Get expert mode system status.

```http
GET /expert/status
```

**Response:**

```json
{
  "database_exists": true,
  "database_path": "index/library.db",
  "database_size_mb": 45.7,
  "books_count": 1247,
  "quotes_count": 18532,
  "message": "Database ready with 1247 books and 18532 quotes"
}
```

---

## Health & Monitoring

### Health Check

Simple health check endpoint.

```http
GET /health
```

**Response:**

```json
{
  "status": "ok",
  "timestamp": "2025-01-15T10:30:00Z"
}
```

---

## Rate Limiting

API endpoints are rate-limited to prevent abuse:

- **Search endpoints**: 100 requests per minute
- **Edit endpoints**: 50 requests per minute
- **Export endpoints**: 10 requests per hour

Rate limit headers are included in responses:

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1642252800
```

---

## Error Responses

All errors follow a consistent format:

```json
{
  "detail": "Error message explaining what went wrong"
}
```

Common error codes:

- `400 Bad Request`: Invalid parameters or request body
- `404 Not Found`: Resource does not exist
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: Server-side error
- `503 Service Unavailable`: Database or service unavailable

---

## Code Examples

### Python

```python
import requests

# Search for quotes
response = requests.get(
    'http://localhost:8000/search',
    params={'q': '"Black Mountain College"', 'limit': 10}
)
results = response.json()

# Get a specific quote
quote = requests.get('http://localhost:8000/quotes/1523').json()

# Edit a book field
edit_response = requests.post(
    'http://localhost:8000/edits/save',
    json={
        'entity_type': 'book',
        'entity_id': 42,
        'field_name': 'title',
        'new_value': 'Updated Title'
    }
)
```

### JavaScript

```javascript
// Search for quotes
const response = await fetch(
  'http://localhost:8000/search?q="Black Mountain College"&limit=10'
);
const results = await response.json();

// Get a specific quote
const quote = await fetch('http://localhost:8000/quotes/1523')
  .then(r => r.json());

// Edit a book field
const editResponse = await fetch('http://localhost:8000/edits/save', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    entity_type: 'book',
    entity_id: 42,
    field_name: 'title',
    new_value: 'Updated Title'
  })
});
```

### curl

```bash
# Search
curl "http://localhost:8000/search?q=\"Black%20Mountain%20College\"&limit=10"

# Get quote
curl "http://localhost:8000/quotes/1523"

# Edit
curl -X POST "http://localhost:8000/edits/save" \
  -H "Content-Type: application/json" \
  -d '{
    "entity_type": "book",
    "entity_id": 42,
    "field_name": "title",
    "new_value": "Updated Title"
  }'

# Export database
curl "http://localhost:8000/export" -o library_export.zip
```

---

## Performance

Expected performance benchmarks:

- **Simple search**: < 100ms for 20k quotes
- **Complex search**: < 500ms for 20k quotes
- **Single quote retrieval**: < 50ms
- **Single field edit**: < 100ms
- **Database export**: < 5s for 20k quotes

Performance may vary based on database size and system resources.

---

## Best Practices

1. **Use exact phrases** for precise matching: `"exact phrase"`
2. **Paginate large result sets** using `offset` and `limit`
3. **Cache search results** on the client side when possible
4. **Use score breakdown** endpoint only for debugging/tuning
5. **Batch edits** using `save-multiple` instead of multiple `save` calls
6. **Monitor rate limits** to avoid throttling
7. **Handle errors gracefully** with appropriate fallbacks

---

## Support

For issues, questions, or feature requests, please open an issue on the project repository.
