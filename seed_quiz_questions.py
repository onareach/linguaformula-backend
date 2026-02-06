#!/usr/bin/env python3
"""
Seed four quiz questions (one per type) linked to formulas via tbl_formula_question.
- Multiple-choice: Newton's Second Law (formula_id 2)
- True/false: Kinetic energy (formula_id 35)
- Word problem: Potential energy (formula_id 36)
- Multipart: Discrete mean (formula_id 198); part (a) mean of 2,3,1,4,2; part (b) how mean changes if four more samples taken
"""
import os
import sys
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

    # 1. Multiple-choice: Newton's Second Law (formula_id 2)
    cur.execute("""
        INSERT INTO tbl_question (question_type, stem, display_order)
        VALUES ('multiple_choice', 'What does Newton''s Second Law state?', 1)
        RETURNING question_id;
    """)
    q_mc_id = cur.fetchone()[0]
    # Answers (wrong ones first, then correct)
    cur.execute("INSERT INTO tbl_answer (answer_text) VALUES ('Force equals mass plus acceleration') RETURNING answer_id;")
    a_mc_1 = cur.fetchone()[0]
    cur.execute("INSERT INTO tbl_answer (answer_text) VALUES ('Force equals mass times acceleration') RETURNING answer_id;")
    a_mc_2 = cur.fetchone()[0]
    cur.execute("INSERT INTO tbl_answer (answer_text) VALUES ('Energy equals mass times the speed of light squared') RETURNING answer_id;")
    a_mc_3 = cur.fetchone()[0]
    cur.execute("INSERT INTO tbl_answer (answer_text) VALUES ('Momentum equals mass times velocity') RETURNING answer_id;")
    a_mc_4 = cur.fetchone()[0]
    for order, (aid, correct) in enumerate([(a_mc_1, False), (a_mc_2, True), (a_mc_3, False), (a_mc_4, False)], 1):
        cur.execute("INSERT INTO tbl_question_answer (question_id, answer_id, is_correct, display_order) VALUES (%s, %s, %s, %s);", (q_mc_id, aid, correct, order))
    cur.execute("INSERT INTO tbl_formula_question (formula_id, question_id, formula_question_is_primary) VALUES (2, %s, true);", (q_mc_id,))

    # 2. True/false: Kinetic energy (formula_id 35)
    cur.execute("""
        INSERT INTO tbl_question (question_type, stem, display_order)
        VALUES ('true_false', 'Kinetic energy equals one-half times mass times velocity squared.', 2)
        RETURNING question_id;
    """)
    q_tf_id = cur.fetchone()[0]
    cur.execute("INSERT INTO tbl_answer (answer_text) VALUES ('True') RETURNING answer_id;")
    a_true = cur.fetchone()[0]
    cur.execute("INSERT INTO tbl_answer (answer_text) VALUES ('False') RETURNING answer_id;")
    a_false = cur.fetchone()[0]
    cur.execute("INSERT INTO tbl_question_answer (question_id, answer_id, is_correct, display_order) VALUES (%s, %s, true, 1);", (q_tf_id, a_true))
    cur.execute("INSERT INTO tbl_question_answer (question_id, answer_id, is_correct, display_order) VALUES (%s, %s, false, 2);", (q_tf_id, a_false))
    cur.execute("INSERT INTO tbl_formula_question (formula_id, question_id, formula_question_is_primary) VALUES (35, %s, true);", (q_tf_id,))

    # 3. Word problem: Potential energy (formula_id 36). E = mgh = 10 * 9.8 * 2 = 196 J
    cur.execute("""
        INSERT INTO tbl_question (question_type, stem, display_order)
        VALUES ('word_problem', 'A 10 kg textbook is lifted 2 meters above the floor. Using g = 9.8 m/s², what is its gravitational potential energy in Joules? (Enter a number.)', 3)
        RETURNING question_id;
    """)
    q_wp_id = cur.fetchone()[0]
    cur.execute("INSERT INTO tbl_answer (answer_text, answer_numeric) VALUES ('196', 196) RETURNING answer_id;")
    a_wp = cur.fetchone()[0]
    cur.execute("INSERT INTO tbl_question_answer (question_id, answer_id, is_correct, display_order) VALUES (%s, %s, true, 1);", (q_wp_id, a_wp))
    cur.execute("INSERT INTO tbl_formula_question (formula_id, question_id, formula_question_is_primary) VALUES (36, %s, true);", (q_wp_id,))

    # 4. Multipart: data 2, 3, 1, 4, 2 → mean 2.4; then how mean changes with four more samples (formula_id 198)
    cur.execute("""
        INSERT INTO tbl_question (question_type, stem, display_order)
        VALUES ('multipart', 'The following data represent the number of errors per 100 lines of code in a sample of 5 files: 2, 3, 1, 4, 2.', 4)
        RETURNING question_id;
    """)
    q_mp_parent_id = cur.fetchone()[0]
    cur.execute("INSERT INTO tbl_formula_question (formula_id, question_id, formula_question_is_primary) VALUES (198, %s, true);", (q_mp_parent_id,))

    # Part (a): mean (same first question)
    cur.execute("""
        INSERT INTO tbl_question (question_type, stem, parent_question_id, part_label, display_order)
        VALUES ('word_problem', 'What is the mean?', %s, 'a', 1)
        RETURNING question_id;
    """, (q_mp_parent_id,))
    q_mp_a = cur.fetchone()[0]
    cur.execute("INSERT INTO tbl_answer (answer_text, answer_numeric) VALUES ('2.4', 2.4) RETURNING answer_id;")
    a_mp_a = cur.fetchone()[0]
    cur.execute("INSERT INTO tbl_question_answer (question_id, answer_id, is_correct, display_order) VALUES (%s, %s, true, 1);", (q_mp_a, a_mp_a))

    # Part (b): how would the mean change if four more samples were taken (values 2,2,3,3 → new mean 22/9 ≈ 2.44)
    cur.execute("""
        INSERT INTO tbl_question (question_type, stem, parent_question_id, part_label, display_order)
        VALUES ('word_problem', 'If four more samples were taken with values 2, 2, 3, 3, what would the new mean be? (Round to two decimal places.)', %s, 'b', 2)
        RETURNING question_id;
    """, (q_mp_parent_id,))
    q_mp_b = cur.fetchone()[0]
    cur.execute("INSERT INTO tbl_answer (answer_text, answer_numeric) VALUES ('2.44', 2.44) RETURNING answer_id;")
    a_mp_b = cur.fetchone()[0]
    cur.execute("INSERT INTO tbl_question_answer (question_id, answer_id, is_correct, display_order) VALUES (%s, %s, true, 1);", (q_mp_b, a_mp_b))

    conn.commit()
    cur.close()
    conn.close()
    print("Seeded 4 questions (MC, T/F, word, multipart) and formula-question links.")

if __name__ == "__main__":
    run()
