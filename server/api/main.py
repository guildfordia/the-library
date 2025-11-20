"""FastAPI application entry point for The Library quote search system."""

import os
import sqlite3

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from api.routes import search, quotes, books, tuning, expert, edits, conflicts, export

app = FastAPI(
    title="The Library API",
    description="Search system that finds and returns quotes from protected documents",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(search.router, prefix="/search", tags=["search"])
app.include_router(quotes.router, prefix="/quotes", tags=["quotes"])
app.include_router(books.router, prefix="/books", tags=["books"])
app.include_router(tuning.router, prefix="/tuning", tags=["tuning"])
app.include_router(expert.router, prefix="/expert", tags=["expert"])
app.include_router(edits.router, prefix="/edits", tags=["edits"])
app.include_router(conflicts.router, prefix="/admin", tags=["admin"])
app.include_router(export.router, prefix="/admin", tags=["admin"])

@app.get("/")
async def root():
    """Health check endpoint."""
    return {"message": "The Library API is running", "status": "healthy"}


@app.get("/health")
async def health_check():
    """Health check with database connectivity."""
    db_path = "index/library.db"

    if not os.path.exists(db_path):
        raise HTTPException(
            status_code=503,
            detail="Database not found. Run indexer first."
        )

    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
            table_count = cursor.fetchone()[0]

        return {
            "status": "healthy",
            "database": "connected",
            "tables": table_count
        }
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Database error: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)