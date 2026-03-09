#!/usr/bin/env python3
"""
One-off script: list exam sheet templates and whether they have content (topics/items).
Run from backend/linguaformula: python scripts/check_exam_sheet_content.py
"""
import os
import sys

# Use same DB as app
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import psycopg2

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    DATABASE_URL = "postgresql://dev_user:dev123@localhost:5432/linguaformula?sslmode=disable"

def main():
    sslmode = "require" if DATABASE_URL.startswith("postgres://") else "disable"
    conn = psycopg2.connect(DATABASE_URL, sslmode=sslmode)
    cur = conn.cursor()

    # 1) All exam sheet templates with course name and segment name
    cur.execute("""
        SELECT t.template_id, t.template_name, t.course_id, t.segment_id,
               c.course_name, c.course_code, c.catalog_course_id,
               s.segment_name
        FROM tbl_exam_sheet_template t
        JOIN tbl_course c ON c.course_id = t.course_id
        LEFT JOIN tbl_segment s ON s.segment_id = t.segment_id
        ORDER BY c.course_name, s.segment_name NULLS LAST, t.template_id;
    """)
    templates = cur.fetchall()

    print("=== tbl_exam_sheet_template ===\n")
    if not templates:
        print("(no rows)")
    else:
        for row in templates:
            template_id, template_name, course_id, segment_id, course_name, course_code, catalog_course_id, segment_name = row
            print(f"  template_id={template_id}  template_name={template_name!r}  course_id={course_id}  segment_id={segment_id}")
            print(f"    course: {course_name!r}  code={course_code!r}  catalog_course_id={catalog_course_id}")
            print(f"    segment_name={segment_name!r}")

    # 2) Item and topic counts per template
    cur.execute("""
        SELECT t.template_id,
               (SELECT COUNT(*) FROM tbl_exam_sheet_template_topic tt WHERE tt.template_id = t.template_id) AS topic_count,
               (SELECT COUNT(*) FROM tbl_exam_sheet_template_item ti WHERE ti.template_id = t.template_id) AS item_count
        FROM tbl_exam_sheet_template t
        ORDER BY t.template_id;
    """)
    counts = cur.fetchall()

    print("\n=== Content per template (topics, items) ===\n")
    if not counts:
        print("(no templates)")
    else:
        any_with_content = False
        for template_id, topic_count, item_count in counts:
            has_content = (topic_count or 0) > 0 or (item_count or 0) > 0
            if has_content:
                any_with_content = True
            print(f"  template_id={template_id}  topics={topic_count}  items={item_count}  {'HAS CONTENT' if has_content else '(empty)'}")
        if not any_with_content:
            print("\n  >>> No templates have any topics or items. All exam sheets are empty.")

    # 3) Catalog course and segments for STAT 352 (for context)
    cur.execute("""
        SELECT catalog_course_id, course_name, course_code
        FROM tbl_catalog_course
        WHERE course_name ILIKE '%STAT%352%' OR course_code ILIKE '%STAT%352%';
    """)
    catalog = cur.fetchall()
    print("\n=== Catalog course (STAT 352) ===\n")
    for row in catalog:
        print(f"  catalog_course_id={row[0]}  name={row[1]!r}  code={row[2]!r}")

    cur.execute("""
        SELECT c.course_id, c.course_name, c.catalog_course_id
        FROM tbl_course c
        WHERE c.course_name ILIKE '%STAT%352%' OR c.course_code ILIKE '%STAT%352%';
    """)
    user_courses = cur.fetchall()
    print("\n=== User course(s) (STAT 352) ===\n")
    for row in user_courses:
        print(f"  course_id={row[0]}  name={row[1]!r}  catalog_course_id={row[2]}")

    # 4) For each template: does the course have user course terms/formulas in that segment? (compile source)
    print("\n=== User course content (terms/formulas) per course+segment ===\n")
    cur.execute("""
        SELECT c.course_id, c.course_name, t.segment_id, s.segment_name,
               (SELECT COUNT(*) FROM tbl_user_course_term uct
                WHERE uct.course_id = c.course_id AND (t.segment_id IS NOT DISTINCT FROM uct.segment_id)) AS term_count,
               (SELECT COUNT(*) FROM tbl_user_course_formula ucf
                WHERE ucf.course_id = c.course_id AND (t.segment_id IS NOT DISTINCT FROM ucf.segment_id)) AS formula_count
        FROM tbl_exam_sheet_template t
        JOIN tbl_course c ON c.course_id = t.course_id
        LEFT JOIN tbl_segment s ON s.segment_id = t.segment_id
        ORDER BY c.course_id, t.segment_id;
    """)
    for row in cur.fetchall():
        course_id, course_name, segment_id, segment_name, term_count, formula_count = row
        total = (term_count or 0) + (formula_count or 0)
        print(f"  course_id={course_id} {course_name!r}  segment_id={segment_id} ({segment_name!r})  terms={term_count}  formulas={formula_count}  -> compile would have {total} items")

    cur.close()
    conn.close()

if __name__ == "__main__":
    main()
