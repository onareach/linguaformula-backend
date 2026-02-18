#!/usr/bin/env python3
"""
Run add_constants_and_units_tables.sql migration.
Creates tbl_constant and tbl_unit if they don't exist.
"""
import os
import psycopg2

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    DATABASE_URL = "postgresql://dev_user:dev123@localhost:5432/linguaformula?sslmode=disable"

sslmode = "require" if DATABASE_URL.startswith("postgres://") else "disable"
db_url = DATABASE_URL.replace("postgres://", "postgresql://", 1) if DATABASE_URL.startswith("postgres://") else DATABASE_URL

MIGRATION_DIR = os.path.join(os.path.dirname(__file__), "migrations")

def run():
    conn = psycopg2.connect(db_url, sslmode=sslmode)
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM information_schema.tables WHERE table_name = 'tbl_constant';")
    if cur.fetchone():
        print("tbl_constant and tbl_unit already exist. Skipping.")
        cur.close()
        conn.close()
        return
    path = os.path.join(MIGRATION_DIR, "add_constants_and_units_tables.sql")
    with open(path) as f:
        cur.execute(f.read())
    conn.commit()
    cur.close()
    conn.close()
    print("Migration completed: tbl_constant and tbl_unit created.")

if __name__ == "__main__":
    run()
