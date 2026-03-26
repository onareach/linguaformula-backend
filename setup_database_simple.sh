#!/bin/bash
# Simplified database setup - uses current user (peer authentication)
# Use this if your PostgreSQL allows peer authentication for your user

set -e

DB_NAME="linguaformula"
DB_USER="dev_user"
DB_PASSWORD="dev123"

echo "🗄️  Setting up LinguaFormula database (using peer authentication)..."
echo ""

# Try to connect as current user first (peer auth)
CURRENT_USER=$(whoami)

# Check if database exists
if psql -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='$DB_NAME'" 2>/dev/null | grep -q 1; then
    echo "✅ Database '$DB_NAME' already exists"
else
    echo "📦 Creating database '$DB_NAME'..."
    createdb "$DB_NAME" 2>/dev/null || {
        echo "❌ Failed. You may need to run as postgres user:"
        echo "   sudo -u postgres createdb $DB_NAME"
        exit 1
    }
fi

# Check if we can connect as current user to create the dev_user
if psql -d postgres -tAc "SELECT 1 FROM pg_roles WHERE rolname='$DB_USER'" 2>/dev/null | grep -q 1; then
    echo "✅ User '$DB_USER' already exists"
else
    echo "👤 Creating user '$DB_USER'..."
    # Try as current user first
    psql -d postgres -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';" 2>/dev/null || {
        echo "⚠️  Need postgres superuser. Trying with sudo..."
        sudo -u postgres psql -d postgres -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';" || {
            echo "❌ Failed to create user. Please run manually:"
            echo "   sudo -u postgres psql"
            echo "   CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';"
            exit 1
        }
    }
fi

# Grant privileges
echo "🔐 Granting privileges..."
psql -d postgres -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;" 2>/dev/null || {
    sudo -u postgres psql -d postgres -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;"
}
psql -d "$DB_NAME" -c "GRANT ALL ON SCHEMA public TO $DB_USER;" 2>/dev/null || {
    sudo -u postgres psql -d "$DB_NAME" -c "GRANT ALL ON SCHEMA public TO $DB_USER;"
}

# Run migrations
echo "📝 Running migrations..."

# Initial schema
echo "  → Running initial_schema.sql..."
PGPASSWORD="$DB_PASSWORD" psql -d "$DB_NAME" -U "$DB_USER" -f migrations/initial_schema.sql

# Schema migration
echo "  → Running schema_migration.sql..."
PGPASSWORD="$DB_PASSWORD" psql -d "$DB_NAME" -U "$DB_USER" -f migrations/schema_migration.sql

echo ""
echo "✅ Database setup complete!"
echo ""
echo "📋 Connection string:"
echo "   postgresql://$DB_USER:$DB_PASSWORD@localhost:5432/$DB_NAME?sslmode=disable"
