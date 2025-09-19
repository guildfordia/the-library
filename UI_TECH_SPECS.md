# UI Technical Specifications

You are generating an ASCII-styled, minimal React UI for the **Semantic Quotes Search Server**.

## Purpose
- Let users search for **quotes** (not full documents).
- Show results **grouped by book**; user expands a book to reveal quotes.
- Keep it responsive, fast, and Pi-friendly. Monochrome, ASCII aesthetic.

## Visual style
- Background: white. Text: black/gray only.
- Global font: **monospace** (`font-mono` via Tailwind).
- Use ASCII frames/separators and labels, e.g.:
  ```
  +--------------------------------------------------------------------------+
  | [search]                                                                 |
  +--------------------------------------------------------------------------+
  ```
- Minimal hints of gray for hierarchy; can use **bold** and **underlined** text where useful.
- No images, icons optional (ASCII caret).

## Behavior (confirmed choices)
- Search bar at top.
- **Search triggers only on Enter or clicking a "Search" button.** No live/debounced search.
- **No exact-phrase special handling** on the frontend; just pass `q` to the backend.
- Results are **grouped by book**.
- Pagination: **10 books per page**.
- Within each expanded book:
  - Show **up to 10 quotes initially**, with a button **"expand"** to reveal 10 more, and so on (incremental reveal).
- Each quote row shows `quote_text` and small meta `(page, section)` when available.
- Each quote has a small **[copy]** button that copies:
  `"quote_text — title, authors (year), page"`
- Show small ASCII spinner **[ .... ]** while searching.
- Empty state text: `no matches (tip: use quotes "..." for exact phrase)` (text stays the same even though we don't treat exact phrase specially on frontend).
- Layout must be **responsive** (mobile → single column, wraps nicely).

## Keyboard & Interaction
- **Dedicated caret** on each book row to expand/collapse (click/tap only).
- **Arrow keys** (↑/↓) move focus across focusable UI elements (search input, Search button, each book row caret, pagination controls, per-quote copy buttons).
- **No Enter or Escape shortcuts** for expansion/collapse. Expansion is via caret click/tap only.
- Apply proper focus styles and `aria` attributes for accessibility (e.g., `aria-expanded` on the caret button).

## Data contracts (align with backend)
- `GET /search?q=<string>&offset=<int>&limit=10`
  Returns:
  ```json
  {
    "results": [
      {
        "book": {
          "id": 123,
          "title": "Book Title",
          "authors": "Author Names",
          "year": 2020,
          "publisher": "Publisher",
          "journal": "Journal Name",
          "doi": "10.1234/doi",
          "isbn": "978-0-123456-78-9",
          "themes": "Theme1, Theme2",
          "summary": "Book summary...",
          "iso690": "Full citation format"
        },
        "hits_count": 25,
        "top_quotes": [
          {
            "id": 456,
            "quote_text": "The actual quote text...",
            "page": 42,
            "keywords": "keyword1, keyword2",
            "score": 8.5
          }
        ]
      }
    ],
    "total": 156,
    "offset": 0,
    "limit": 10,
    "query": "search term"
  }
  ```

## Implementation Notes
- Use React 18+ with functional components and hooks
- Tailwind CSS for styling with monospace font classes
- Fetch API for backend communication
- localStorage for any client-side preferences (optional)
- No external icon libraries; ASCII characters only
- Ensure CORS is handled (backend already configured)
- API base URL: `http://localhost:8000` (configurable via env var)