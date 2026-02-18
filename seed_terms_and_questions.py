#!/usr/bin/env python3
"""
Seed tbl_term with initial terms (population, sample, population size, sample size),
link them to Statistics discipline, and create multiple-choice and true/false
definition questions with plausible wrong answers.

Run after: migrations/add_terms_tables.sql
  Local: python seed_terms_and_questions.py
  Heroku: heroku run python seed_terms_and_questions.py -a linguaformula-backend

Safe to run multiple times: skips terms that already exist. Uses lowercase term names.
"""
import os
import random

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    DATABASE_URL = "postgresql://dev_user:dev123@localhost:5432/linguaformula?sslmode=disable"

# Terms: (term_name, definition, formulaic_expression or None)
TERMS = [
    ("population", "the entire group of individuals about which information is sought.", None),
    ("sample", "a subset of the population that is actually observed.", None),
    ("population size", "total number of individuals in the population.", r"N"),
    ("sample size", "number of individuals in the sample.", r"n"),
]

# Multiple-choice: stem template "What does [term] mean?" with (definition, is_correct) choices.
# Wrong definitions are plausible alternatives (definitions of related terms or common confusions).
MC_QUESTIONS = {
    "population": [
        ("the entire group of individuals about which information is sought.", True),
        ("a subset of the population that is actually observed.", False),  # sample
        ("the total number of individuals in the population.", False),    # population size
        ("the number of individuals in the sample.", False),               # sample size
    ],
    "sample": [
        ("a subset of the population that is actually observed.", True),
        ("the entire group of individuals about which information is sought.", False),  # population
        ("the total number of individuals in the population.", False),    # population size
        ("the number of individuals in the sample.", False),               # sample size
    ],
    "population size": [
        ("total number of individuals in the population.", True),
        ("the entire group of individuals about which information is sought.", False),  # population
        ("a subset of the population that is actually observed.", False),  # sample
        ("number of individuals in the sample.", False),                   # sample size
    ],
    "sample size": [
        ("number of individuals in the sample.", True),
        ("the entire group of individuals about which information is sought.", False),  # population
        ("a subset of the population that is actually observed.", False),  # sample
        ("total number of individuals in the population.", False),        # population size
    ],
}

# True/false: (stem, is_correct). Stem is "The term [X] means: [definition]."
TF_QUESTIONS = {
    "population": [
        ("The term population means: the entire group of individuals about which information is sought.", True),
        ("The term population means: a subset of the population that is actually observed.", False),
    ],
    "sample": [
        ("The term sample means: a subset of the population that is actually observed.", True),
        ("The term sample means: the total number of individuals in the population.", False),
    ],
    "population size": [
        ("The term population size means: total number of individuals in the population.", True),
        ("The term population size means: number of individuals in the sample.", False),
    ],
    "sample size": [
        ("The term sample size means: number of individuals in the sample.", True),
        ("The term sample size means: the entire group of individuals about which information is sought.", False),
    ],
}


def run():
    """Returns (terms_added, questions_added, message)."""
    import psycopg2

    sslmode = "require" if DATABASE_URL.startswith("postgres://") else "disable"
    db_url = (
        DATABASE_URL.replace("postgres://", "postgresql://", 1)
        if DATABASE_URL.startswith("postgres://")
        else DATABASE_URL
    )
    conn = psycopg2.connect(db_url, sslmode=sslmode)
    cur = conn.cursor()

    # Get Statistics discipline_id
    cur.execute(
        "SELECT discipline_id FROM tbl_discipline WHERE discipline_handle = %s;",
        ("statistics",),
    )
    row = cur.fetchone()
    if not row:
        raise RuntimeError("Discipline 'statistics' not found. Run populate_disciplines.py first.")
    stats_id = row[0]

    terms_added = 0
    questions_added = 0
    display_order = 0

    for term_name, definition, formulaic_expr in TERMS:
        # Skip if term already exists (avoids duplicate terms and questions)
        cur.execute("SELECT term_id FROM tbl_term WHERE term_name = %s;", (term_name,))
        existing = cur.fetchone()
        if existing:
            print(f"  Skipping existing term: {term_name}")
            continue

        # Insert term
        cur.execute(
            """
            INSERT INTO tbl_term (term_name, definition, display_order, formulaic_expression)
            VALUES (%s, %s, %s, %s) RETURNING term_id;
            """,
            (term_name, definition, display_order, formulaic_expr),
        )
        term_id = cur.fetchone()[0]
        terms_added += 1
        display_order += 1
        print(f"  Added term: {term_name} (id={term_id})")

        # Link to Statistics (primary)
        cur.execute(
            """
            INSERT INTO tbl_term_discipline (term_id, discipline_id, term_discipline_is_primary)
            VALUES (%s, %s, true)
            ON CONFLICT (term_id, discipline_id) DO NOTHING;
            """,
            (term_id, stats_id),
        )

        # Multiple-choice question
        choices = MC_QUESTIONS.get(term_name, [])
        if choices:
            stem = f"What does {term_name} mean?"
            # Shuffle choices for variety (keep correct/incorrect, just order)
            shuffled = list(choices)
            random.shuffle(shuffled)

            cur.execute(
                """
                INSERT INTO tbl_question (question_type, stem, display_order)
                VALUES ('multiple_choice', %s, %s) RETURNING question_id;
                """,
                (stem, display_order),
            )
            qid = cur.fetchone()[0]
            display_order += 1
            for order, (text, is_correct) in enumerate(shuffled, 1):
                cur.execute(
                    "INSERT INTO tbl_answer (answer_text) VALUES (%s) RETURNING answer_id;",
                    (text,),
                )
                aid = cur.fetchone()[0]
                cur.execute(
                    """
                    INSERT INTO tbl_question_answer (question_id, answer_id, is_correct, display_order)
                    VALUES (%s, %s, %s, %s);
                    """,
                    (qid, aid, is_correct, order),
                )
            cur.execute(
                """
                INSERT INTO tbl_term_question (term_id, question_id, term_question_is_primary)
                VALUES (%s, %s, true);
                """,
                (term_id, qid),
            )
            questions_added += 1

        # True/false questions
        tf_pairs = TF_QUESTIONS.get(term_name, [])
        for stem, correct in tf_pairs:
            cur.execute(
                """
                INSERT INTO tbl_question (question_type, stem, display_order)
                VALUES ('true_false', %s, %s) RETURNING question_id;
                """,
                (stem, display_order),
            )
            qid = cur.fetchone()[0]
            display_order += 1

            # Reuse or create True/False answers
            cur.execute("SELECT answer_id FROM tbl_answer WHERE answer_text = 'True' LIMIT 1;")
            r = cur.fetchone()
            if r:
                a_true = r[0]
            else:
                cur.execute("INSERT INTO tbl_answer (answer_text) VALUES ('True') RETURNING answer_id;")
                a_true = cur.fetchone()[0]
            cur.execute("SELECT answer_id FROM tbl_answer WHERE answer_text = 'False' LIMIT 1;")
            r = cur.fetchone()
            if r:
                a_false = r[0]
            else:
                cur.execute("INSERT INTO tbl_answer (answer_text) VALUES ('False') RETURNING answer_id;")
                a_false = cur.fetchone()[0]

            cur.execute(
                """
                INSERT INTO tbl_question_answer (question_id, answer_id, is_correct, display_order)
                VALUES (%s, %s, %s, 1);
                """,
                (qid, a_true, correct),
            )
            cur.execute(
                """
                INSERT INTO tbl_question_answer (question_id, answer_id, is_correct, display_order)
                VALUES (%s, %s, %s, 2);
                """,
                (qid, a_false, not correct),
            )
            cur.execute(
                """
                INSERT INTO tbl_term_question (term_id, question_id, term_question_is_primary)
                VALUES (%s, %s, false);
                """,
                (term_id, qid),
            )
            questions_added += 1

    conn.commit()
    cur.close()
    conn.close()

    msg = f"Terms: {terms_added} added. Questions: {questions_added} added."
    print(msg)
    return terms_added, questions_added, msg


if __name__ == "__main__":
    run()
