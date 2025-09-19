# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Role
Claude serves as a project copilot for "The Library" - a search system that finds and returns *quotes* from protected documents without ever exposing full document content. Focus on concise, action-oriented implementation that prioritizes exact phrase matching and privacy protection.

## Objectives & Non-Goals

**Objectives:**
- Build a quote search system using SQLite + FTS5 for exact phrase matching
- Ingest CSV metadata and JSON highlight files into searchable index
- Return only quotes + citations, never full document content
- Support Docker deployment on Raspberry Pi 4
- Implement BM25 scoring with phrase bonuses

**Non-Goals:**
- Do not expose or return raw document content
- No PostgreSQL or pgvector (SQLite only for MVP)
- No semantic search initially (FAISS comes later)
- No complex UI (minimal React for now)

## Repository Structure

```
├── api/
│   ├── main.py              # FastAPI application entry point
│   ├── routes/
│   │   ├── search.py        # Search endpoint with FTS5 queries
│   │   └── quotes.py        # Individual quote retrieval
│   └── services/
│       ├── parser.py        # Query parsing (quotes, AND/OR/NOT)
│       └── scorer.py        # BM25 + phrase bonus scoring
├── indexer/
│   ├── build_index.py       # SQLite + FTS5 index builder
│   └── normalize.py         # Text normalization utilities
├── data/
│   ├── extracts/           # JSON files with highlights (~366 files)
│   └── pdfs/               # Source PDF documents (not indexed)
├── index/                  # SQLite database file location
├── docker-compose.yml      # Container orchestration
├── Dockerfile             # API container definition
└── README.md              # Project documentation
```

## Data Model

**books table:**
- `id` (PRIMARY KEY)
- `title` (TEXT)
- `authors` (TEXT)
- `year` (INTEGER)
- `themes` (TEXT)
- `keywords` (TEXT)
- `summary` (TEXT)
- `iso690` (TEXT) - Full citation

**quotes table:**
- `id` (PRIMARY KEY)
- `book_id` (FOREIGN KEY)
- `quote_text` (TEXT)
- `page` (INTEGER)
- `section` (TEXT)
- `keywords` (TEXT)
- `source_file` (TEXT)

**quotes_fts virtual table (FTS5):**
- Indexes: `quote_text`, `keywords`
- Uses BM25 ranking from FTS5
- Rebuilt from canonical `quotes` table

## Query DSL & Parsing

**Supported syntax:**
- Quoted phrases: `"exact phrase"` (highest priority)
- Boolean operators: `term1 AND term2`, `term1 OR term2`, `NOT term3`
- Prefix matching: `term*`
- Field filters (future): `author:dewey`, `year:1936`, `theme:education`

**Parsing rules:**
- Extract first quoted phrase for phrase_bonus calculation
- Convert to FTS5 MATCH syntax
- Preserve operator precedence (NOT > AND > OR)

## Scoring Algorithm (MVP)

```python
base_score = bm25(quote_text, keywords)
phrase_bonus = 2.0 if exact_phrase_in_quote else 0.0
final_score = base_score + phrase_bonus
```

**Result grouping:**
- Group by `book_id` for UI display
- Show book metadata + hit count
- Expandable quotes section per book
- Sort books by highest-scoring quote

## API Contracts

**GET /search**
```
Query params: q (required), offset (default: 0), limit (default: 20)
Response: {
  "results": [
    {
      "book": {
        "id": 1,
        "title": "...",
        "authors": "...",
        "year": 1936,
        "iso690": "..."
      },
      "hits_count": 5,
      "top_quotes": [
        {
          "id": 123,
          "quote_text": "...",
          "page": 42,
          "keywords": "...",
          "score": 8.5
        }
      ]
    }
  ],
  "total": 156
}
```

**GET /quotes/{id}**
```
Response: {
  "id": 123,
  "quote_text": "...",
  "page": 42,
  "book": { /* full book metadata */ },
  "citation": "Formatted ISO 690 citation"
}
```

**POST /admin/reindex**
```
Response: { "status": "success", "indexed_books": 1000, "indexed_quotes": 15000 }
```

## Common Commands

**Index Operations:**
```bash
# Rebuild entire index from data/extracts/
python indexer/build_index.py

# Rebuild FTS index only (faster)
python indexer/build_index.py --fts-only
```

**Development:**
```bash
# Start API locally
uvicorn api.main:app --reload --port 8000

# Run with Docker
docker-compose up --build

# Test search endpoint
curl "http://localhost:8000/search?q=\"Black Mountain College\""
```

**Database Operations:**
```bash
# SQLite console
sqlite3 index/library.db

# Backup index
cp index/library.db index/library_backup_$(date +%Y%m%d).db

# View FTS schema
sqlite3 index/library.db ".schema quotes_fts"
```

## Architecture Notes

**Data Flow:**
1. JSON files in `data/extracts/` are source of truth
2. `indexer/build_index.py` parses JSON → SQLite tables
3. FTS5 virtual table built from canonical tables
4. API queries FTS + applies phrase bonuses
5. Results grouped by book, return quotes + citations only

**SQLite Optimization (Pi 4):**
```sql
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA cache_size = 10000;
PRAGMA temp_store = memory;
```

**FTS5 Configuration:**
```sql
CREATE VIRTUAL TABLE quotes_fts USING fts5(
  quote_text, keywords,
  content='quotes',
  content_rowid='id'
);
```

## Acceptance Criteria (MVP)

- [ ] Exact phrase queries return expected quotes at top
- [ ] No full document content ever returned
- [ ] Reindex works end-to-end JSON → searchable results
- [ ] BM25 + phrase bonus scoring implemented
- [ ] Docker deployment works on Pi 4
- [ ] API returns book-grouped results with citations
- [ ] Search handles ~20k quotes with sub-second response

## Later Features (Post-MVP)

- FAISS embeddings for semantic discovery
- Faceted search (author, year, theme filters)
- Reranking with sentence transformers
- Advanced query parsing (field filters)
- React UI with quote highlighting