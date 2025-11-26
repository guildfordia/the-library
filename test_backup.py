#!/usr/bin/env python3
"""Test backup file integrity and contents."""

import zipfile
import sqlite3
import sys
from pathlib import Path
import shutil

def test_backup(backup_file):
    """Test a backup file."""
    print(f'Testing backup file: {backup_file}')
    print('=' * 60)
    print()

    if not Path(backup_file).exists():
        print(f'[FAIL] Backup file not found: {backup_file}')
        return False

    try:
        # Test 1: Can we open the ZIP file?
        print('Test 1: Opening ZIP file...')
        with zipfile.ZipFile(backup_file, 'r') as zf:
            print('  [OK] ZIP file is valid and readable')

            # Test 2: Check for required files
            print()
            print('Test 2: Checking for required files...')
            files = zf.namelist()

            has_db = any('library.db' in f for f in files)
            has_csv = any('.csv' in f for f in files)
            has_json = any('.json' in f for f in files)

            db_status = '[OK] Found' if has_db else '[FAIL] Missing'
            csv_status = '[OK] Found' if has_csv else '[FAIL] Missing'
            json_status = '[OK] Found' if has_json else '[FAIL] Missing'

            print(f'  Database file: {db_status}')
            print(f'  CSV files: {csv_status}')
            print(f'  JSON files: {json_status}')

            if not (has_db and has_csv and has_json):
                print()
                print('[FAIL] Backup is missing required files!')
                return False

            # Test 3: Extract and verify database
            print()
            print('Test 3: Extracting and testing database...')

            # Extract to temp directory
            test_dir = Path('backups/test_restore')
            if test_dir.exists():
                shutil.rmtree(test_dir)
            test_dir.mkdir(parents=True)

            zf.extractall(test_dir)
            print('  [OK] Files extracted successfully')

            # Test database integrity
            db_path = test_dir / 'index' / 'library.db'
            if not db_path.exists():
                print('  [FAIL] Database file not found after extraction')
                return False

            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            # Test basic queries
            cursor.execute('SELECT COUNT(*) FROM books')
            book_count = cursor.fetchone()[0]
            print(f'  [OK] Database readable: {book_count} books')

            cursor.execute('SELECT COUNT(*) FROM quotes')
            quote_count = cursor.fetchone()[0]
            print(f'  [OK] Database readable: {quote_count} quotes')

            # Test a sample query
            cursor.execute('SELECT title FROM books LIMIT 1')
            sample = cursor.fetchone()
            if sample:
                title_preview = sample[0][:50]
                print(f'  [OK] Sample book title: "{title_preview}..."')

            # Check table structure
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            print(f'  [OK] Found {len(tables)} tables: {", ".join(tables)}')

            conn.close()

            # Test 4: Verify file counts and sizes
            print()
            print('Test 4: File statistics...')
            csv_files = [f for f in files if f.endswith('.csv')]
            json_files = [f for f in files if f.endswith('.json')]

            print(f'  CSV files in backup: {len(csv_files)}')
            for csv_file in csv_files:
                info = zf.getinfo(csv_file)
                size_kb = info.file_size / 1024
                print(f'    - {csv_file} ({size_kb:.1f} KB)')

            print(f'  JSON files in backup: {len(json_files)}')
            print(f'  Total files in backup: {len(files)}')

            # Calculate total backup size
            total_size = sum(zf.getinfo(f).file_size for f in files)
            compressed_size = sum(zf.getinfo(f).compress_size for f in files)
            compression_ratio = (1 - compressed_size / total_size) * 100

            print(f'  Uncompressed size: {total_size / 1024 / 1024:.2f} MB')
            print(f'  Compressed size: {compressed_size / 1024 / 1024:.2f} MB')
            print(f'  Compression ratio: {compression_ratio:.1f}%')

            # Cleanup
            shutil.rmtree(test_dir)
            print()
            print('  [OK] Cleanup completed')

    except Exception as e:
        print(f'  [FAIL] Error: {e}')
        import traceback
        traceback.print_exc()
        return False

    print()
    print('=' * 60)
    print('[SUCCESS] All tests passed! Backup is valid and restorable.')
    return True


if __name__ == '__main__':
    if len(sys.argv) > 1:
        backup_file = sys.argv[1]
    else:
        # Default to most recent backup
        backup_dir = Path('backups')
        backups = sorted(backup_dir.glob('library_backup_*.zip'), key=lambda p: p.stat().st_mtime, reverse=True)
        if not backups:
            print('[FAIL] No backups found in backups/ directory')
            sys.exit(1)
        backup_file = backups[0]

    success = test_backup(backup_file)
    sys.exit(0 if success else 1)
