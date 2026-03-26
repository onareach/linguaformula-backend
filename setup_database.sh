#!/bin/bash
# Database setup script for LinguaFormula
# This script sets up the local database and runs migrations

set -e

DB_NAME="linguaformula"
DB_USER="${1:-dev_user}"
DB_PASSWORD="${2:-dev123}"
PGUSER="${PGUSER:-postgres}"

echo "🗄️  Setting up LinguaFormula database..."
echo ""
echo "⚠️  Note: You'll be prompted for your PostgreSQL password"
echo "   (This is usually your system password or the 'postgres' user password)"
echo ""

# Check if database exists
echo "📋 Checking if database exists..."
if PGPASSWORD="${PGPASSWORD}" psql -U "$PGUSER" -lqt 2>/dev/null | cut -d \| -f 1 | grep -qw "$DB_NAME"; then
    echo "✅ Database '$DB_NAME' already exists"
else
    echo "📦 Creating database '$DB_NAME'..."
    PGPASSWORD="${PGPASSWORD}" createdb -U "$PGUSER" "$DB_NAME" || {
        echo ""
        echo "❌ Failed to create database. Trying with password prompt..."
        createdb -U "$PGUSER" "$DB_NAME"
    }
fi

# Check if user exists and create if needed
echo "📋 Checking if user exists..."
if PGPASSWORD="${PGPASSWORD}" psql -U "$PGUSER" -d postgres -tAc "SELECT 1 FROM pg_roles WHERE rolname='$DB_USER'" 2>/dev/null | grep -q 1; then
    echo "✅ User '$DB_USER' already exists"
else
    echo "👤 Creating user '$DB_USER'..."
    PGPASSWORD="${PGPASSWORD}" psql -U "$PGUSER" -d postgres -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';" 2>/dev/null || {
        echo ""
        echo "⚠️  Password authentication required. Please enter your PostgreSQL password:"
        psql -U "$PGUSER" -d postgres -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';"
    }
fi

# Grant privileges
echo "🔐 Granting privileges..."
PGPASSWORD="${PGPASSWORD}" psql -U "$PGUSER" -d postgres -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;" 2>/dev/null || {
    psql -U "$PGUSER" -d postgres -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;"
}
PGPASSWORD="${PGPASSWORD}" psql -U "$PGUSER" -d "$DB_NAME" -c "GRANT ALL ON SCHEMA public TO $DB_USER;" 2>/dev/null || {
    psql -U "$PGUSER" -d "$DB_NAME" -c "GRANT ALL ON SCHEMA public TO $DB_USER;"
}

# Run migrations
echo "📝 Running migrations..."

# Initial schema
echo "  → Running initial_schema.sql..."
PGPASSWORD="$DB_PASSWORD" psql -d "$DB_NAME" -U "$DB_USER" -f migrations/initial_schema.sql 2>/dev/null || {
    echo "    (You may be prompted for password)"
    psql -d "$DB_NAME" -U "$DB_USER" -f migrations/initial_schema.sql
}

# Schema migration
echo "  → Running schema_migration.sql..."
PGPASSWORD="$DB_PASSWORD" psql -d "$DB_NAME" -U "$DB_USER" -f migrations/schema_migration.sql 2>/dev/null || {
    echo "    (You may be prompted for password)"
    psql -d "$DB_NAME" -U "$DB_USER" -f migrations/schema_migration.sql
}

echo ""
echo "✅ Database setup complete!"
echo ""
echo "📋 Connection string:"
echo "   postgresql://$DB_USER:$DB_PASSWORD@localhost:5432/$DB_NAME?sslmode=disable"
echo ""
echo "💡 To use this in your app, set:"
echo "   export DATABASE_URL=\"postgresql://$DB_USER:$DB_PASSWORD@localhost:5432/$DB_NAME?sslmode=disable\""
echo ""
echo "💡 Or set PGPASSWORD environment variable to avoid password prompts:"
echo "   export PGPASSWORD=your_postgres_password"
echo "   ./setup_database.sh"
