#!/usr/bin/env python3
"""
Run the table rename and discipline tables migration.

This script will:
1. Rename 'formula' table to 'tbl_formula'
2. Rename 'id' column to 'formula_id'
3. Add 'symbolic_verbalization' column
4. Create 'tbl_disciplines' and 'tbl_formula_disciplines' tables
5. Update all foreign key references

Usage:
    Local: python run_table_rename_migration.py
    Heroku: heroku run python run_table_rename_migration.py -a linguaformula-backend
"""

import os
import sys
import psycopg2
from psycopg2 import sql

# Get database URL from environment or use defaults
DATABASE_URL = os.environ.get('DATABASE_URL')

if not DATABASE_URL:
    # Default to local database
    DB_NAME = os.environ.get('DB_NAME', 'linguaformula')
    DB_USER = os.environ.get('DB_USER', 'dev_user')
    DB_PASSWORD = os.environ.get('DB_PASSWORD')
    DB_HOST = os.environ.get('DB_HOST', 'localhost')
    DB_PORT = os.environ.get('DB_PORT', '5432')
    
    if not DB_PASSWORD:
        DB_PASSWORD = input(f"Enter password for database user '{DB_USER}': ")
    
    DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

def run_migration():
    """Run the migration script."""
    conn = None
    try:
        # Get database URL from global scope
        db_url = DATABASE_URL
        
        # Parse DATABASE_URL
        if db_url.startswith('postgres://'):
            db_url = db_url.replace('postgres://', 'postgresql://', 1)
        
        conn = psycopg2.connect(db_url)
        conn.autocommit = False  # Use transactions
        cur = conn.cursor()
        
        print("=" * 70)
        print("Starting Table Rename and Discipline Tables Migration")
        print("=" * 70)
        
        # Read the migration SQL file
        migration_file = os.path.join(os.path.dirname(__file__), 'migrations', 'rename_formula_table_and_add_disciplines.sql')
        
        if not os.path.exists(migration_file):
            print(f"ERROR: Migration file not found: {migration_file}")
            sys.exit(1)
        
        print(f"\nReading migration file: {migration_file}")
        with open(migration_file, 'r') as f:
            migration_sql = f.read()
        
        # Check if migration has already been run
        cur.execute("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables 
                WHERE table_name = 'tbl_formula'
            );
        """)
        already_run = cur.fetchone()[0]
        
        if already_run:
            print("\nWARNING: It appears this migration may have already been run.")
            print("Table 'tbl_formula' already exists.")
            response = input("Do you want to continue anyway? (yes/no): ")
            if response.lower() != 'yes':
                print("Migration cancelled.")
                conn.close()
                return
        
        # Check if formula table exists (old name)
        cur.execute("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables 
                WHERE table_name = 'formula'
            );
        """)
        formula_exists = cur.fetchone()[0]
        
        if not formula_exists and not already_run:
            print("\nERROR: Neither 'formula' nor 'tbl_formula' table exists.")
            print("Please run the initial schema migration first.")
            conn.close()
            sys.exit(1)
        
        print("\nExecuting migration...")
        print("This may take a few moments...")
        
        # Execute the migration
        cur.execute(migration_sql)
        
        # Commit the transaction
        conn.commit()
        
        print("\n" + "=" * 70)
        print("Migration completed successfully!")
        print("=" * 70)
        
        # Verify the migration
        print("\nVerifying migration...")
        
        # Check tbl_formula exists
        cur.execute("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables 
                WHERE table_name = 'tbl_formula'
            );
        """)
        if cur.fetchone()[0]:
            print("✓ tbl_formula table exists")
        else:
            print("✗ tbl_formula table NOT found")
        
        # Check formula_id column exists
        cur.execute("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name = 'tbl_formula' AND column_name = 'formula_id'
            );
        """)
        if cur.fetchone()[0]:
            print("✓ formula_id column exists")
        else:
            print("✗ formula_id column NOT found")
        
        # Check symbolic_verbalization column exists
        cur.execute("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name = 'tbl_formula' AND column_name = 'symbolic_verbalization'
            );
        """)
        if cur.fetchone()[0]:
            print("✓ symbolic_verbalization column exists")
        else:
            print("✗ symbolic_verbalization column NOT found")
        
        # Check new tables exist
        for table in ['tbl_disciplines', 'tbl_formula_disciplines']:
            cur.execute("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.tables 
                    WHERE table_name = %s
                );
            """, (table,))
            if cur.fetchone()[0]:
                print(f"✓ {table} table exists")
            else:
                print(f"✗ {table} table NOT found")
        
        # Count records in tbl_formula
        cur.execute("SELECT COUNT(*) FROM tbl_formula")
        count = cur.fetchone()[0]
        print(f"\nTotal formulas in tbl_formula: {count}")
        
        cur.close()
        conn.close()
        
        print("\nMigration verification complete!")
        
    except psycopg2.Error as e:
        print(f"\nERROR: Database error occurred:")
        print(f"  {e}")
        if conn:
            conn.rollback()
            conn.close()
        sys.exit(1)
    except Exception as e:
        print(f"\nERROR: {e}")
        if conn:
            conn.rollback()
            conn.close()
        sys.exit(1)

if __name__ == '__main__':
    run_migration()
