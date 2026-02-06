#!/usr/bin/env python3
"""
Add one quiz question per formula for all formulas that do not yet have a question.
Uses existing seed for formula_id 2, 35, 36, 198; adds T/F, MC, word_problem, or multipart for the rest.
Run after seed_quiz_questions.py. Safe to run multiple times (skips formulas that already have a question).
"""
import os
import psycopg2
from decimal import Decimal

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    DATABASE_URL = "postgresql://dev_user:dev123@localhost:5432/linguaformula?sslmode=disable"

# All formula IDs that have content in populate_all_formula_fields (47 total). 2, 35, 36, 198 already have questions.
FORMULA_IDS_WITH_CONTENT = [
    1, 34, 35, 36, 2, 3, 67, 133, 134, 135, 143, 169, 142, 144, 145, 100, 146, 148, 149, 150, 151, 152,
    154, 157, 158, 159, 165, 170, 171, 172, 176, 177, 179, 181, 184, 185, 187, 190, 191, 192, 193, 197, 198,
    199, 202, 203, 204,
]

# Question specs for formulas that do NOT already have a question (exclude 2, 35, 36, 198).
# Each item: formula_id, question_type, stem, and type-specific field (answers, correct_tf, word_answer, or multipart_parts).
def _tf(stem, correct):
    return {"formula_id": None, "type": "true_false", "stem": stem, "correct_tf": correct}

def _mc(stem, choices):
    return {"formula_id": None, "type": "multiple_choice", "stem": stem, "choices": choices}

def _wp(stem, answer_text, answer_numeric=None):
    return {"formula_id": None, "type": "word_problem", "stem": stem, "answer_text": answer_text, "answer_numeric": answer_numeric}

def _mp(parent_stem, parts):
    return {"formula_id": None, "type": "multipart", "parent_stem": parent_stem, "parts": parts}

# Parts for multipart: (part_label, stem, answer_text, answer_numeric)
QUESTION_SPECS = [
    (1, _tf("Momentum equals mass times velocity.", True)),
    (34, _mc("In a closed system with no external forces, what happens to total momentum in a collision?",
             [("Total momentum before equals total momentum after", True), ("Total momentum increases", False), ("Total momentum becomes zero", False), ("Total momentum doubles", False)])),
    (3, _mc("What does E = mc² represent?",
            [("Mass-energy equivalence", True), ("Kinetic energy", False), ("Force equals mass times acceleration", False), ("Momentum conservation", False)])),
    (67, _tf("The limit as n approaches infinity of (1 + 1/n)^n equals e, approximately 2.71828.", True)),
    (133, _wp("In a study, the population has 50 members. What is n?", "50", 50)),
    (134, _wp("A sample of 5 parts is drawn from a bucket. What is r?", "5", 5)),
    (135, _wp("How many ways can you arrange 4 distinct books in a row? (Enter a number.)", "24", 24)),
    (143, _wp("How many ordered 3-letter codes can be made from 26 distinct letters if no letter is repeated? (Enter the integer.)", "15600", 15600)),
    (169, _wp("How many distinct arrangements are there of the letters in the word SEE? (Enter a number.)", "3", 3)),
    (142, _wp("How many 3-person committees can be chosen from 10 people if order does not matter? C(10,3) = ? (Enter the integer.)", "120", 120)),
    (144, _tf("The sample space S is the set of all possible outcomes of an experiment.", True)),
    (145, _tf("An individual outcome from a sample space may be denoted by x, s, or ω.", True)),
    (100, _tf("The set of all positive real numbers { x | x > 0 } can be used as a sample space for continuous random variables.", True)),
    (146, _tf("An event E is a subset of the sample space.", True)),
    (148, _mc("The union of events E₁ and E₂ contains outcomes that are in:",
              [("E₁ or E₂ or both", True), ("Only E₁", False), ("Only E₂", False), ("Neither E₁ nor E₂", False)])),
    (149, _mc("The intersection of events E₁ and E₂ contains outcomes that are in:",
              [("Both E₁ and E₂", True), ("E₁ or E₂", False), ("Neither E₁ nor E₂", False), ("The complement of E₁", False)])),
    (150, _tf("The complement of event E, written E', contains all outcomes in the sample space that are not in E.", True)),
    (151, _tf("Two events A and B are mutually exclusive if and only if A ∩ B = ∅.", True)),
    (152, _tf("The double complement of E satisfies (E')' = E.", True)),
    (154, _tf("The distributive law (A ∪ B) ∩ C = (A ∩ C) ∪ (B ∩ C) is true for sets.", True)),
    (157, _tf("The distributive law (A ∩ B) ∪ C = (A ∪ C) ∩ (B ∪ C) is true for sets.", True)),
    (158, _tf("De Morgan's law states: (A ∪ B)' = A' ∩ B'.", True)),
    (159, _tf("De Morgan's law states: (A ∩ B)' = A' ∪ B'.", True)),
    (165, _wp("You have 4 shirts and 3 pairs of pants. How many different shirt-pant outfits can you make? (Enter a number.)", "12", 12)),
    (170, _tf("P(E) denotes the probability of event E.", True)),
    (171, _tf("When a sample space has N equally likely outcomes, each outcome has probability 1/N.", True)),
    (172, _wp("One diode is drawn at random from 100 diodes. What is the probability as a decimal? (Enter a number, e.g. 0.01)", "0.01", 0.01)),
    (176, _wp("For a discrete event E with outcomes having P(a₁)=0.2 and P(a₂)=0.3, what is P(E) if E = {a₁, a₂}? (Enter a decimal.)", "0.5", 0.5)),
    (177, _tf("The relative frequency of an event (number of times it occurred divided by number of trials) approximates its probability.", True)),
    (179, _wp("If P(A)=0.5, P(B)=0.4, and P(A∩B)=0.2, what is P(A∪B)? (Enter a decimal.)", "0.7", 0.7)),
    (181, _tf("If A and B are mutually exclusive, then P(A ∩ B) = 0.", True)),
    (184, _wp("If P(A)=0.5 and P(A∩B)=0.2, what is P(B|A)? (Enter a decimal.)", "0.4", 0.4)),
    (185, _wp("From a bag with 4 green and 6 red marbles, what is P(green first and red second) without replacement? (Enter a decimal to two places, e.g. 0.27)", "0.27", 0.27)),
    (187, _wp("P(B)=P(B|A)P(A)+P(B|A')P(A'). If P(B|A)=0.1, P(A)=0.2, P(B|A')=0.05, P(A')=0.8, what is P(B)? (Enter a decimal to three places.)", "0.06", 0.06)),
    (190, _wp("Two independent components have P(L)=0.8 and P(R)=0.9. What is P(both work)? (Enter a decimal.)", "0.72", 0.72)),
    (191, _wp("Two independent components have P(T)=0.95 and P(B)=0.9. What is P(at least one works)? (Enter a decimal to three places.)", "0.995", 0.995)),
    (192, _wp("If p=0.1 is the probability a sample is contaminated and n=3, what is P(none contaminated)? (1-p)^n. (Enter a decimal to three places.)", "0.729", 0.729)),
    (193, _tf("The probability mass function p(x) gives P(X = x) for a discrete random variable X.", True)),
    (197, _wp("If f(t)=2t on [0,1], what is F(0.5)? F(x)=∫₀^x 2t dt. (Enter a decimal.)", "0.25", 0.25)),
    (199, _mp("A discrete random variable X takes values 0 and 1 with P(X=0)=0.4 and P(X=1)=0.6. So μ = 0(0.4)+1(0.6)=0.6.",
              [("a", "What is the mean μ?", "0.6", 0.6), ("b", "What is the variance σ²? Use σ² = Σ (x−μ)² f(x). (Round to two decimal places.)", "0.24", 0.24)])),
    (202, _tf("The standard deviation σ of a random variable is the square root of its variance.", True)),
    (203, _wp("For n=3, p=0.5, what is P(X=2) for a binomial? Use C(3,2)(0.5)²(0.5)¹. (Enter a decimal to three places.)", "0.375", 0.375)),
    (204, _wp("In 5 fair coin flips (n=5, p=0.5), what is the probability of exactly 2 heads? C(5,2)(0.5)²(0.5)³. (Enter a decimal to three places.)", "0.3125", 0.3125)),
]

def run():
    """Returns (count_added, message)."""
    sslmode = "require" if DATABASE_URL.startswith("postgres://") else "disable"
    db_url = DATABASE_URL.replace("postgres://", "postgresql://", 1) if DATABASE_URL.startswith("postgres://") else DATABASE_URL
    conn = psycopg2.connect(db_url, sslmode=sslmode)
    cur = conn.cursor()

    cur.execute("SELECT formula_id FROM tbl_formula_question")
    already_linked = {row[0] for row in cur.fetchall()}

    added = 0
    display_order_base = 10

    for formula_id, spec in QUESTION_SPECS:
        if formula_id in already_linked:
            continue
        qtype = spec["type"]
        if qtype == "true_false":
            stem = spec["stem"]
            correct = spec["correct_tf"]
            cur.execute("""
                INSERT INTO tbl_question (question_type, stem, display_order)
                VALUES ('true_false', %s, %s) RETURNING question_id;
            """, (stem, display_order_base + added))
            qid = cur.fetchone()[0]
            cur.execute("INSERT INTO tbl_answer (answer_text) VALUES ('True') RETURNING answer_id;")
            a_true = cur.fetchone()[0]
            cur.execute("INSERT INTO tbl_answer (answer_text) VALUES ('False') RETURNING answer_id;")
            a_false = cur.fetchone()[0]
            cur.execute("INSERT INTO tbl_question_answer (question_id, answer_id, is_correct, display_order) VALUES (%s, %s, %s, 1);", (qid, a_true, correct))
            cur.execute("INSERT INTO tbl_question_answer (question_id, answer_id, is_correct, display_order) VALUES (%s, %s, %s, 2);", (qid, a_false, not correct))
            cur.execute("INSERT INTO tbl_formula_question (formula_id, question_id, formula_question_is_primary) VALUES (%s, %s, true);", (formula_id, qid))
            added += 1
        elif qtype == "multiple_choice":
            stem = spec["stem"]
            choices = spec["choices"]
            cur.execute("""
                INSERT INTO tbl_question (question_type, stem, display_order)
                VALUES ('multiple_choice', %s, %s) RETURNING question_id;
            """, (stem, display_order_base + added))
            qid = cur.fetchone()[0]
            for order, (text, is_correct) in enumerate(choices, 1):
                cur.execute("INSERT INTO tbl_answer (answer_text) VALUES (%s) RETURNING answer_id;", (text,))
                aid = cur.fetchone()[0]
                cur.execute("INSERT INTO tbl_question_answer (question_id, answer_id, is_correct, display_order) VALUES (%s, %s, %s, %s);", (qid, aid, is_correct, order))
            cur.execute("INSERT INTO tbl_formula_question (formula_id, question_id, formula_question_is_primary) VALUES (%s, %s, true);", (formula_id, qid))
            added += 1
        elif qtype == "word_problem":
            stem = spec["stem"]
            ans_text = spec["answer_text"]
            ans_num = spec.get("answer_numeric")
            cur.execute("""
                INSERT INTO tbl_question (question_type, stem, display_order)
                VALUES ('word_problem', %s, %s) RETURNING question_id;
            """, (stem, display_order_base + added))
            qid = cur.fetchone()[0]
            if ans_num is not None:
                cur.execute("INSERT INTO tbl_answer (answer_text, answer_numeric) VALUES (%s, %s) RETURNING answer_id;", (ans_text, Decimal(str(ans_num))))
            else:
                cur.execute("INSERT INTO tbl_answer (answer_text) VALUES (%s) RETURNING answer_id;", (ans_text,))
            aid = cur.fetchone()[0]
            cur.execute("INSERT INTO tbl_question_answer (question_id, answer_id, is_correct, display_order) VALUES (%s, %s, true, 1);", (qid, aid))
            cur.execute("INSERT INTO tbl_formula_question (formula_id, question_id, formula_question_is_primary) VALUES (%s, %s, true);", (formula_id, qid))
            added += 1
        elif qtype == "multipart":
            parent_stem = spec["parent_stem"]
            parts = spec["parts"]
            cur.execute("""
                INSERT INTO tbl_question (question_type, stem, display_order)
                VALUES ('multipart', %s, %s) RETURNING question_id;
            """, (parent_stem, display_order_base + added))
            parent_id = cur.fetchone()[0]
            cur.execute("INSERT INTO tbl_formula_question (formula_id, question_id, formula_question_is_primary) VALUES (%s, %s, true);", (formula_id, parent_id))
            for part_order, (part_label, part_stem, part_ans_text, part_ans_num) in enumerate(parts, 1):
                cur.execute("""
                    INSERT INTO tbl_question (question_type, stem, parent_question_id, part_label, display_order)
                    VALUES ('word_problem', %s, %s, %s, %s) RETURNING question_id;
                """, (part_stem, parent_id, part_label, part_order))
                part_qid = cur.fetchone()[0]
                cur.execute("INSERT INTO tbl_answer (answer_text, answer_numeric) VALUES (%s, %s) RETURNING answer_id;", (part_ans_text, Decimal(str(part_ans_num))))
                part_aid = cur.fetchone()[0]
                cur.execute("INSERT INTO tbl_question_answer (question_id, answer_id, is_correct, display_order) VALUES (%s, %s, true, 1);", (part_qid, part_aid))
            added += 1

    conn.commit()
    cur.close()
    conn.close()
    msg = f"Added {added} new formula question(s). Formulas that already had a question were skipped."
    print(msg)
    return added, msg

if __name__ == "__main__":
    run()
