# Expert Mode - Database Reindexing

Expert Mode provides advanced functionality to reload and rebuild the search index from new data files.

## Endpoints

### POST /expert/reindex

Rebuilds the entire search database from CSV (books) and/or JSON (quotes) files.

**Request Body:**
```json
{
  "csv_path": "/path/to/bibliography.csv",
  "json_folder": "/path/to/quotes/folder"
}
```

**Response:**
```json
{
  "status": "success",
  "books_processed": 1250,
  "quotes_processed": 5847,
  "elapsed_seconds": 12.34,
  "database_path": "index/library.db",
  "message": "Successfully reindexed CSV: 1250 books, JSON: 5847 quotes in 12.34s"
}
```

### GET /expert/status

Get current database status and statistics.

**Response:**
```json
{
  "database_exists": true,
  "database_path": "index/library.db",
  "database_size_mb": 45.67,
  "books_count": 1250,
  "quotes_count": 5847,
  "message": "Database ready with 1250 books and 5847 quotes"
}
```

## Usage Examples

### 1. Reindex from both CSV and JSON

```bash
curl -X POST "http://localhost:8000/expert/reindex" \
  -H "Content-Type: application/json" \
  -d '{
    "csv_path": "/Users/username/data/bibliography.csv",
    "json_folder": "/Users/username/data/extracts"
  }'
```

### 2. Reindex only books from CSV

```bash
curl -X POST "http://localhost:8000/expert/reindex" \
  -H "Content-Type: application/json" \
  -d '{
    "csv_path": "/Users/username/data/new_bibliography.csv"
  }'
```

### 3. Reindex only quotes from JSON folder

```bash
curl -X POST "http://localhost:8000/expert/reindex" \
  -H "Content-Type: application/json" \
  -d '{
    "json_folder": "/Users/username/data/new_extracts"
  }'
```

### 4. Check database status

```bash
curl -X GET "http://localhost:8000/expert/status"
```

## CSV Format Requirements

The CSV file should contain book metadata with the following columns:

- `title` - Book title
- `authors` - Author names
- `year` - Publication year
- `publisher` - Publisher name
- `journal` - Journal name (for articles)
- `doi` - Digital Object Identifier
- `isbn` - ISBN number
- `themes` - Thematic categories
- `keywords` - Keywords/tags
- `summary` - Book summary/abstract
- `iso690` - ISO 690 citation format

## JSON Format Requirements

JSON files should contain quote data with this structure:

```json
{
  "metadata": {
    "title": "Book Title",
    "authors": "Author Names",
    "year": 2023,
    "themes": "Theme categories",
    "keywords": "Keywords"
  },
  "quotes": [
    {
      "text": "Quote content here...",
      "page": 42,
      "section": "Chapter 3",
      "keywords": "quote-specific keywords"
    }
  ]
}
```

## Process Overview

1. **Validation**: Checks that specified files/folders exist
2. **Schema Recreation**: Drops existing tables and recreates schema
3. **CSV Processing**: Imports book metadata into `books` table
4. **JSON Processing**: Imports quotes into `quotes` table
5. **FTS5 Indexing**: Rebuilds full-text search index
6. **Response**: Returns processing statistics and timing

## Error Handling

- **404**: File or folder not found
- **400**: Invalid input (missing paths, invalid JSON)
- **500**: Processing error (database issues, file corruption)

All errors include descriptive messages to help diagnose issues.

## Performance Notes

- Processing time depends on file size and number of records
- Large datasets (>10,000 records) may take several minutes
- The database is locked during reindexing
- All existing data is replaced during the process

## Integration with Search

After successful reindexing:
- All `/search` endpoints immediately use the new data
- Tuning configurations are preserved
- No restart required
- Search performance is optimized with rebuilt FTS5 index