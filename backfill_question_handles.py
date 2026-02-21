#!/usr/bin/env python3
"""Backfill question_handle values from question text.

Run after migrations/add_question_handle.sql.
Uses slugify: lowercase, replace spaces/punctuation with _, collapse underscores.
Handles collisions by appending _2, _3, etc.
"""

import os
import re
import sys

import psycopg2

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://dev_user:dev123@localhost:5432/linguaformula")


def slugify(s: str, max_len: int = 100) -> str:
    """Convert to slug: lowercase, replace non-alphanumeric with _, collapse, strip."""
    if not s or not isinstance(s, str):
        return ""
    s = s.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s[:max_len] if len(s) > max_len else s


def backfill_questions(cur) -> int:
    cur.execute("""
        SELECT question_id, question_type, stem, part_label
        FROM tbl_question
        WHERE question_handle IS NULL OR question_handle = ''
        ORDER BY question_id;
    """)
    rows = cur.fetchall()
    if not rows:
        return 0

    cur.execute("SELECT question_handle FROM tbl_question WHERE question_handle IS NOT NULL AND question_handle != '';")
    used = {str(r[0]).strip().lower() for r in cur.fetchall() if r[0]}

    updated = 0
    for qid, qtype, stem, part_label in rows:
        seed = stem or ""
        if qtype == "multipart" and part_label:
            seed = f"{part_label}_{seed}"
        base = slugify(seed) or f"question_{qid}"
        handle = base
        n = 2
        while handle in used:
            handle = f"{base}_{n}"
            n += 1
        used.add(handle)
        cur.execute(
            "UPDATE tbl_question SET question_handle = %s, updated_at = CURRENT_TIMESTAMP WHERE question_id = %s;",
            (handle, qid),
        )
        updated += 1
    return updated


def main():
    sslmode = "require" if DATABASE_URL.startswith("postgres://") else "disable"
    conn = psycopg2.connect(DATABASE_URL, sslmode=sslmode)
    cur = conn.cursor()
    try:
        count = backfill_questions(cur)
        conn.commit()
        print(f"Backfill complete: {count} questions updated.")
    except Exception as e:
        conn.rollback()
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()
