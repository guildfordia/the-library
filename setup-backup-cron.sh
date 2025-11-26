#!/bin/bash
#
# Setup automatic daily backups for The Library
#
# This script:
# 1. Makes the backup script executable
# 2. Creates a cron job to run backups daily at 6 AM
# 3. Creates the backups directory
#
# Usage: ./setup-backup-cron.sh
#

set -e

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP_SCRIPT="$SCRIPT_DIR/server/backup.py"
BACKUP_DIR="$SCRIPT_DIR/backups"

echo "Setting up automatic backups for The Library"
echo "=============================================="
echo ""

# Make backup script executable
echo "1. Making backup script executable..."
chmod +x "$BACKUP_SCRIPT"
echo "   ✓ Done"
echo ""

# Create backups directory
echo "2. Creating backups directory..."
mkdir -p "$BACKUP_DIR"
echo "   ✓ Directory: $BACKUP_DIR"
echo ""

# Setup cron job
echo "3. Setting up cron job (daily at 6 AM)..."

CRON_COMMAND="0 6 * * * cd $SCRIPT_DIR && /usr/bin/python3 $BACKUP_SCRIPT --backup-dir $BACKUP_DIR --keep 5 >> $SCRIPT_DIR/backups/backup.log 2>&1"

# Check if cron job already exists
if crontab -l 2>/dev/null | grep -F "$BACKUP_SCRIPT" >/dev/null; then
    echo "   ⚠ Cron job already exists. Removing old version..."
    crontab -l 2>/dev/null | grep -v "$BACKUP_SCRIPT" | crontab -
fi

# Add new cron job
(crontab -l 2>/dev/null; echo "$CRON_COMMAND") | crontab -

echo "   ✓ Cron job added"
echo ""

# Display current cron jobs
echo "4. Current cron jobs:"
echo "   -----------------"
crontab -l | grep -F "$BACKUP_SCRIPT" || echo "   (none found - this is unexpected!)"
echo ""

# Test backup script
echo "5. Testing backup script..."
echo "   Running test backup now..."
cd "$SCRIPT_DIR"
python3 "$BACKUP_SCRIPT" --backup-dir "$BACKUP_DIR" --keep 5
echo ""

echo "✅ Backup system setup complete!"
echo ""
echo "Summary:"
echo "  • Backup script: $BACKUP_SCRIPT"
echo "  • Backup directory: $BACKUP_DIR"
echo "  • Schedule: Daily at 6:00 AM"
echo "  • Retention: 5 most recent backups"
echo "  • Log file: $BACKUP_DIR/backup.log"
echo ""
echo "To manually run a backup:"
echo "  cd $SCRIPT_DIR && python3 server/backup.py"
echo ""
echo "To list existing backups:"
echo "  cd $SCRIPT_DIR && python3 server/backup.py --list"
echo ""
echo "To remove the cron job:"
echo "  crontab -e  (then delete the line containing 'backup.py')"
echo ""
