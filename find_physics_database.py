#!/usr/bin/env python3
"""
Helper script to find the physics_web_app database
"""
import psycopg2
import sys
import os

def list_databases():
    """List all PostgreSQL databases"""
    db_user = os.environ.get("DB_USER", os.environ.get("PGUSER", "postgres"))
    db_password = os.environ.get("DB_PASSWORD", os.environ.get("PGPASSWORD", ""))
    
    try:
        # Connect to default postgres database
        conn = psycopg2.connect(
            host=os.environ.get("DB_HOST", "localhost"),
            port=os.environ.get("DB_PORT", "5432"),
            database="postgres",
            user=db_user,
            password=db_password
        )
        cursor = conn.cursor()
        cursor.execute("""
            SELECT datname FROM pg_database 
            WHERE datistemplate = false 
            AND datname NOT IN ('postgres')
            ORDER BY datname;
        """)
        databases = [row[0] for row in cursor.fetchall()]
        cursor.close()
        conn.close()
        return databases
    except psycopg2.OperationalError as e:
        if "password authentication failed" in str(e) or "no password supplied" in str(e):
            print(f"⚠️  Password authentication required")
            print(f"   💡 Set PGPASSWORD environment variable:")
            print(f"      export PGPASSWORD=your_postgres_password")
            print(f"   💡 Or set DB_PASSWORD:")
            print(f"      export DB_PASSWORD=your_postgres_password")
        else:
            print(f"❌ Error connecting to PostgreSQL: {e}")
        return []
    except Exception as e:
        print(f"❌ Error connecting to PostgreSQL: {e}")
        return []

def check_table_exists(db_name, table_name):
    """Check if a table exists in a database"""
    db_user = os.environ.get("DB_USER", os.environ.get("PGUSER", "postgres"))
    db_password = os.environ.get("DB_PASSWORD", os.environ.get("PGPASSWORD", ""))
    
    try:
        conn = psycopg2.connect(
            host=os.environ.get("DB_HOST", "localhost"),
            port=os.environ.get("DB_PORT", "5432"),
            database=db_name,
            user=db_user,
            password=db_password
        )
        cursor = conn.cursor()
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = %s
            );
        """, (table_name,))
        exists = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        return exists
    except:
        return False

def count_rows(db_name, table_name):
    """Count rows in a table"""
    db_user = os.environ.get("DB_USER", os.environ.get("PGUSER", "postgres"))
    db_password = os.environ.get("DB_PASSWORD", os.environ.get("PGPASSWORD", ""))
    
    try:
        conn = psycopg2.connect(
            host=os.environ.get("DB_HOST", "localhost"),
            port=os.environ.get("DB_PORT", "5432"),
            database=db_name,
            user=db_user,
            password=db_password
        )
        cursor = conn.cursor()
        cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
        count = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        return count
    except:
        return None

def main():
    print("🔍 Finding physics_web_app database...")
    print()
    
    # Check if password is set
    if not os.environ.get("PGPASSWORD") and not os.environ.get("DB_PASSWORD"):
        print("⚠️  No password set. Trying to connect...")
        print("   💡 If connection fails, set PGPASSWORD:")
        print("      export PGPASSWORD=your_postgres_password")
        print()
    
    databases = list_databases()
    
    if not databases:
        print()
        print("❌ No databases found or couldn't connect")
        print()
        print("💡 To fix this:")
        print("   1. Set your PostgreSQL password:")
        print("      export PGPASSWORD=your_postgres_password")
        print("   2. Or set specific credentials:")
        print("      export DB_USER=postgres")
        print("      export DB_PASSWORD=your_password")
        print("   3. Then run the script again")
        return
    
    print(f"📋 Found {len(databases)} database(s):")
    print()
    
    physics_dbs = []
    for db in databases:
        print(f"  • {db}")
        if "physics" in db.lower() or "formula" in db.lower():
            physics_dbs.append(db)
    
    print()
    
    if physics_dbs:
        print("🎯 Potential source databases:")
        for db in physics_dbs:
            if check_table_exists(db, "formula"):
                formula_count = count_rows(db, "formula")
                app_count = count_rows(db, "application") if check_table_exists(db, "application") else 0
                print(f"  ✅ {db}")
                print(f"     - Has 'formula' table: {formula_count} rows")
                if app_count > 0:
                    print(f"     - Has 'application' table: {app_count} rows")
                print()
    else:
        print("⚠️  No databases with 'physics' or 'formula' in the name found")
        print()
        print("💡 To check a specific database manually:")
        print("   python3 migrate_from_physics_app.py <database_name>")

if __name__ == "__main__":
    main()
