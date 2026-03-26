#!/usr/bin/env python3
"""
Migrate complete dataset from physics_web_app database to linguaformula database
This script exports all data from the old database and imports it into the new one.
"""
import psycopg2
import sys
import os
from psycopg2.extras import execute_values

# Source database (physics_web_app) - can be overridden by command line argument
SOURCE_DB_NAME_DEFAULT = "physics_web_app_3"
# Try PGPASSWORD first, then SOURCE_DB_PASSWORD, then default
SOURCE_DB_USER = os.environ.get("SOURCE_DB_USER", os.environ.get("PGUSER", "postgres"))
SOURCE_DB_PASSWORD = os.environ.get("PGPASSWORD") or os.environ.get("SOURCE_DB_PASSWORD") or "dev123"
SOURCE_DB_HOST = os.environ.get("SOURCE_DB_HOST", "localhost")
SOURCE_DB_PORT = os.environ.get("SOURCE_DB_PORT", "5432")

# Target database (linguaformula)
TARGET_DB_NAME = "linguaformula"
TARGET_DB_USER = os.environ.get("TARGET_DB_USER", "dev_user")
TARGET_DB_PASSWORD = os.environ.get("TARGET_DB_PASSWORD", "dev123")
TARGET_DB_HOST = os.environ.get("TARGET_DB_HOST", "localhost")
TARGET_DB_PORT = os.environ.get("TARGET_DB_PORT", "5432")

def get_connection(db_name, db_user, db_password, db_host, db_port):
    """Create a database connection"""
    try:
        conn = psycopg2.connect(
            host=db_host,
            port=db_port,
            database=db_name,
            user=db_user,
            password=db_password
        )
        return conn
    except psycopg2.OperationalError as e:
        if "password authentication failed" in str(e):
            print(f"❌ Password authentication failed for database {db_name}")
            print(f"   User: {db_user}")
            print(f"   💡 Set the correct password:")
            print(f"      export PGPASSWORD=your_password")
            print(f"      export SOURCE_DB_PASSWORD=your_password")
            print(f"   💡 Or set a different user:")
            print(f"      export SOURCE_DB_USER=postgres")
        else:
            print(f"❌ Error connecting to database {db_name}: {e}")
        return None
    except psycopg2.Error as e:
        print(f"❌ Error connecting to database {db_name}: {e}")
        return None

def get_table_columns(conn, table_name):
    """Get column names for a table"""
    cursor = conn.cursor()
    cursor.execute(f"""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name = %s 
        ORDER BY ordinal_position;
    """, (table_name,))
    columns = [row[0] for row in cursor.fetchall()]
    cursor.close()
    return columns

def export_table_data(conn, table_name):
    """Export all data from a table"""
    cursor = conn.cursor()
    columns = get_table_columns(conn, table_name)
    
    if not columns:
        cursor.close()
        return None, None
    
    column_list = ", ".join(columns)
    cursor.execute(f"SELECT {column_list} FROM {table_name};")
    rows = cursor.fetchall()
    cursor.close()
    
    return columns, rows

def import_table_data(conn, table_name, columns, rows, clear_existing=False):
    """Import data into a table"""
    if not rows:
        return 0
    
    cursor = conn.cursor()
    
    # Clear existing data if requested
    if clear_existing:
        cursor.execute(f"TRUNCATE TABLE {table_name} CASCADE;")
        print(f"    Cleared existing data from {table_name}")
    
    # Build INSERT statement
    column_list = ", ".join(columns)
    placeholders = ", ".join(["%s"] * len(columns))
    
    # Use execute_values for bulk insert
    insert_query = f"INSERT INTO {table_name} ({column_list}) VALUES %s ON CONFLICT DO NOTHING;"
    
    try:
        execute_values(cursor, insert_query, rows)
        conn.commit()
        count = cursor.rowcount
        cursor.close()
        return count
    except psycopg2.Error as e:
        conn.rollback()
        cursor.close()
        print(f"    ⚠️  Error importing {table_name}: {e}")
        # Try with individual inserts for better error handling
        return import_table_data_individual(conn, table_name, columns, rows)

def import_table_data_individual(conn, table_name, columns, rows):
    """Import data row by row (fallback method)"""
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
        except psycopg2.Error as e:
            print(f"    ⚠️  Skipped row due to error: {e}")
            continue
    
    conn.commit()
    cursor.close()
    return count

def migrate_table(source_conn, target_conn, table_name, clear_existing=False):
    """Migrate a single table from source to target"""
    print(f"  → Migrating {table_name}...")
    
    # Export from source
    columns, rows = export_table_data(source_conn, table_name)
    
    if columns is None:
        print(f"    ⚠️  Table {table_name} not found in source database")
        return 0
    
    if not rows:
        print(f"    ℹ️  Table {table_name} is empty")
        return 0
    
    # Import to target
    count = import_table_data(target_conn, table_name, columns, rows, clear_existing)
    print(f"    ✅ Imported {count} rows into {table_name}")
    return count

def update_sequences(target_conn):
    """Update sequences to match the highest IDs"""
    cursor = target_conn.cursor()
    
    # Update formula sequence
    cursor.execute("SELECT setval('formula_id_seq', (SELECT MAX(id) FROM formula));")
    
    # Update application sequence if table exists
    try:
        cursor.execute("SELECT setval('application_id_seq', COALESCE((SELECT MAX(id) FROM application), 1));")
    except:
        pass
    
    target_conn.commit()
    cursor.close()
    print("  ✅ Updated sequences")

def main():
    print("🔄 Migrating data from physics_web_app to linguaformula...")
    print()
    
    # Get source database name if provided
    if len(sys.argv) > 1:
        SOURCE_DB_NAME = sys.argv[1]
        print(f"📋 Source database: {SOURCE_DB_NAME}")
    else:
        SOURCE_DB_NAME = os.environ.get("SOURCE_DB_NAME", SOURCE_DB_NAME_DEFAULT)
        print(f"📋 Source database: {SOURCE_DB_NAME} (default)")
        print("   💡 You can specify a different database: python3 migrate_from_physics_app.py <db_name>")
        print("   💡 Or set SOURCE_DB_NAME environment variable")
    
    print(f"📋 Target database: {TARGET_DB_NAME}")
    print()
    
    # Connect to databases
    print("🔌 Connecting to databases...")
    print(f"   Source: {SOURCE_DB_NAME} as {SOURCE_DB_USER}")
    print(f"   Target: {TARGET_DB_NAME} as {TARGET_DB_USER}")
    
    if not SOURCE_DB_PASSWORD or SOURCE_DB_PASSWORD == "dev123":
        print()
        print("⚠️  Using default password. If connection fails, set:")
        print("   export PGPASSWORD=your_postgres_password")
        print("   export SOURCE_DB_PASSWORD=your_postgres_password")
        print()
    
    source_conn = get_connection(SOURCE_DB_NAME, SOURCE_DB_USER, SOURCE_DB_PASSWORD, 
                                 SOURCE_DB_HOST, SOURCE_DB_PORT)
    if not source_conn:
        print()
        print(f"❌ Failed to connect to source database: {SOURCE_DB_NAME}")
        print()
        print("💡 Troubleshooting:")
        print("   1. Set the correct password:")
        print("      export PGPASSWORD=your_postgres_password")
        print("   2. Or set specific source credentials:")
        print("      export SOURCE_DB_USER=postgres")
        print("      export SOURCE_DB_PASSWORD=your_password")
        print("   3. Verify database exists:")
        print("      psql -l | grep physics")
        print("   4. Try connecting manually:")
        print(f"      psql -d {SOURCE_DB_NAME} -U {SOURCE_DB_USER}")
        sys.exit(1)
    
    target_conn = get_connection(TARGET_DB_NAME, TARGET_DB_USER, TARGET_DB_PASSWORD,
                                 TARGET_DB_HOST, TARGET_DB_PORT)
    if not target_conn:
        print(f"❌ Failed to connect to target database: {TARGET_DB_NAME}")
        sys.exit(1)
    
    print("✅ Connected to both databases")
    print()
    
    # Tables to migrate (in order to respect foreign key constraints)
    tables_to_migrate = [
        ("formula", True),  # (table_name, clear_existing)
        ("application", True),
        ("application_formula", True),
        # Add other tables if they exist
        ("formula_variables", True),
        ("formula_relationships", True),
        ("formula_keywords", True),
        ("formula_examples", True),
        ("formula_prerequisites", True),
    ]
    
    total_rows = 0
    
    # Migrate each table
    for table_name, clear_existing in tables_to_migrate:
        try:
            count = migrate_table(source_conn, target_conn, table_name, clear_existing)
            total_rows += count
        except Exception as e:
            print(f"    ❌ Error migrating {table_name}: {e}")
            continue
    
    # Update sequences
    print()
    print("🔄 Updating sequences...")
    update_sequences(target_conn)
    
    # Close connections
    source_conn.close()
    target_conn.close()
    
    print()
    print("✅ Migration complete!")
    print(f"📊 Total rows migrated: {total_rows}")
    print()
    print("💡 Verify the migration:")
    print(f"   psql -d {TARGET_DB_NAME} -U {TARGET_DB_USER} -c \"SELECT COUNT(*) FROM formula;\"")
    print(f"   psql -d {TARGET_DB_NAME} -U {TARGET_DB_USER} -c \"SELECT COUNT(*) FROM application;\"")
    print()
    print("🌐 Refresh your browser at http://localhost:3000 to see the imported data")

if __name__ == "__main__":
    main()
