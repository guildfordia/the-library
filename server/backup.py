#!/usr/bin/env python3
"""
Automatic backup system for The Library.

Creates daily backups of:
- SQLite database (library.db)
- CSV bibliography files
- JSON quote/extract files

Retention: Keeps only the 5 most recent backups.
Schedule: Run daily at 6 AM via cron.

Usage:
    python backup.py [--backup-dir /path/to/backups]
"""

import os
import sys
import zipfile
import shutil
from pathlib import Path
from datetime import datetime
import argparse


def get_backup_filename():
    """Generate timestamped backup filename."""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    return f"library_backup_{timestamp}.zip"


def create_backup(base_dir: Path, backup_dir: Path):
    """
    Create a ZIP archive containing all critical data files.

    Args:
        base_dir: Root directory of the library project
        backup_dir: Directory where backups should be stored

    Returns:
        Path to created backup file
    """
    backup_dir.mkdir(parents=True, exist_ok=True)

    backup_path = backup_dir / get_backup_filename()

    print(f"Creating backup: {backup_path}")

    with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Backup database
        db_path = base_dir / 'index' / 'library.db'
        if db_path.exists():
            zipf.write(db_path, arcname='index/library.db')
            print(f"  ✓ Added database: {db_path.stat().st_size / 1024 / 1024:.2f} MB")
        else:
            print(f"  ⚠ Database not found: {db_path}")

        # Backup database WAL files (for SQLite consistency)
        for wal_file in ['library.db-wal', 'library.db-shm']:
            wal_path = base_dir / 'index' / wal_file
            if wal_path.exists():
                zipf.write(wal_path, arcname=f'index/{wal_file}')
                print(f"  ✓ Added WAL file: {wal_file}")

        # Backup CSV files (bibliography)
        csv_count = 0
        csv_dir = base_dir / 'data' / 'biblio'
        if csv_dir.exists():
            for csv_file in csv_dir.glob('*.csv'):
                zipf.write(csv_file, arcname=f'data/biblio/{csv_file.name}')
                csv_count += 1
            print(f"  ✓ Added {csv_count} CSV file(s)")
        else:
            print(f"  ⚠ CSV directory not found: {csv_dir}")

        # Backup JSON files (extracts/quotes)
        json_count = 0
        json_dir = base_dir / 'data' / 'extracts'
        if json_dir.exists():
            for json_file in json_dir.glob('*.json'):
                zipf.write(json_file, arcname=f'data/extracts/{json_file.name}')
                json_count += 1
            print(f"  ✓ Added {json_count} JSON file(s)")
        else:
            print(f"  ⚠ JSON directory not found: {json_dir}")

    backup_size = backup_path.stat().st_size / 1024 / 1024
    print(f"✅ Backup created: {backup_path.name} ({backup_size:.2f} MB)")

    return backup_path


def cleanup_old_backups(backup_dir: Path, keep_count: int = 5):
    """
    Remove old backups, keeping only the most recent ones.

    Args:
        backup_dir: Directory containing backups
        keep_count: Number of most recent backups to keep
    """
    # Find all backup files
    backup_files = sorted(
        backup_dir.glob('library_backup_*.zip'),
        key=lambda p: p.stat().st_mtime,
        reverse=True  # Most recent first
    )

    if len(backup_files) <= keep_count:
        print(f"✓ Found {len(backup_files)} backup(s), no cleanup needed (keeping {keep_count})")
        return

    # Delete old backups
    to_delete = backup_files[keep_count:]
    print(f"🗑  Removing {len(to_delete)} old backup(s)...")

    for old_backup in to_delete:
        old_backup.unlink()
        print(f"  ✓ Deleted: {old_backup.name}")

    print(f"✅ Cleanup complete. Keeping {keep_count} most recent backups.")


def list_backups(backup_dir: Path):
    """List all existing backups with details."""
    backup_files = sorted(
        backup_dir.glob('library_backup_*.zip'),
        key=lambda p: p.stat().st_mtime,
        reverse=True
    )

    if not backup_files:
        print("No backups found.")
        return

    print(f"\nFound {len(backup_files)} backup(s):\n")

    for backup in backup_files:
        stat = backup.stat()
        size_mb = stat.st_size / 1024 / 1024
        modified = datetime.fromtimestamp(stat.st_mtime)

        print(f"  {backup.name}")
        print(f"    Size: {size_mb:.2f} MB")
        print(f"    Date: {modified.strftime('%Y-%m-%d %H:%M:%S')}")
        print()


def main():
    parser = argparse.ArgumentParser(
        description='Backup The Library database and data files'
    )
    parser.add_argument(
        '--backup-dir',
        type=str,
        default='backups',
        help='Directory to store backups (default: ./backups)'
    )
    parser.add_argument(
        '--keep',
        type=int,
        default=5,
        help='Number of backups to keep (default: 5)'
    )
    parser.add_argument(
        '--list',
        action='store_true',
        help='List existing backups and exit'
    )

    args = parser.parse_args()

    # Determine base directory (parent of server directory)
    base_dir = Path(__file__).parent.parent.resolve()
    backup_dir = Path(args.backup_dir)

    # Make backup_dir absolute if it's relative
    if not backup_dir.is_absolute():
        backup_dir = base_dir / backup_dir

    print(f"Base directory: {base_dir}")
    print(f"Backup directory: {backup_dir}")
    print()

    # List mode
    if args.list:
        list_backups(backup_dir)
        return

    # Create backup
    try:
        backup_path = create_backup(base_dir, backup_dir)
        print()

        # Cleanup old backups
        cleanup_old_backups(backup_dir, keep_count=args.keep)
        print()

        # Show current backups
        list_backups(backup_dir)

        print("✅ Backup process completed successfully")
        sys.exit(0)

    except Exception as e:
        print(f"❌ Backup failed: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
