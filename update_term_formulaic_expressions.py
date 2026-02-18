#!/usr/bin/env python3
"""
Update formulaic_expression for terms that have standard symbols.
  population size -> N
  sample size -> n
  union -> A \\cup B (already set by seed_union_term.py)

Run: python3 update_term_formulaic_expressions.py
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

# term_name -> formulaic_expression (LaTeX)
TERM_FORMULAIC = {
    "population size": r"N",
    "sample size": r"n",
    "union": r"A \cup B",
}


def run():
    import psycopg2

    conn = psycopg2.connect(db_url, sslmode=sslmode)
    cur = conn.cursor()
    for term_name, expr in TERM_FORMULAIC.items():
        cur.execute(
            "UPDATE tbl_term SET formulaic_expression = %s WHERE term_name = %s RETURNING term_id;",
            (expr, term_name),
        )
        row = cur.fetchone()
        if row:
            print(f"  Updated '{term_name}' -> {expr}")
        else:
            print(f"  (No term '{term_name}' found)")
    conn.commit()
    cur.close()
    conn.close()
    print("Done.")


if __name__ == "__main__":
    run()
