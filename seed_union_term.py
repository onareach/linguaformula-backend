#!/usr/bin/env python3
"""
Add the term "union" with formulaic expression A \cup B for testing.
Run after: migrations/add_terms_tables.sql, migrations/add_term_formulaic_expression.sql
  Local: python seed_union_term.py
  Heroku: heroku run python seed_union_term.py -a linguaformula-backend
"""
import os
import sys

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

    cur.execute("SELECT term_id FROM tbl_term WHERE term_name = %s;", ("union",))
    existing = cur.fetchone()
    if existing:
        cur.execute(
            "UPDATE tbl_term SET formulaic_expression = %s WHERE term_id = %s;",
            (r"A \cup B", existing[0]),
        )
        conn.commit()
        print("Term 'union' already existed. Updated formulaic_expression to A \\cup B.")
        cur.close()
        conn.close()
        return

    cur.execute("SELECT discipline_id FROM tbl_discipline WHERE discipline_handle = %s;", ("statistics",))
    row = cur.fetchone()
    if not row:
        cur.execute("SELECT discipline_id FROM tbl_discipline WHERE discipline_handle = %s;", ("combinatorics",))
        row = cur.fetchone()
    if not row:
        print("ERROR: No statistics or combinatorics discipline found.")
        sys.exit(1)
    discipline_id = row[0]

    cur.execute(
        """
        INSERT INTO tbl_term (term_name, definition, display_order, formulaic_expression)
        VALUES (%s, %s, %s, %s) RETURNING term_id;
        """,
        ("union", "the set of all elements that are in set A or in set B (or both).", 10, r"A \cup B"),
    )
    term_id = cur.fetchone()[0]
    cur.execute(
        """
        INSERT INTO tbl_term_discipline (term_id, discipline_id, term_discipline_is_primary)
        VALUES (%s, %s, true);
        """,
        (term_id, discipline_id),
    )
    conn.commit()
    cur.close()
    conn.close()
    print("Added term 'union' with formulaic_expression A \\cup B (id=%s)." % term_id)


if __name__ == "__main__":
    run()
