"""
Simple test script for The Library API.
Run after building the index to verify everything works.
"""

import requests
import json
import sys

BASE_URL = "http://localhost:8000"

def test_health():
    """Test health endpoint"""
    print("Testing health endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            print("✓ Health check passed")
            print(json.dumps(response.json(), indent=2))
        else:
            print(f"✗ Health check failed: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("✗ Cannot connect to API. Is it running?")
        return False
    return True

def test_search():
    """Test search endpoint"""
    print("\nTesting search endpoint...")

    test_queries = [
        "education",
        '"Black Mountain"',
        "educat*",
        "progressive AND college"
    ]

    for query in test_queries:
        print(f"Searching for: {query}")
        try:
            response = requests.get(f"{BASE_URL}/search", params={"q": query, "limit": 5})
            if response.status_code == 200:
                data = response.json()
                print(f"  ✓ Found {data['total']} results")
                if data['results']:
                    first_result = data['results'][0]
                    print(f"  Top book: {first_result['book']['title']}")
                    if first_result['top_quotes']:
                        print(f"  Top quote: {first_result['top_quotes'][0]['quote_text'][:100]}...")
            else:
                print(f"  ✗ Search failed: {response.status_code}")
        except Exception as e:
            print(f"  ✗ Search error: {e}")

def test_quote_detail():
    """Test quote detail endpoint"""
    print("\nTesting quote detail endpoint...")

    # First, get a quote ID from search
    try:
        response = requests.get(f"{BASE_URL}/search", params={"q": "education", "limit": 1})
        if response.status_code == 200:
            data = response.json()
            if data['results'] and data['results'][0]['top_quotes']:
                quote_id = data['results'][0]['top_quotes'][0]['id']
                print(f"Testing quote ID: {quote_id}")

                detail_response = requests.get(f"{BASE_URL}/quotes/{quote_id}")
                if detail_response.status_code == 200:
                    quote_data = detail_response.json()
                    print("  ✓ Quote detail retrieved")
                    print(f"  Quote: {quote_data['quote_text'][:100]}...")
                    print(f"  Citation: {quote_data['citation'][:100]}...")
                else:
                    print(f"  ✗ Quote detail failed: {detail_response.status_code}")
            else:
                print("  No quotes found to test detail endpoint")
    except Exception as e:
        print(f"  ✗ Quote detail error: {e}")

def test_stats():
    """Test stats endpoint"""
    print("\nTesting stats endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/quotes/admin/stats")
        if response.status_code == 200:
            stats = response.json()
            print("✓ Stats retrieved")
            print(f"  Books: {stats['books']}")
            print(f"  Quotes: {stats['quotes']}")
            print(f"  FTS entries: {stats['fts_entries']}")
            print(f"  Database size: {stats['database_size_bytes']} bytes")
        else:
            print(f"✗ Stats failed: {response.status_code}")
    except Exception as e:
        print(f"✗ Stats error: {e}")

def main():
    print("The Library API Test Script")
    print("=" * 30)

    if not test_health():
        print("\nAPI is not running or not healthy. Start it with:")
        print("  uvicorn api.main:app --reload --port 8000")
        print("Or:")
        print("  docker-compose up")
        sys.exit(1)

    test_search()
    test_quote_detail()
    test_stats()

    print("\n" + "=" * 30)
    print("Test completed! 🎉")
    print(f"API documentation: {BASE_URL}/docs")

if __name__ == "__main__":
    main()