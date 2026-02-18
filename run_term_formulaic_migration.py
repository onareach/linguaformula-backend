#!/usr/bin/env python3
"""
Run the add_term_formulaic_expression migration.
Adds formulaic_expression column to tbl_term.

  Local: python run_term_formulaic_migration.py
  Heroku: heroku run python run_term_formulaic_migration.py -a linguaformula-backend
"""

import os
import sys
import psycopg2

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    DATABASE_URL = "postgresql://dev_user:dev123@localhost:5432/linguaformula?sslmode=disable"

sslmode = "require" if DATABASE_URL.startswith("postgres://") else "disable"
db_url = (
    DATABASE_URL.replace("postgres://", "postgresql://", 1)
    if DATABASE_URL.startswith("postgres://")
    else DATABASE_URL
)


def run():
    migration_path = os.path.join(os.path.dirname(__file__), "migrations", "add_term_formulaic_expression.sql")
    if not os.path.exists(migration_path):
        print(f"ERROR: Migration file not found: {migration_path}")
        sys.exit(1)

    conn = psycopg2.connect(db_url, sslmode=sslmode)
    conn.autocommit = False
    cur = conn.cursor()

    cur.execute("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name = 'tbl_term' AND column_name = 'formulaic_expression';
    """)
    if cur.fetchone():
        print("formulaic_expression column already exists. Skipping.")
        conn.close()
        return

    with open(migration_path, "r") as f:
        sql = f.read()
    cur.execute(sql)
    conn.commit()
    cur.close()
    conn.close()
    print("Migration completed: formulaic_expression column added to tbl_term.")


if __name__ == "__main__":
    run()
