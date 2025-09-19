#!/bin/bash

# Script to rebuild The Library search index
# Usage: ./rebuild_index.sh [--fts-only]

set -e

echo "🔄 Rebuilding The Library search index..."

# Change to server directory
cd "$(dirname "$0")/server"

# Check if data files exist (paths relative to server directory)
if [ ! -f "../data/biblio/bibliographie_finale_these_FINAL_translated.csv" ]; then
    echo "⚠️  Warning: Bibliography CSV not found at ../data/biblio/bibliographie_finale_these_FINAL_translated.csv"
fi

if [ ! -d "../data/extracts" ]; then
    echo "⚠️  Warning: Extracts directory not found at ../data/extracts/"
fi

# Run the indexer
echo "📚 Running indexer..."
python3 indexer/build_index.py "$@"

echo "✅ Index rebuild complete!"
echo "💡 To start the API server, run: cd server && uvicorn api.main:app --reload --port 8000"