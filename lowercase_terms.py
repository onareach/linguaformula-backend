#!/usr/bin/env python3
"""
Lowercase all term names in tbl_term.
  Local: python3 lowercase_terms.py
  Heroku: heroku run python3 lowercase_terms.py -a linguaformula-backend
"""
import os

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
    import psycopg2

    conn = psycopg2.connect(db_url, sslmode=sslmode)
    cur = conn.cursor()
    cur.execute("UPDATE tbl_term SET term_name = LOWER(term_name);")
    n = cur.rowcount
    conn.commit()
    cur.close()
    conn.close()
    print("Lowercased %d term(s) in tbl_term." % n)


if __name__ == "__main__":
    run()
