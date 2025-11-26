# Backup System Documentation

## Overview

The Library has an automatic backup system that creates daily snapshots of all critical data:
- SQLite database (`library.db`)
- Bibliography CSV files
- Quote/extract JSON files

## Configuration

- **Schedule**: Daily at 6:00 AM
- **Retention**: 5 most recent backups
- **Location**: `/opt/the-library/backups/` (production)
- **Format**: ZIP archives with timestamp

## Backup Filename Format

```
library_backup_YYYYMMDD_HHMMSS.zip
```

Example: `library_backup_20250126_060000.zip`

## Backup Contents

Each backup contains:
```
library_backup_YYYYMMDD_HHMMSS.zip
├── index/
│   ├── library.db           # Main SQLite database
│   ├── library.db-wal       # Write-ahead log (if exists)
│   └── library.db-shm       # Shared memory file (if exists)
├── data/
│   ├── biblio/
│   │   └── *.csv           # Bibliography CSV files
│   └── extracts/
│       └── *.json          # Quote/extract JSON files
```

## Setup (Production Server)

### Initial Setup

1. SSH into production server:
   ```bash
   ssh retcon
   ```

2. Navigate to project directory:
   ```bash
   cd /opt/the-library
   ```

3. Run setup script:
   ```bash
   chmod +x setup-backup-cron.sh
   ./setup-backup-cron.sh
   ```

This will:
- Make the backup script executable
- Create the backups directory
- Set up a cron job for daily 6 AM backups
- Run a test backup

### Verify Setup

Check that cron job is installed:
```bash
crontab -l | grep backup
```

Expected output:
```
0 6 * * * cd /opt/the-library && /usr/bin/python3 /opt/the-library/server/backup.py --backup-dir /opt/the-library/backups --keep 5 >> /opt/the-library/backups/backup.log 2>&1
```

## Manual Operations

### Run Backup Manually

```bash
cd /opt/the-library
python3 server/backup.py
```

### List Existing Backups

```bash
cd /opt/the-library
python3 server/backup.py --list
```

Example output:
```
Found 5 backup(s):

  library_backup_20250126_060000.zip
    Size: 125.45 MB
    Date: 2025-01-26 06:00:00

  library_backup_20250125_060000.zip
    Size: 124.89 MB
    Date: 2025-01-25 06:00:00
  ...
```

### Check Backup Logs

```bash
tail -50 /opt/the-library/backups/backup.log
```

### Change Retention Policy

To keep more/fewer backups, edit the cron job:
```bash
crontab -e
```

Change `--keep 5` to your desired number.

## Restore from Backup

### Full Restore

1. Stop the application:
   ```bash
   cd /opt/the-library
   docker compose -f docker-compose.prod.yml down
   ```

2. Extract backup:
   ```bash
   cd /opt/the-library
   unzip backups/library_backup_YYYYMMDD_HHMMSS.zip -d restore_temp
   ```

3. Replace files:
   ```bash
   # Backup current state (just in case)
   mv index/library.db index/library.db.old
   mv data/biblio data/biblio.old
   mv data/extracts data/extracts.old

   # Restore from backup
   cp restore_temp/index/library.db index/
   cp -r restore_temp/data/biblio/* data/biblio/
   cp -r restore_temp/data/extracts/* data/extracts/

   # Cleanup
   rm -rf restore_temp
   ```

4. Restart application:
   ```bash
   docker compose -f docker-compose.prod.yml up -d
   ```

### Partial Restore (Database Only)

If you only need to restore the database:

```bash
cd /opt/the-library
docker compose -f docker-compose.prod.yml down

# Extract just the database
unzip -j backups/library_backup_YYYYMMDD_HHMMSS.zip "index/library.db" -d index/

docker compose -f docker-compose.prod.yml up -d
```

## Troubleshooting

### Backups Not Running

1. Check cron job exists:
   ```bash
   crontab -l | grep backup
   ```

2. Check cron service is running:
   ```bash
   systemctl status cron
   # or
   service cron status
   ```

3. Check backup logs for errors:
   ```bash
   tail -100 /opt/the-library/backups/backup.log
   ```

### Disk Space Issues

1. Check available space:
   ```bash
   df -h /opt/the-library/backups
   ```

2. Reduce retention if needed:
   ```bash
   crontab -e
   # Change --keep 5 to --keep 3
   ```

3. Manually clean old backups:
   ```bash
   cd /opt/the-library/backups
   ls -lht library_backup_*.zip
   rm library_backup_YYYYMMDD_HHMMSS.zip  # Delete specific old backup
   ```

### Backup Script Fails

Run manually to see error details:
```bash
cd /opt/the-library
python3 server/backup.py --backup-dir backups --keep 5
```

## Monitoring

### Check Backup Status

Create a simple monitoring script:

```bash
#!/bin/bash
# check-backups.sh

BACKUP_DIR="/opt/the-library/backups"
MAX_AGE_HOURS=30  # Should have backup within last 30 hours

# Find most recent backup
LATEST=$(ls -t $BACKUP_DIR/library_backup_*.zip 2>/dev/null | head -1)

if [ -z "$LATEST" ]; then
    echo "❌ No backups found!"
    exit 1
fi

# Check age
AGE_SECONDS=$(( $(date +%s) - $(stat -c %Y "$LATEST") ))
AGE_HOURS=$(( $AGE_SECONDS / 3600 ))

echo "Latest backup: $(basename $LATEST)"
echo "Age: $AGE_HOURS hours"

if [ $AGE_HOURS -gt $MAX_AGE_HOURS ]; then
    echo "⚠️  Backup is older than $MAX_AGE_HOURS hours!"
    exit 1
else
    echo "✅ Backup is current"
    exit 0
fi
```

## Best Practices

1. **Test Restores**: Periodically test restoring from backups to ensure they work
2. **Monitor Logs**: Check `backups/backup.log` regularly for errors
3. **Disk Space**: Ensure sufficient disk space for retention policy
4. **Off-site**: Consider periodically copying backups to another location
5. **Before Major Changes**: Run manual backup before database migrations or bulk edits

## Additional Notes

- Backups run at 6 AM server time
- Backups include SQLite WAL files for consistency
- Old backups are automatically deleted (keeps 5 most recent)
- Backup process typically takes 1-5 minutes depending on data size
- Failed backups will be logged to `backups/backup.log`
