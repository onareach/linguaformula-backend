#!/usr/bin/env python3
"""
Re-link user course terms and formulas to segments when segment_id is NULL.

Use case: After segment_label was dropped by add_segment_table_and_replace_segment_label.sql,
some rows may have segment_id NULL (e.g. backfill ran before data existed, or name mismatch).
This script sets segment_id for those rows by catalog course and segment name.

Usage (from backend/linguaformula):
  python3 scripts/relink_user_course_segments.py
  python3 scripts/relink_user_course_segments.py --catalog-course-id 1 --segment-name "Midterm 1"
  python3 scripts/relink_user_course_segments.py --dry-run

Defaults: catalog_course_id=1 (STAT 352), segment_name="Midterm 1".
Only affects rows where segment_id IS NULL and course has the given catalog_course_id.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import psycopg2

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    DATABASE_URL = "postgresql://dev_user:dev123@localhost:5432/linguaformula?sslmode=disable"


def main():
    ap = argparse.ArgumentParser(description="Re-link user course term/formula to segment by catalog course + segment name")
    ap.add_argument("--catalog-course-id", type=int, default=1, help="Catalog course id (default 1 = STAT 352)")
    ap.add_argument("--segment-name", type=str, default="Midterm 1", help="Segment name to assign (default Midterm 1)")
    ap.add_argument("--dry-run", action="store_true", help="Only report what would be updated")
    args = ap.parse_args()

    sslmode = "require" if DATABASE_URL.startswith("postgres://") else "disable"
    conn = psycopg2.connect(DATABASE_URL, sslmode=sslmode)
    cur = conn.cursor()

    # Resolve segment_id from catalog_course_id + segment_name
    cur.execute(
        "SELECT segment_id FROM tbl_segment WHERE catalog_course_id = %s AND segment_name = %s;",
        (args.catalog_course_id, args.segment_name),
    )
    row = cur.fetchone()
    if not row:
        print(f"No segment found for catalog_course_id={args.catalog_course_id} and segment_name={args.segment_name!r}")
        cur.close()
        conn.close()
        sys.exit(1)
    segment_id = row[0]
    print(f"Using segment_id={segment_id} for catalog_course_id={args.catalog_course_id}, segment_name={args.segment_name!r}")

    # User course terms: set segment_id where course has this catalog and segment_id is NULL
    cur.execute(
        """
        UPDATE tbl_user_course_term u
        SET segment_id = %s
        FROM tbl_course c
        WHERE c.course_id = u.course_id
          AND c.catalog_course_id = %s
          AND u.segment_id IS NULL
        RETURNING u.course_id;
        """,
        (segment_id, args.catalog_course_id),
    )
    term_rows = cur.fetchall()
    term_count = len(term_rows)

    # User course formulas: same
    cur.execute(
        """
        UPDATE tbl_user_course_formula u
        SET segment_id = %s
        FROM tbl_course c
        WHERE c.course_id = u.course_id
          AND c.catalog_course_id = %s
          AND u.segment_id IS NULL
        RETURNING u.course_id;
        """,
        (segment_id, args.catalog_course_id),
    )
    formula_rows = cur.fetchall()
    formula_count = len(formula_rows)

    if args.dry_run:
        conn.rollback()
        print(f"[DRY RUN] Would update terms={term_count}, formulas={formula_count}")
    else:
        conn.commit()
        print(f"Updated terms={term_count}, formulas={formula_count}")

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
