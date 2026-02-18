#!/usr/bin/env python3
"""
Move 9 formula items (that are really terms) from tbl_formula to tbl_term.
- Inserts into tbl_term with formulaic_expression from latex
- Copies discipline links from tbl_formula_discipline to tbl_term_discipline
- Copies question links from tbl_formula_question to tbl_term_question
- Deletes the formulas (CASCADE cleans tbl_formula_discipline, tbl_formula_question)

Formula IDs to move: 100, 144, 145, 146, 148, 149, 150, 151, 170

Run: python3 migrate_formulas_to_terms.py
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

FORMULA_IDS = [100, 144, 145, 146, 148, 149, 150, 151, 170]


def run():
    import psycopg2

    conn = psycopg2.connect(db_url, sslmode=sslmode)
    cur = conn.cursor()

    for formula_id in FORMULA_IDS:
        cur.execute(
            """
            SELECT formula_id, formula_name, formula_description, english_verbalization, latex
            FROM tbl_formula WHERE formula_id = %s;
            """,
            (formula_id,),
        )
        row = cur.fetchone()
        if not row:
            print(f"  Skipping formula_id {formula_id} (not found)")
            continue

        _, formula_name, formula_desc, english_verbal, latex = row
        definition = (formula_desc or english_verbal or "").strip()
        if not definition:
            definition = f"Definition of {formula_name}."
        term_name = formula_name.lower()

        cur.execute(
            """
            INSERT INTO tbl_term (term_name, definition, display_order, formulaic_expression)
            VALUES (%s, %s, NULL, %s) RETURNING term_id;
            """,
            (term_name, definition, latex),
        )
        term_id = cur.fetchone()[0]
        print(f"  Added term: {term_name} (id={term_id}) from formula {formula_id}")

        cur.execute(
            """
            SELECT discipline_id, COALESCE(formula_discipline_is_primary, false)
            FROM tbl_formula_discipline WHERE formula_id = %s;
            """,
            (formula_id,),
        )
        disciplines = cur.fetchall()
        has_primary = any(r[1] for r in disciplines)
        for i, (disc_id, fd_primary) in enumerate(disciplines):
            is_primary = fd_primary if has_primary else (i == 0)
            cur.execute(
                """
                INSERT INTO tbl_term_discipline (term_id, discipline_id, term_discipline_is_primary)
                VALUES (%s, %s, %s)
                ON CONFLICT (term_id, discipline_id) DO NOTHING;
                """,
                (term_id, disc_id, is_primary),
            )

        cur.execute(
            """
            SELECT question_id, formula_question_is_primary
            FROM tbl_formula_question WHERE formula_id = %s;
            """,
            (formula_id,),
        )
        questions = cur.fetchall()
        for i, (qid, _) in enumerate(questions):
            is_primary = i == 0
            cur.execute(
                """
                INSERT INTO tbl_term_question (term_id, question_id, term_question_is_primary)
                VALUES (%s, %s, %s)
                ON CONFLICT (term_id, question_id) DO NOTHING;
                """,
                (term_id, qid, is_primary),
            )
        if questions:
            print(f"    Linked {len(questions)} question(s)")

        cur.execute("DELETE FROM tbl_formula WHERE formula_id = %s;", (formula_id,))
        print(f"  Deleted formula {formula_id}")

    conn.commit()
    cur.close()
    conn.close()
    print("Done.")


if __name__ == "__main__":
    run()
