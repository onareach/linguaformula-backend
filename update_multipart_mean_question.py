#!/usr/bin/env python3
"""
One-time update: replace the discrete mean multipart question (formula_id 198)
from the old 3-part (mean, variance, std dev) to 2-part: (a) What is the mean?
(b) If four more samples were taken with values 2, 2, 3, 3, what would the new mean be?
Run on DBs that were seeded with the previous version of seed_quiz_questions.py.
"""
import os
import psycopg2

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    DATABASE_URL = "postgresql://dev_user:dev123@localhost:5432/linguaformula?sslmode=disable"

def run():
    sslmode = "require" if DATABASE_URL.startswith("postgres://") else "disable"
    if DATABASE_URL.startswith("postgres://"):
        db_url = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    else:
        db_url = DATABASE_URL
    conn = psycopg2.connect(db_url, sslmode=sslmode)
    cur = conn.cursor()

    # Find multipart parent by distinctive stem (works regardless of formula_id on production)
    cur.execute("""
        SELECT question_id FROM tbl_question
        WHERE question_type = 'multipart' AND parent_question_id IS NULL
        AND stem LIKE %s;
    """, ("%errors per 100 lines%",))
    row = cur.fetchone()
    if not row:
        msg = "No multipart parent found (stem containing 'errors per 100 lines'). Nothing to update."
        cur.close()
        conn.close()
        return False, msg
    parent_id = row[0]

    # Get child parts (a, b, c)
    cur.execute("""
        SELECT question_id, part_label FROM tbl_question
        WHERE parent_question_id = %s ORDER BY display_order;
    """, (parent_id,))
    children = cur.fetchall()
    part_a_id = None
    part_b_id = None
    part_c_id = None
    for qid, label in children:
        if label == "a":
            part_a_id = qid
        elif label == "b":
            part_b_id = qid
        elif label == "c":
            part_c_id = qid

    # Delete part (b) and (c) if present: question_answer rows then question rows
    for qid in (part_b_id, part_c_id):
        if qid is None:
            continue
        cur.execute("DELETE FROM tbl_question_answer WHERE question_id = %s;", (qid,))
        cur.execute("DELETE FROM tbl_question WHERE question_id = %s;", (qid,))

    # If we had a part (b) we already deleted it. If we had 3 parts, we now have only part (a). Insert new part (b).
    cur.execute("""
        INSERT INTO tbl_question (question_type, stem, parent_question_id, part_label, display_order)
        VALUES ('word_problem', 'If four more samples were taken with values 2, 2, 3, 3, what would the new mean be? (Round to two decimal places.)', %s, 'b', 2)
        RETURNING question_id;
    """, (parent_id,))
    new_b_id = cur.fetchone()[0]
    cur.execute("INSERT INTO tbl_answer (answer_text, answer_numeric) VALUES ('2.44', 2.44) RETURNING answer_id;")
    a_b = cur.fetchone()[0]
    cur.execute("INSERT INTO tbl_question_answer (question_id, answer_id, is_correct, display_order) VALUES (%s, %s, true, 1);", (new_b_id, a_b))

    conn.commit()
    cur.close()
    conn.close()
    return True, "Updated multipart mean question: now 2 parts (a) mean, (b) new mean after four more samples."

if __name__ == "__main__":
    import sys
    success, message = run()
    print(message)
    sys.exit(0 if success else 1)
