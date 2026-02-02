#!/usr/bin/env python3
"""
Run database migrations on Heroku
This script reads SQL files and executes them on the Heroku database
"""
import os
import psycopg2
import sys

# Get DATABASE_URL from environment (set by Heroku)
DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    print("❌ DATABASE_URL not found in environment")
    sys.exit(1)

def run_sql_file(conn, filepath):
    """Execute SQL commands from a file"""
    with open(filepath, 'r') as f:
        sql = f.read()
    
    # Split by semicolons and execute each statement
    cursor = conn.cursor()
    statements = [s.strip() for s in sql.split(';') if s.strip() and not s.strip().startswith('--')]
    
    for statement in statements:
        if statement:
            try:
                cursor.execute(statement)
            except Exception as e:
                # Ignore "already exists" errors
                if "already exists" not in str(e).lower() and "duplicate" not in str(e).lower():
                    print(f"⚠️  Warning: {e}")
    
    conn.commit()
    cursor.close()

def main():
    print("🔄 Running database migrations on Heroku...")
    
    # Connect to database
    conn = psycopg2.connect(DATABASE_URL, sslmode='require')
    print("✅ Connected to database")
    
    # Get migrations directory
    migrations_dir = os.path.join(os.path.dirname(__file__), "migrations")
    
    # Run migrations in order
    migrations = [
        "initial_schema.sql",
        "schema_migration.sql"
    ]
    
    for migration in migrations:
        filepath = os.path.join(migrations_dir, migration)
        if os.path.exists(filepath):
            print(f"  → Running {migration}...")
            run_sql_file(conn, filepath)
            print(f"    ✅ {migration} completed")
        else:
            print(f"    ⚠️  {migration} not found")
    
    conn.close()
    print("✅ All migrations completed!")

if __name__ == "__main__":
    main()
