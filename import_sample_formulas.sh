#!/bin/bash
# Import sample formulas into the database

set -e

DB_NAME="linguaformula"
DB_USER="dev_user"
DB_PASSWORD="dev123"

echo "📥 Importing sample formulas into database..."

# Check if PGPASSWORD is set, otherwise use the default
if [ -z "$PGPASSWORD" ]; then
    export PGPASSWORD="$DB_PASSWORD"
fi

# Run import scripts
echo "  → Importing production formulas..."
PGPASSWORD="$DB_PASSWORD" psql -d "$DB_NAME" -U "$DB_USER" -f migrations/import_production_formulas.sql 2>/dev/null || {
    echo "    (You may be prompted for password)"
    psql -d "$DB_NAME" -U "$DB_USER" -f migrations/import_production_formulas.sql
}

echo "  → Adding simple linear regression..."
PGPASSWORD="$DB_PASSWORD" psql -d "$DB_NAME" -U "$DB_USER" -f migrations/add_simple_linear_regression.sql 2>/dev/null || {
    psql -d "$DB_NAME" -U "$DB_USER" -f migrations/add_simple_linear_regression.sql
}

echo ""
echo "✅ Formula import complete!"
echo ""
echo "📊 Verifying import..."
PGPASSWORD="$DB_PASSWORD" psql -d "$DB_NAME" -U "$DB_USER" -c "SELECT COUNT(*) as total_formulas FROM formula;" 2>/dev/null || {
    psql -d "$DB_NAME" -U "$DB_USER" -c "SELECT COUNT(*) as total_formulas FROM formula;"
}
