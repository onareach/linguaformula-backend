#!/usr/bin/env python3
"""
Setup Heroku database schema and import data
"""
import psycopg2
import os
import sys

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    print("❌ DATABASE_URL not found")
    sys.exit(1)

# Initial schema SQL (includes enhancements from schema_migration)
INITIAL_SCHEMA = """
CREATE TABLE IF NOT EXISTS formula (
    id SERIAL PRIMARY KEY,
    formula_name VARCHAR(100) NOT NULL,
    latex TEXT NOT NULL,
    display_order INTEGER,
    formula_description TEXT,
    english_verbalization TEXT,
    category VARCHAR(50),
    difficulty_level VARCHAR(20),
    assumptions TEXT,
    formula_expression TEXT,
    output_target VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS application (
    id SERIAL PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    problem_text TEXT NOT NULL,
    subject_area VARCHAR(50),
    image_filename VARCHAR(255),
    image_data BYTEA,
    image_text TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS application_formula (
    application_id INTEGER NOT NULL REFERENCES application(id) ON DELETE CASCADE,
    formula_id INTEGER NOT NULL REFERENCES formula(id) ON DELETE CASCADE,
    relevance_score FLOAT,
    variable_mapping JSONB,
    solution_steps TEXT,
    confidence_score FLOAT,
    missing_variables TEXT[],
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (application_id, formula_id)
);

CREATE INDEX IF NOT EXISTS idx_formula_display_order ON formula(display_order);
CREATE INDEX IF NOT EXISTS idx_formula_name ON formula(formula_name);
CREATE INDEX IF NOT EXISTS idx_application_subject_area ON application(subject_area);
CREATE INDEX IF NOT EXISTS idx_application_formula_app_id ON application_formula(application_id);
CREATE INDEX IF NOT EXISTS idx_application_formula_formula_id ON application_formula(formula_id);
"""

def main():
    print("🔄 Setting up Heroku database...")
    
    conn = psycopg2.connect(DATABASE_URL, sslmode='require')
    cursor = conn.cursor()
    
    # Execute schema creation
    print("  → Creating tables...")
    # Split by semicolons and execute each statement
    statements = [s.strip() for s in INITIAL_SCHEMA.split(';') if s.strip() and not s.strip().startswith('--')]
    for statement in statements:
        if statement:
            try:
                cursor.execute(statement)
            except Exception as e:
                # Ignore "already exists" errors
                if "already exists" not in str(e).lower():
                    print(f"    ⚠️  {e}")
    conn.commit()
    
    # Add additional columns if they don't exist (from schema_migration)
    print("  → Adding enhancement columns...")
    try:
        cursor.execute("ALTER TABLE formula ADD COLUMN IF NOT EXISTS category VARCHAR(50);")
        cursor.execute("ALTER TABLE formula ADD COLUMN IF NOT EXISTS difficulty_level VARCHAR(20);")
        cursor.execute("ALTER TABLE formula ADD COLUMN IF NOT EXISTS assumptions TEXT;")
        cursor.execute("ALTER TABLE formula ADD COLUMN IF NOT EXISTS formula_expression TEXT;")
        cursor.execute("ALTER TABLE formula ADD COLUMN IF NOT EXISTS output_target VARCHAR(100);")
        cursor.execute("ALTER TABLE application_formula ADD COLUMN IF NOT EXISTS variable_mapping JSONB;")
        cursor.execute("ALTER TABLE application_formula ADD COLUMN IF NOT EXISTS solution_steps TEXT;")
        cursor.execute("ALTER TABLE application_formula ADD COLUMN IF NOT EXISTS confidence_score FLOAT;")
        cursor.execute("ALTER TABLE application_formula ADD COLUMN IF NOT EXISTS missing_variables TEXT[];")
        conn.commit()
    except Exception as e:
        print(f"    ⚠️  {e}")
    
    # Check if tables exist
    cursor.execute("""
        SELECT COUNT(*) FROM information_schema.tables 
        WHERE table_name IN ('formula', 'application', 'application_formula');
    """)
    table_count = cursor.fetchone()[0]
    
    cursor.close()
    conn.close()
    
    print(f"  ✅ Database setup complete! Tables found: {table_count}")
    
    if table_count == 3:
        print("  ✅ All tables created successfully")
    else:
        print("  ⚠️  Some tables may be missing")

if __name__ == "__main__":
    main()
