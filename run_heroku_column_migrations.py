#!/usr/bin/env python3
"""
Run column addition migrations on Heroku database.
Adds units, example, and historical_context columns to tbl_formula.
"""
import os
import sys
import psycopg2

# Get DATABASE_URL from environment (set by Heroku)
DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    print("❌ DATABASE_URL not found in environment")
    print("   This script should be run on Heroku with: heroku run python run_heroku_column_migrations.py")
    sys.exit(1)

def run_migrations():
    """Run migrations to add new columns to tbl_formula."""
    conn = None
    try:
        # Parse DATABASE_URL
        if DATABASE_URL.startswith('postgres://'):
            db_url = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
        else:
            db_url = DATABASE_URL
        
        # Determine SSL mode
        sslmode = "require" if DATABASE_URL.startswith("postgres://") else "disable"
        
        conn = psycopg2.connect(db_url, sslmode=sslmode)
        cur = conn.cursor()
        
        print("=" * 70)
        print("Running column migrations on Heroku database")
        print("=" * 70)
        
        # Add units column
        print("\n1. Adding 'units' column...")
        try:
            cur.execute("ALTER TABLE tbl_formula ADD COLUMN IF NOT EXISTS units TEXT;")
            conn.commit()
            print("   ✅ 'units' column added")
        except Exception as e:
            if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
                print("   ⏭️  'units' column already exists")
            else:
                raise
        
        # Add example column
        print("\n2. Adding 'example' column...")
        try:
            cur.execute("ALTER TABLE tbl_formula ADD COLUMN IF NOT EXISTS example TEXT;")
            conn.commit()
            print("   ✅ 'example' column added")
        except Exception as e:
            if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
                print("   ⏭️  'example' column already exists")
            else:
                raise
        
        # Add historical_context column
        print("\n3. Adding 'historical_context' column...")
        try:
            cur.execute("ALTER TABLE tbl_formula ADD COLUMN IF NOT EXISTS historical_context TEXT;")
            conn.commit()
            print("   ✅ 'historical_context' column added")
        except Exception as e:
            if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
                print("   ⏭️  'historical_context' column already exists")
            else:
                raise
        
        # Verify columns exist
        print("\n4. Verifying columns...")
        cur.execute("""
            SELECT column_name, data_type, is_nullable 
            FROM information_schema.columns 
            WHERE table_name = 'tbl_formula' 
              AND column_name IN ('units', 'example', 'historical_context')
            ORDER BY column_name;
        """)
        columns = cur.fetchall()
        
        if len(columns) == 3:
            print("   ✅ All columns verified:")
            for col_name, data_type, is_nullable in columns:
                print(f"      - {col_name}: {data_type} (nullable: {is_nullable})")
        else:
            print(f"   ⚠️  Expected 3 columns, found {len(columns)}")
            for col_name, data_type, is_nullable in columns:
                print(f"      - {col_name}: {data_type} (nullable: {is_nullable})")
        
        cur.close()
        conn.close()
        
        print("\n" + "=" * 70)
        print("✅ Migrations completed successfully!")
        print("=" * 70)
        
    except psycopg2.Error as e:
        print(f"\n❌ Database error occurred:")
        print(f"  {e}")
        if conn:
            conn.rollback()
            conn.close()
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        if conn:
            conn.rollback()
            conn.close()
        sys.exit(1)

if __name__ == "__main__":
    run_migrations()
