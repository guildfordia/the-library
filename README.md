# The Library

A search system that finds and returns *quotes* from protected documents without ever exposing full document content.

## Features

- **Privacy-First**: Returns only quotes + citations, never full documents
- **Exact Phrase Matching**: Prioritizes exact phrase matches with BM25 + phrase bonus scoring
- **SQLite + FTS5**: Fast full-text search optimized for Raspberry Pi 4
- **Docker Ready**: Simple deployment with docker-compose
- **RESTful API**: FastAPI-based with OpenAPI documentation

## Launch Instructions

### Option A: Docker Deployment (Recommended)

**Prerequisites**: Docker and Docker Compose installed

```bash
# 1. Start the application
docker-compose up --build

# 2. The API will be available at http://localhost:8000
# The index will be built automatically during startup

# 3. Test the search
curl "http://localhost:8000/search?q=\"Black Mountain College\""

# 4. View API documentation
open http://localhost:8000/docs
```

### Option B: Local Development (No Docker)

**Prerequisites**: Python 3.8+ and pip installed

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Build the search index
python -m indexer.build_index

# 3. Start the API server
uvicorn api.main:app --reload --port 8000

# 4. Test the search
curl "http://localhost:8000/search?q=\"Black Mountain College\""

# 5. View API documentation
open http://localhost:8000/docs
```

## Example Searches

```bash
# Simple search
curl "http://localhost:8000/search?q=education"

# Quoted phrase (gets scoring bonus)
curl "http://localhost:8000/search?q=\"Black Mountain College\""

# Boolean operators
curl "http://localhost:8000/search?q=education AND progressive"

# Prefix matching
curl "http://localhost:8000/search?q=educat*"
```

## API Endpoints

- `GET /search?q=query&offset=0&limit=20` - Search quotes
- `GET /quotes/{id}` - Get quote by ID with citation
- `POST /quotes/admin/reindex` - Rebuild search index
- `GET /quotes/admin/stats` - Database statistics
- `GET /health` - Health check

## Data Structure

```
data/
├── biblio/
│   └── final_biblio_EXCELLENCE_FINALE.csv  # Book metadata
└── extracts/
    └── *_highlights.json                   # Quote/highlight files

index/
└── library.db                             # SQLite database
```

## Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run indexer
python -m indexer.build_index

# Start API with hot reload
uvicorn api.main:app --reload --port 8000

# View API documentation
open http://localhost:8000/docs
```

## Configuration

The system is optimized for Raspberry Pi 4 with SQLite tuning:

```sql
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA cache_size = 10000;
PRAGMA temp_store = memory;
```

## Query Syntax

- **Quoted phrases**: `"exact phrase"` (gets phrase bonus)
- **Boolean operators**: `term1 AND term2`, `term1 OR term2`, `NOT term3`
- **Prefix matching**: `term*`
- **Combined**: `"Black Mountain College" AND education*`

## Architecture

1. **Data Sources**: CSV bibliography + JSON highlight files
2. **Indexer**: Parses sources → SQLite + FTS5 virtual table
3. **API**: FastAPI with BM25 + phrase bonus scoring
4. **Results**: Book-grouped with expandable quotes
5. **Privacy**: Only quotes + citations returned, never full documents