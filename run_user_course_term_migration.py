#!/usr/bin/env python3
"""
Run the add_user_course_term migration.
Creates: tbl_user_course_term (course-term linkage for self-testing).

Prerequisites: tbl_user_course, tbl_term must exist.
  Local: python run_user_course_term_migration.py
  Heroku: heroku run python run_user_course_term_migration.py -a linguaformula-backend
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
    migration_path = os.path.join(os.path.dirname(__file__), "migrations", "add_user_course_term.sql")
    if not os.path.exists(migration_path):
        print(f"ERROR: Migration file not found: {migration_path}")
        sys.exit(1)

    conn = psycopg2.connect(db_url, sslmode=sslmode)
    conn.autocommit = False
    cur = conn.cursor()

    cur.execute(
        "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'tbl_user_course_term');"
    )
    if cur.fetchone()[0]:
        print("tbl_user_course_term already exists. Migration may have been run. Skipping.")
        conn.close()
        return

    with open(migration_path, "r") as f:
        sql = f.read()
    cur.execute(sql)
    conn.commit()
    cur.close()
    conn.close()
    print("Migration completed: tbl_user_course_term created.")


if __name__ == "__main__":
    run()
