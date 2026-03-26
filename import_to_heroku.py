#!/usr/bin/env python3
"""
Import data from local database to Heroku database
"""
import psycopg2
import sys
import os
from psycopg2.extras import execute_values

# Source: Local database
SOURCE_DB_NAME = "linguaformula"
SOURCE_DB_USER = "dev_user"
SOURCE_DB_PASSWORD = "dev123"

# Target: Heroku database (from environment)
TARGET_DATABASE_URL = os.environ.get("HEROKU_DATABASE_URL")
if not TARGET_DATABASE_URL:
    print("❌ HEROKU_DATABASE_URL not set")
    print("   Get it with: heroku config:get DATABASE_URL -a linguaformula-backend")
    sys.exit(1)

def get_connection(db_name, db_user, db_password):
    """Create local database connection"""
    try:
        conn = psycopg2.connect(
            host="localhost",
            port="5432",
            database=db_name,
            user=db_user,
            password=db_password
        )
        return conn
    except Exception as e:
        print(f"❌ Error connecting to local database: {e}")
        return None

def get_heroku_connection(database_url):
    """Create Heroku database connection"""
    try:
        conn = psycopg2.connect(database_url, sslmode='require')
        return conn
    except Exception as e:
        print(f"❌ Error connecting to Heroku database: {e}")
        return None

def export_table_data(conn, table_name):
    """Export all data from a table"""
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM {table_name};")
    rows = cursor.fetchall()
    
    # Get column names
    column_names = [desc[0] for desc in cursor.description]
    cursor.close()
    
    return column_names, rows

def import_table_data(conn, table_name, columns, rows):
    """Import data into a table"""
    if not rows:
        return 0
    
    cursor = conn.cursor()
    column_list = ", ".join(columns)
    placeholders = ", ".join(["%s"] * len(columns))
    
    insert_query = f"INSERT INTO {table_name} ({column_list}) VALUES ({placeholders}) ON CONFLICT DO NOTHING;"
    
    count = 0
    for row in rows:
        try:
            cursor.execute(insert_query, row)
            if cursor.rowcount > 0:
                count += 1
        except Exception as e:
            print(f"    ⚠️  Skipped row: {e}")
            continue
    
    conn.commit()
    cursor.close()
    return count

def migrate_table(source_conn, target_conn, table_name):
    """Migrate a single table"""
    print(f"  → Migrating {table_name}...")
    
    columns, rows = export_table_data(source_conn, table_name)
    
    if not rows:
        print(f"    ℹ️  Table {table_name} is empty")
        return 0
    
    count = import_table_data(target_conn, table_name, columns, rows)
    print(f"    ✅ Imported {count} rows")
    return count

def update_sequences(target_conn):
    """Update sequences"""
    cursor = target_conn.cursor()
    cursor.execute("SELECT setval('formula_id_seq', COALESCE((SELECT MAX(id) FROM formula), 1));")
    cursor.execute("SELECT setval('application_id_seq', COALESCE((SELECT MAX(id) FROM application), 1));")
    target_conn.commit()
    cursor.close()
    print("  ✅ Updated sequences")

def main():
    print("🔄 Importing data from local to Heroku...")
    print()
    
    # Connect to databases
    source_conn = get_connection(SOURCE_DB_NAME, SOURCE_DB_USER, SOURCE_DB_PASSWORD)
    if not source_conn:
        sys.exit(1)
    
    target_conn = get_heroku_connection(TARGET_DATABASE_URL)
    if not target_conn:
        sys.exit(1)
    
    print("✅ Connected to both databases")
    print()
    
    # Migrate tables
    tables = ["formula", "application", "application_formula"]
    total = 0
    
    for table in tables:
        try:
            count = migrate_table(source_conn, target_conn, table)
            total += count
        except Exception as e:
            print(f"    ❌ Error: {e}")
    
    # Update sequences
    print()
    print("🔄 Updating sequences...")
    update_sequences(target_conn)
    
    # Close connections
    source_conn.close()
    target_conn.close()
    
    print()
    print(f"✅ Import complete! Total rows: {total}")

if __name__ == "__main__":
    main()
