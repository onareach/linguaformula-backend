#!/usr/bin/env python3
"""
Export all data from tbl_formula to a JSON file.
"""
import os
import sys
import json
import psycopg2
from datetime import datetime

# Get database URL from environment or use defaults
DATABASE_URL = os.environ.get('DATABASE_URL')

if not DATABASE_URL:
    # Default to local database
    DB_NAME = os.environ.get('DB_NAME', 'linguaformula')
    DB_USER = os.environ.get('DB_USER', 'dev_user')
    DB_PASSWORD = os.environ.get('DB_PASSWORD') or os.environ.get('PGPASSWORD')
    DB_HOST = os.environ.get('DB_HOST', 'localhost')
    DB_PORT = os.environ.get('DB_PORT', '5432')
    
    if not DB_PASSWORD:
        try:
            DB_PASSWORD = input(f"Enter password for database user '{DB_USER}': ")
        except (EOFError, KeyboardInterrupt):
            print("❌ Password required. Set DB_PASSWORD or PGPASSWORD environment variable.")
            sys.exit(1)
    
    DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

def export_formulas():
    """Export all formulas from tbl_formula to JSON."""
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
        print("Exporting formulas from tbl_formula to JSON")
        print("=" * 70)
        
        # Query all formulas
        cur.execute("""
            SELECT 
                formula_id,
                formula_name,
                latex,
                display_order,
                formula_description,
                english_verbalization,
                created_at,
                updated_at,
                formula_expression,
                symbolic_verbalization,
                example,
                historical_context,
                units
            FROM tbl_formula
            ORDER BY display_order NULLS LAST, formula_id;
        """)
        
        formulas = cur.fetchall()
        
        # Convert to list of dictionaries
        formula_list = []
        for row in formulas:
            formula_dict = {
                "formula_id": row[0],
                "formula_name": row[1],
                "latex": row[2],
                "display_order": row[3],
                "formula_description": row[4],
                "english_verbalization": row[5],
                "created_at": row[6].isoformat() if row[6] else None,
                "updated_at": row[7].isoformat() if row[7] else None,
                "formula_expression": row[8],
                "symbolic_verbalization": row[9],
                "example": row[10],
                "historical_context": row[11],
                "units": row[12]
            }
            formula_list.append(formula_dict)
        
        # Create output filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"tbl_formula_export_{timestamp}.json"
        
        # Write to JSON file
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                "export_date": datetime.now().isoformat(),
                "total_formulas": len(formula_list),
                "formulas": formula_list
            }, f, indent=2, ensure_ascii=False)
        
        print(f"\n✅ Successfully exported {len(formula_list)} formulas")
        print(f"📄 Output file: {output_file}")
        
        cur.close()
        conn.close()
        
        return output_file
        
    except psycopg2.Error as e:
        print(f"\n❌ Database error occurred:")
        print(f"  {e}")
        if conn:
            conn.close()
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        if conn:
            conn.close()
        sys.exit(1)

if __name__ == '__main__':
    export_formulas()
