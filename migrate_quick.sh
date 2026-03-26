#!/bin/bash
# Quick migration script with password prompt
# Usage: ./migrate_quick.sh [source_database_name]

set -e

SOURCE_DB="${1:-physics_web_app_3}"
TARGET_DB="linguaformula"

echo "🔄 Quick Migration from $SOURCE_DB to $TARGET_DB"
echo ""
echo "⚠️  You'll need your PostgreSQL password"
echo ""

# Prompt for password
read -sp "Enter PostgreSQL password: " PASSWORD
echo ""

# Set environment variables
export PGPASSWORD="$PASSWORD"
export SOURCE_DB_PASSWORD="$PASSWORD"
export TARGET_DB_PASSWORD="dev123"

# Run migration
python3 migrate_from_physics_app.py "$SOURCE_DB"
