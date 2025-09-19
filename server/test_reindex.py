#!/usr/bin/env python3
"""
Test script for Expert Mode reindexing functionality.
This script demonstrates how to use the /expert/reindex endpoint.
"""

import json
import requests
import time

API_URL = "http://localhost:8000"

def test_expert_status():
    """Test the expert status endpoint."""
    print("🔍 Checking expert status...")

    response = requests.get(f"{API_URL}/expert/status")

    if response.status_code == 200:
        data = response.json()
        print(f"✅ Database exists: {data['database_exists']}")
        if data['database_exists']:
            print(f"   📊 Books: {data['books_count']:,}")
            print(f"   📝 Quotes: {data['quotes_count']:,}")
            print(f"   💾 Size: {data['database_size_mb']} MB")
    else:
        print(f"❌ Error: {response.status_code} - {response.text}")

def test_reindex_validation():
    """Test reindex endpoint validation."""
    print("\n🧪 Testing reindex validation...")

    # Test with no paths provided
    response = requests.post(f"{API_URL}/expert/reindex", json={})

    if response.status_code == 400:
        print("✅ Correctly rejected empty request")
    else:
        print(f"❌ Unexpected response: {response.status_code}")

    # Test with non-existent file
    response = requests.post(f"{API_URL}/expert/reindex", json={
        "csv_path": "/nonexistent/file.csv"
    })

    if response.status_code == 404:
        print("✅ Correctly rejected non-existent file")
    else:
        print(f"❌ Unexpected response: {response.status_code}")

def test_reindex_current_data():
    """Test reindexing with current data files."""
    print("\n🔄 Testing reindex with current data...")

    # Use existing data paths
    csv_path = "/Users/murexpecten/Code/the-library/data/biblio/bibliographie_finale_these_FINAL_translated.csv"
    json_folder = "/Users/murexpecten/Code/the-library/data/extracts"

    # Check if files exist
    import os
    if not os.path.exists(csv_path):
        print(f"⚠️  CSV file not found: {csv_path}")
        print("   Using only JSON folder for testing...")
        csv_path = None

    if not os.path.exists(json_folder):
        print(f"⚠️  JSON folder not found: {json_folder}")
        print("   Using only CSV file for testing...")
        json_folder = None

    if not csv_path and not json_folder:
        print("❌ No test data available")
        return

    request_data = {}
    if csv_path:
        request_data["csv_path"] = csv_path
    if json_folder:
        request_data["json_folder"] = json_folder

    print(f"   📁 Request: {request_data}")

    start_time = time.time()
    response = requests.post(f"{API_URL}/expert/reindex", json=request_data)
    elapsed = time.time() - start_time

    if response.status_code == 200:
        data = response.json()
        print(f"✅ Reindex successful in {elapsed:.2f}s")
        print(f"   📚 Books processed: {data['books_processed']}")
        print(f"   📝 Quotes processed: {data['quotes_processed']}")
        print(f"   ⏱️  Server time: {data['elapsed_seconds']}s")
        print(f"   💬 Message: {data['message']}")
    else:
        print(f"❌ Reindex failed: {response.status_code}")
        print(f"   Error: {response.text}")

def test_search_after_reindex():
    """Test that search still works after reindexing."""
    print("\n🔍 Testing search functionality...")

    response = requests.get(f"{API_URL}/search", params={"q": "artificial intelligence", "limit": 3})

    if response.status_code == 200:
        data = response.json()
        print(f"✅ Search working - found {data['total']} results")
        if data['results']:
            first_result = data['results'][0]
            print(f"   📖 Top result: {first_result['book']['title']}")
            print(f"   🎯 Score: {first_result['top_quotes'][0]['score']}")
    else:
        print(f"❌ Search failed: {response.status_code}")

if __name__ == "__main__":
    print("🚀 Testing Expert Mode Reindexing")
    print("=" * 50)

    try:
        test_expert_status()
        test_reindex_validation()
        test_reindex_current_data()
        test_search_after_reindex()

        print("\n✅ All tests completed!")

    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to API. Make sure the server is running on localhost:8000")
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")