#!/usr/bin/env python3
"""Backfill term_handle and formula_handle from term_name and formula_name.
Run after migrations add_term_handle.sql and add_formula_handle.sql.
Uses slugify: lowercase, replace spaces/punctuation with _, collapse underscores.
Handles collisions by appending _2, _3, etc."""

import os
import re
import sys

import psycopg2

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://dev_user:dev123@localhost:5432/linguaformula")


def slugify(s: str, max_len: int = 80) -> str:
    """Convert to slug: lowercase, replace non-alphanumeric with _, collapse, strip."""
    if not s or not isinstance(s, str):
        return ""
    s = s.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s[:max_len] if len(s) > max_len else s


def backfill_terms(cur) -> int:
    cur.execute("SELECT term_id, term_name FROM tbl_term WHERE term_handle IS NULL OR term_handle = '';")
    rows = cur.fetchall()
    updated = 0
    used = set()
    cur.execute("SELECT term_handle FROM tbl_term WHERE term_handle IS NOT NULL AND term_handle != '';")
    used.update(r[0] for r in cur.fetchall())
    for tid, name in rows:
        base = slugify(name) or f"term_{tid}"
        handle = base
        n = 2
        while handle in used:
            handle = f"{base}_{n}"
            n += 1
        used.add(handle)
        cur.execute("UPDATE tbl_term SET term_handle = %s, updated_at = CURRENT_TIMESTAMP WHERE term_id = %s;", (handle, tid))
        updated += 1
    return updated


def backfill_formulas(cur) -> int:
    cur.execute("SELECT formula_id, formula_name FROM tbl_formula WHERE formula_handle IS NULL OR formula_handle = '';")
    rows = cur.fetchall()
    updated = 0
    used = set()
    cur.execute("SELECT formula_handle FROM tbl_formula WHERE formula_handle IS NOT NULL AND formula_handle != '';")
    used.update(r[0] for r in cur.fetchall())
    for fid, name in rows:
        base = slugify(name) or f"formula_{fid}"
        handle = base
        n = 2
        while handle in used:
            handle = f"{base}_{n}"
            n += 1
        used.add(handle)
        cur.execute("UPDATE tbl_formula SET formula_handle = %s, updated_at = CURRENT_TIMESTAMP WHERE formula_id = %s;", (handle, fid))
        updated += 1
    return updated


def main():
    sslmode = "require" if DATABASE_URL.startswith("postgres://") else "disable"
    conn = psycopg2.connect(DATABASE_URL, sslmode=sslmode)
    cur = conn.cursor()
    try:
        terms_updated = backfill_terms(cur)
        formulas_updated = backfill_formulas(cur)
        conn.commit()
        print(f"Backfill complete: {terms_updated} terms, {formulas_updated} formulas updated.")
    except Exception as e:
        conn.rollback()
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()
