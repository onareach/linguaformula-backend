# app.py
# Lingua Formula API backend
# This app.py was created in order to expose an API endpoint for
# Vercel Next.js to call
# The Heroku API URL will be configured when deploying
# The Heroku PostgreSQL login will be: heroku pg:psql -a [app-name]

from flask import Flask, jsonify, request, make_response
from flask_cors import CORS
import psycopg2
from update_multipart_mean_question import run as run_multipart_mean_update
from seed_all_formula_questions import run as run_seed_all_formula_questions
import os
import json
import secrets
import hashlib
import openai
import jwt
import bcrypt
from datetime import datetime, timedelta
import base64
from PIL import Image
import io
import pytesseract

app = Flask(__name__)

# CORS: allowed origins for browser requests (e.g. forgot-password from frontend).
# Add more via env CORS_ORIGINS (comma-separated, no spaces), e.g. CORS_ORIGINS=https://my-app.vercel.app
_default_origins = [
    "http://localhost:3000",
    "http://localhost:3001",
    "https://linguaformula.com",
    "https://www.linguaformula.com",
    "https://linguaformula.vercel.app",
    "https://frontend-4y57xooet-david-longs-projects-14094a66.vercel.app",
    "https://frontend-ebv9w8qm1-david-longs-projects-14094a66.vercel.app",
    "https://frontend-mauve-three-67.vercel.app",
]
_extra_origins = [o.strip() for o in os.environ.get("CORS_ORIGINS", "").split(",") if o.strip()]
CORS(
    app,
    origins=_default_origins + _extra_origins,
    supports_credentials=True,
    allow_headers=["Content-Type", "Authorization"],
    methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
)

DATABASE_URL = os.environ.get("DATABASE_URL")
# Fallback to local database if DATABASE_URL is not set
if not DATABASE_URL:
    DATABASE_URL = "postgresql://dev_user:dev123@localhost:5432/linguaformula?sslmode=disable"
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
JWT_SECRET = os.environ.get("JWT_SECRET", "dev-secret-change-in-production")
AUTH_COOKIE_NAME = "linguaformula_token"

if OPENAI_API_KEY:
    openai.api_key = OPENAI_API_KEY

def _auth_db():
    sslmode = "require" if DATABASE_URL.startswith("postgres://") else "disable"
    return psycopg2.connect(DATABASE_URL, sslmode=sslmode)

def _create_jwt(user_id, email):
    payload = {"sub": user_id, "email": email, "exp": datetime.utcnow() + timedelta(days=7)}
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")

def _verify_jwt(token):
    if not token:
        return None
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        return {"user_id": payload["sub"], "email": payload["email"]}
    except jwt.InvalidTokenError:
        return None

def _get_current_user():
    """Auth from cookie (desktop) or Authorization: Bearer (mobile; cross-origin cookie often not sent)."""
    token = request.cookies.get(AUTH_COOKIE_NAME)
    if not token and request.headers.get("Authorization"):
        parts = request.headers.get("Authorization", "").strip().split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            token = parts[1]
    return _verify_jwt(token)

def _user_response(user_row):
    # user_row: (user_id, email, display_name, is_admin)
    is_admin = user_row[3] if len(user_row) > 3 else False
    return {"id": user_row[0], "email": user_row[1], "display_name": user_row[2], "is_admin": is_admin}


def _require_admin():
    """Require authenticated admin. Returns (claims, None) or (None, response_tuple)."""
    claims = _get_current_user()
    if not claims:
        return None, (jsonify({"error": "Not authenticated"}), 401)
    conn = _auth_db()
    cur = conn.cursor()
    cur.execute("SELECT is_admin FROM tbl_user WHERE user_id = %s;", (claims["user_id"],))
    row = cur.fetchone()
    cur.close()
    conn.close()
    if not row or not row[0]:
        return None, (jsonify({"error": "Admin access required"}), 403)
    return claims, None

def get_formulas():
    # Use sslmode=require for production (Heroku uses postgres://), disable for local development
    # Heroku DATABASE_URL starts with postgres://, local uses postgresql://
    sslmode = "require" if DATABASE_URL.startswith("postgres://") else "disable"
    conn = psycopg2.connect(DATABASE_URL, sslmode=sslmode)
    cursor = conn.cursor()
    cursor.execute("SELECT formula_id, formula_name, latex, formula_description, english_verbalization, symbolic_verbalization FROM tbl_formula ORDER BY formula_name;")
    formulas = cursor.fetchall()
    result = [{"id": row[0], "formula_name": row[1], "latex": row[2], 
               "formula_description": row[3], "english_verbalization": row[4], "symbolic_verbalization": row[5]} for row in formulas]
    cursor.close()
    conn.close()
    return result

def get_formulas_by_disciplines(discipline_ids, include_children=True):
    """Get formulas filtered by discipline IDs, optionally including child disciplines."""
    sslmode = "require" if DATABASE_URL.startswith("postgres://") else "disable"
    conn = psycopg2.connect(DATABASE_URL, sslmode=sslmode)
    cursor = conn.cursor()
    
    if include_children:
        # Get all child discipline IDs for the selected parent disciplines
        cursor.execute("""
            WITH RECURSIVE discipline_tree AS (
                SELECT discipline_id FROM tbl_discipline WHERE discipline_id = ANY(%s)
                UNION ALL
                SELECT d.discipline_id 
                FROM tbl_discipline d
                INNER JOIN discipline_tree dt ON d.discipline_parent_id = dt.discipline_id
            )
            SELECT DISTINCT f.formula_id, f.formula_name, f.latex,
                   f.formula_description, f.english_verbalization, f.symbolic_verbalization
            FROM tbl_formula f
            INNER JOIN tbl_formula_discipline fd ON f.formula_id = fd.formula_id
            INNER JOIN discipline_tree dt ON fd.discipline_id = dt.discipline_id
            ORDER BY f.formula_name;
        """, (discipline_ids,))
    else:
        # Only get formulas directly linked to the selected disciplines
        cursor.execute("""
            SELECT DISTINCT f.formula_id, f.formula_name, f.latex,
                   f.formula_description, f.english_verbalization, f.symbolic_verbalization
            FROM tbl_formula f
            INNER JOIN tbl_formula_discipline fd ON f.formula_id = fd.formula_id
            WHERE fd.discipline_id = ANY(%s)
            ORDER BY f.formula_name;
        """, (discipline_ids,))
    
    formulas = cursor.fetchall()
    result = [{"id": row[0], "formula_name": row[1], "latex": row[2], 
               "formula_description": row[3], "english_verbalization": row[4], "symbolic_verbalization": row[5]} for row in formulas]
    cursor.close()
    conn.close()
    return result

# Function to fetch a single formula by ID
def get_formula_by_id(formula_id):
    # Use sslmode=require for production (Heroku uses postgres://), disable for local development
    sslmode = "require" if DATABASE_URL.startswith("postgres://") else "disable"
    conn = psycopg2.connect(DATABASE_URL, sslmode=sslmode)
    cursor = conn.cursor()
    cursor.execute("SELECT formula_id, formula_name, latex, formula_description, english_verbalization, symbolic_verbalization, units, example, historical_context FROM tbl_formula WHERE formula_id = %s;", (formula_id,))
    formula = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if formula:
        return {
            "id": formula[0],
            "formula_name": formula[1],
            "latex": formula[2],
            "formula_description": formula[3],
            "english_verbalization": formula[4],
            "symbolic_verbalization": formula[5],
            "units": formula[6],
            "example": formula[7],
            "historical_context": formula[8]
        }
    else:
        return None

def get_applications():
    # Use sslmode=require for production (Heroku uses postgres://), disable for local development
    sslmode = "require" if DATABASE_URL.startswith("postgres://") else "disable"
    conn = psycopg2.connect(DATABASE_URL, sslmode=sslmode)
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, problem_text, subject_area, image_filename, image_text, created_at FROM application ORDER BY created_at DESC;")
    applications = cursor.fetchall()
    result = [{"id": row[0], "title": row[1], "problem_text": row[2], "subject_area": row[3], 
               "image_filename": row[4], "image_text": row[5], "created_at": row[6].isoformat() if row[6] else None} for row in applications]
    cursor.close()
    conn.close()
    return result

def get_application_by_id(application_id):
    # Use sslmode=require for production (Heroku uses postgres://), disable for local development
    sslmode = "require" if DATABASE_URL.startswith("postgres://") else "disable"
    conn = psycopg2.connect(DATABASE_URL, sslmode=sslmode)
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, problem_text, subject_area, image_filename, image_text, created_at FROM application WHERE id = %s;", (application_id,))
    application = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if application:
        return {
            "id": application[0],
            "title": application[1],
            "problem_text": application[2],
            "subject_area": application[3],
            "image_filename": application[4],
            "image_text": application[5],
            "created_at": application[6].isoformat() if application[6] else None
        }
    else:
        return None

def get_application_formulas(application_id):
    sslmode = "require" if DATABASE_URL.startswith("postgres://") else "disable"
    conn = psycopg2.connect(DATABASE_URL, sslmode=sslmode)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT f.formula_id, f.formula_name, f.latex, f.formula_description, af.relevance_score
        FROM tbl_formula f
        JOIN application_formula af ON f.formula_id = af.formula_id
        WHERE af.application_id = %s
        ORDER BY af.relevance_score DESC NULLS LAST;
    """, (application_id,))
    formulas = cursor.fetchall()
    result = [{"id": row[0], "formula_name": row[1], "latex": row[2], 
               "formula_description": row[3], "relevance_score": row[4]} for row in formulas]
    cursor.close()
    conn.close()
    return result

def create_application(title, problem_text, subject_area=None, image_filename=None, image_data=None, image_text=None):
    sslmode = "require" if DATABASE_URL.startswith("postgres://") else "disable"
    conn = psycopg2.connect(DATABASE_URL, sslmode=sslmode)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO application (title, problem_text, subject_area, image_filename, image_data, image_text)
        VALUES (%s, %s, %s, %s, %s, %s) RETURNING id;
    """, (title, problem_text, subject_area, image_filename, image_data, image_text))
    application_id = cursor.fetchone()[0]
    conn.commit()
    cursor.close()
    conn.close()
    return application_id

def extract_text_from_image(image_data):
    """Extract text from image using OCR (Tesseract)"""
    try:
        image = Image.open(io.BytesIO(image_data))
        text = pytesseract.image_to_string(image)
        return text.strip()
    except Exception as e:
        print(f"OCR Error: {str(e)}")
        return None

def extract_text_with_openai(image_data):
    """Extract and interpret text from image using OpenAI Vision API"""
    try:
        if not OPENAI_API_KEY:
            return None
        
        # Convert image to base64
        image_base64 = base64.b64encode(image_data).decode('utf-8')
        
        response = openai.ChatCompletion.create(
            model="gpt-4-vision-preview",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Please extract and transcribe all text, mathematical expressions, diagrams, and problem descriptions from this image. Include any tables, formulas, or structured data. Format the output clearly and preserve the mathematical notation."
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_base64}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=1000
        )
        
        return response.choices[0].message.content
    except Exception as e:
        print(f"OpenAI Vision Error: {str(e)}")
        return None

def link_application_formula(application_id, formula_id, relevance_score=None):
    sslmode = "require" if DATABASE_URL.startswith("postgres://") else "disable"
    conn = psycopg2.connect(DATABASE_URL, sslmode=sslmode)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO application_formula (application_id, formula_id, relevance_score)
        VALUES (%s, %s, %s)
        ON CONFLICT (application_id, formula_id) 
        DO UPDATE SET relevance_score = EXCLUDED.relevance_score;
    """, (application_id, formula_id, relevance_score))
    conn.commit()
    cursor.close()
    conn.close()

# Route to fetch all disciplines with hierarchy
@app.route('/api/disciplines', methods=['GET'])
def fetch_disciplines():
    try:
        sslmode = "require" if DATABASE_URL.startswith("postgres://") else "disable"
        conn = psycopg2.connect(DATABASE_URL, sslmode=sslmode)
        cursor = conn.cursor()
        
        # Fetch all disciplines with parent info, formula counts, and term counts.
        # formula_count and term_count = distinct items in that discipline's subtree.
        cursor.execute("""
            SELECT 
                d.discipline_id,
                d.discipline_name,
                d.discipline_handle,
                d.discipline_description,
                d.discipline_parent_id,
                COALESCE(p.discipline_name, NULL) as parent_name,
                COALESCE(p.discipline_handle, NULL) as parent_handle,
                (SELECT COUNT(DISTINCT fd.formula_id)
                 FROM tbl_formula_discipline fd
                 WHERE fd.discipline_id IN (
                   WITH RECURSIVE subtree AS (
                     SELECT discipline_id FROM tbl_discipline WHERE discipline_id = d.discipline_id
                     UNION ALL
                     SELECT child.discipline_id FROM tbl_discipline child
                     INNER JOIN subtree s ON child.discipline_parent_id = s.discipline_id
                   )
                   SELECT discipline_id FROM subtree
                 )
                ) as formula_count,
                (SELECT COUNT(DISTINCT td.term_id)
                 FROM tbl_term_discipline td
                 WHERE td.discipline_id IN (
                   WITH RECURSIVE subtree AS (
                     SELECT discipline_id FROM tbl_discipline WHERE discipline_id = d.discipline_id
                     UNION ALL
                     SELECT child.discipline_id FROM tbl_discipline child
                     INNER JOIN subtree s ON child.discipline_parent_id = s.discipline_id
                   )
                   SELECT discipline_id FROM subtree
                 )
                ) as term_count
            FROM tbl_discipline d
            LEFT JOIN tbl_discipline p ON d.discipline_parent_id = p.discipline_id
            ORDER BY d.discipline_name;
        """)
        
        disciplines = cursor.fetchall()
        result = []
        for row in disciplines:
            result.append({
                "id": row[0],
                "name": row[1],
                "handle": row[2],
                "description": row[3],
                "parent_id": row[4],
                "parent_name": row[5],
                "parent_handle": row[6],
                "formula_count": row[7],
                "term_count": row[8] if len(row) > 8 else 0
            })
        
        cursor.close()
        conn.close()
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/disciplines', methods=['POST'])
def api_discipline_create():
    """Create a discipline (admin only)."""
    claims, err = _require_admin()
    if err:
        return err
    data = request.get_json()
    if not data or not isinstance(data, dict):
        return jsonify({"error": "JSON body required"}), 400
    name = (data.get("discipline_name") or data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "discipline_name is required"}), 400
    handle = (data.get("discipline_handle") or data.get("handle") or "").strip()
    if not handle:
        return jsonify({"error": "discipline_handle is required"}), 400
    description = (data.get("discipline_description") or data.get("description") or "").strip() or None
    parent_id = data.get("discipline_parent_id") or data.get("parent_id")
    if parent_id is not None and parent_id != "":
        try:
            parent_id = int(parent_id)
        except (TypeError, ValueError):
            parent_id = None
    else:
        parent_id = None
    sslmode = "require" if DATABASE_URL.startswith("postgres://") else "disable"
    conn = psycopg2.connect(DATABASE_URL, sslmode=sslmode)
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO tbl_discipline (discipline_name, discipline_handle, discipline_description, discipline_parent_id)
            VALUES (%s, %s, %s, %s) RETURNING discipline_id;
        """, (name, handle, description, parent_id))
        did = cur.fetchone()[0]
        conn.commit()
    except psycopg2.IntegrityError as e:
        conn.rollback()
        cur.close()
        conn.close()
        if "discipline_handle" in str(e) or "unique" in str(e).lower():
            return jsonify({"error": "discipline_handle already exists"}), 400
        return jsonify({"error": str(e)}), 400
    cur.execute("""
        SELECT d.discipline_id, d.discipline_name, d.discipline_handle, d.discipline_description, d.discipline_parent_id,
               p.discipline_name, p.discipline_handle
        FROM tbl_discipline d
        LEFT JOIN tbl_discipline p ON d.discipline_parent_id = p.discipline_id
        WHERE d.discipline_id = %s;
    """, (did,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    obj = {
        "id": row[0], "name": row[1], "handle": row[2], "description": row[3], "parent_id": row[4],
        "parent_name": row[5], "parent_handle": row[6], "formula_count": 0, "term_count": 0
    }
    return jsonify(obj), 201


@app.route('/api/disciplines/<int:discipline_id>', methods=['PATCH'])
def api_discipline_update(discipline_id):
    """Update a discipline (admin only)."""
    claims, err = _require_admin()
    if err:
        return err
    data = request.get_json()
    if not data or not isinstance(data, dict):
        return jsonify({"error": "JSON body required"}), 400
    updates = {}
    if "discipline_name" in data or "name" in data:
        s = (str(data.get("discipline_name") or data.get("name") or "")).strip()
        if not s:
            return jsonify({"error": "discipline_name cannot be empty"}), 400
        updates["discipline_name"] = s
    if "discipline_handle" in data or "handle" in data:
        s = (str(data.get("discipline_handle") or data.get("handle") or "")).strip()
        if not s:
            return jsonify({"error": "discipline_handle cannot be empty"}), 400
        updates["discipline_handle"] = s
    if "discipline_description" in data or "description" in data:
        updates["discipline_description"] = (str(data.get("discipline_description") or data.get("description") or "")).strip() or None
    if "discipline_parent_id" in data or "parent_id" in data:
        v = data.get("discipline_parent_id") or data.get("parent_id")
        updates["discipline_parent_id"] = int(v) if v is not None and v != "" else None
    if not updates:
        return jsonify({"error": "No valid fields to update"}), 400
    sslmode = "require" if DATABASE_URL.startswith("postgres://") else "disable"
    conn = psycopg2.connect(DATABASE_URL, sslmode=sslmode)
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM tbl_discipline WHERE discipline_id = %s;", (discipline_id,))
    if cur.fetchone() is None:
        cur.close()
        conn.close()
        return jsonify({"error": "Discipline not found"}), 404
    try:
        set_clause = ", ".join(f"{k} = %s" for k in updates) + ", updated_at = CURRENT_TIMESTAMP"
        vals = [updates[k] for k in updates]
        cur.execute(f"UPDATE tbl_discipline SET {set_clause} WHERE discipline_id = %s;", vals + [discipline_id])
        conn.commit()
    except psycopg2.IntegrityError as e:
        conn.rollback()
        cur.close()
        conn.close()
        if "discipline_handle" in str(e) or "unique" in str(e).lower():
            return jsonify({"error": "discipline_handle already exists"}), 400
        return jsonify({"error": str(e)}), 400
    cur.execute("""
        SELECT d.discipline_id, d.discipline_name, d.discipline_handle, d.discipline_description, d.discipline_parent_id,
               p.discipline_name, p.discipline_handle,
               (SELECT COUNT(DISTINCT fd.formula_id) FROM tbl_formula_discipline fd
                WHERE fd.discipline_id IN (WITH RECURSIVE subtree AS (
                  SELECT discipline_id FROM tbl_discipline WHERE discipline_id = d.discipline_id
                  UNION ALL SELECT child.discipline_id FROM tbl_discipline child
                  INNER JOIN subtree s ON child.discipline_parent_id = s.discipline_id
                ) SELECT discipline_id FROM subtree)),
               (SELECT COUNT(DISTINCT td.term_id) FROM tbl_term_discipline td
                WHERE td.discipline_id IN (WITH RECURSIVE subtree AS (
                  SELECT discipline_id FROM tbl_discipline WHERE discipline_id = d.discipline_id
                  UNION ALL SELECT child.discipline_id FROM tbl_discipline child
                  INNER JOIN subtree s ON child.discipline_parent_id = s.discipline_id
                ) SELECT discipline_id FROM subtree))
        FROM tbl_discipline d
        LEFT JOIN tbl_discipline p ON d.discipline_parent_id = p.discipline_id
        WHERE d.discipline_id = %s;
    """, (discipline_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    obj = {
        "id": row[0], "name": row[1], "handle": row[2], "description": row[3], "parent_id": row[4],
        "parent_name": row[5], "parent_handle": row[6], "formula_count": row[7] or 0, "term_count": row[8] or 0
    }
    return jsonify(obj), 200


@app.route('/api/disciplines/import', methods=['POST'])
def api_disciplines_import():
    """Bulk import disciplines from JSON (admin only). Existing IDs are updated; new records (null/absent id) are inserted."""
    claims, err = _require_admin()
    if err:
        return err
    data = request.get_json()
    if not data or not isinstance(data, dict):
        return jsonify({"error": "JSON body required"}), 400
    items = data.get("disciplines")
    if not isinstance(items, list):
        return jsonify({"error": "disciplines array required"}), 400

    seen_ids = set()
    for i, row in enumerate(items):
        if not isinstance(row, dict):
            return jsonify({
                "error": "Invalid file format.",
                "details": [f"Record {i + 1} is not a valid object. Each discipline must be a JSON object with discipline_name and discipline_handle."]
            }), 400
        did = row.get("discipline_id") or row.get("id")
        if did is not None:
            try:
                did = int(did)
            except (TypeError, ValueError):
                return jsonify({
                    "error": "Invalid discipline_id.",
                    "details": [f"Record {i + 1} has an invalid discipline_id. It must be a number, or omit the field to create a new record."]
                }), 400
            if did in seen_ids:
                return jsonify({
                    "error": "Duplicate discipline_id.",
                    "details": [f"Record {i + 1} uses discipline_id {did}, which appears more than once. Each discipline_id must be unique in the file."]
                }), 400
            seen_ids.add(did)

    sslmode = "require" if DATABASE_URL.startswith("postgres://") else "disable"
    conn = psycopg2.connect(DATABASE_URL, sslmode=sslmode)
    cur = conn.cursor()

    cur.execute("SELECT discipline_id, discipline_handle FROM tbl_discipline;")
    rows_db = cur.fetchall()
    existing_ids = {r[0] for r in rows_db}
    handle_to_id = {r[1]: r[0] for r in rows_db if r[1]}

    inserted = 0
    updated = 0
    errors = []

    for i, row in enumerate(items):
        did = row.get("discipline_id") or row.get("id")
        if did is not None:
            did = int(did)
        name = (str(row.get("discipline_name") or row.get("name") or "")).strip()
        handle = (str(row.get("discipline_handle") or row.get("handle") or "")).strip()
        description = (str(row.get("discipline_description") or row.get("description") or "")).strip() or None
        parent_id = row.get("discipline_parent_id") or row.get("parent_id")
        parent_handle = (str(row.get("discipline_parent_handle") or row.get("parent_handle") or "")).strip() or None
        if parent_id is not None and parent_id != "":
            try:
                parent_id = int(parent_id)
            except (TypeError, ValueError):
                parent_id = None
        elif parent_handle:
            parent_id = handle_to_id.get(parent_handle)
            if parent_id is None:
                label = name or handle or f"record {i + 1}"
                errors.append(
                    f"Record {i + 1} (\"{label}\"): The parent_handle \"{parent_handle}\" does not match any discipline. "
                    "Check the spelling, or ensure the parent discipline appears earlier in the file."
                )
                continue
        else:
            parent_id = None

        if not name:
            errors.append(
                f"Record {i + 1}: Missing discipline_name. Every discipline must have a name."
            )
            continue
        if not handle:
            errors.append(
                f"Record {i + 1} (\"{name}\"): Missing discipline_handle. Every discipline must have a unique handle (e.g. physics, classical_mechanics)."
            )
            continue

        if did is not None:
            if did not in existing_ids:
                errors.append(
                    f"Record {i + 1} (\"{name}\"): discipline_id {did} does not exist in the database. "
                    "To create a new discipline, omit the discipline_id field. To update an existing one, use a valid id from a recent download."
                )
                continue
            try:
                cur.execute("""
                    UPDATE tbl_discipline SET discipline_name = %s, discipline_handle = %s, discipline_description = %s,
                    discipline_parent_id = %s, updated_at = CURRENT_TIMESTAMP WHERE discipline_id = %s;
                """, (name, handle, description, parent_id, did))
                updated += 1
            except psycopg2.IntegrityError as e:
                conn.rollback()
                cur.close()
                conn.close()
                if "discipline_handle" in str(e) or "unique" in str(e).lower():
                    return jsonify({
                        "error": "Duplicate discipline_handle.",
                        "details": [f"Record {i + 1} (\"{name}\"): The handle \"{handle}\" is already used by another discipline. Choose a different handle."]
                    }), 400
                return jsonify({"error": str(e)}), 400
        else:
            if parent_id is not None and parent_id not in existing_ids:
                errors.append(
                    f"Record {i + 1} (\"{name}\"): parent_id {parent_id} does not exist. "
                    "Use an existing discipline_id, or use parent_handle to reference a discipline by its handle."
                )
                continue
            try:
                cur.execute("""
                    INSERT INTO tbl_discipline (discipline_name, discipline_handle, discipline_description, discipline_parent_id)
                    VALUES (%s, %s, %s, %s) RETURNING discipline_id;
                """, (name, handle, description, parent_id))
                new_id = cur.fetchone()[0]
                existing_ids.add(new_id)
                handle_to_id[handle] = new_id
                inserted += 1
            except psycopg2.IntegrityError as e:
                conn.rollback()
                cur.close()
                conn.close()
                if "discipline_handle" in str(e) or "unique" in str(e).lower():
                    return jsonify({
                        "error": "Duplicate discipline_handle.",
                        "details": [f"Record {i + 1} (\"{name}\"): The handle \"{handle}\" is already used by another discipline. Choose a different handle."]
                    }), 400
                return jsonify({"error": str(e)}), 400

    if errors:
        conn.rollback()
        cur.close()
        conn.close()
        return jsonify({
            "error": "The file could not be imported. Please fix the following and try again.",
            "details": errors
        }), 400

    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"message": "Import complete", "inserted": inserted, "updated": updated}), 200


@app.route('/api/disciplines/<int:discipline_id>', methods=['DELETE'])
def api_discipline_delete(discipline_id):
    """Delete a discipline (admin only). Cascades to tbl_formula_discipline, tbl_term_discipline, child disciplines."""
    claims, err = _require_admin()
    if err:
        return err
    sslmode = "require" if DATABASE_URL.startswith("postgres://") else "disable"
    conn = psycopg2.connect(DATABASE_URL, sslmode=sslmode)
    cur = conn.cursor()
    cur.execute("DELETE FROM tbl_discipline WHERE discipline_id = %s RETURNING discipline_id;", (discipline_id,))
    deleted = cur.rowcount
    conn.commit()
    cur.close()
    conn.close()
    if deleted == 0:
        return jsonify({"error": "Discipline not found"}), 404
    return jsonify({"message": "Discipline deleted"}), 200


def get_terms():
    """Get all terms."""
    sslmode = "require" if DATABASE_URL.startswith("postgres://") else "disable"
    conn = psycopg2.connect(DATABASE_URL, sslmode=sslmode)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT term_id, term_name, definition, formulaic_expression
        FROM tbl_term
        ORDER BY term_name;
    """)
    terms = cursor.fetchall()
    result = [{"id": row[0], "term_name": row[1], "definition": row[2], "formulaic_expression": row[3]} for row in terms]
    cursor.close()
    conn.close()
    return result


def get_terms_by_disciplines(discipline_ids, include_children=True):
    """Get terms filtered by discipline IDs, optionally including child disciplines."""
    sslmode = "require" if DATABASE_URL.startswith("postgres://") else "disable"
    conn = psycopg2.connect(DATABASE_URL, sslmode=sslmode)
    cursor = conn.cursor()
    if include_children:
        cursor.execute("""
            WITH RECURSIVE discipline_tree AS (
                SELECT discipline_id FROM tbl_discipline WHERE discipline_id = ANY(%s)
                UNION ALL
                SELECT d.discipline_id
                FROM tbl_discipline d
                INNER JOIN discipline_tree dt ON d.discipline_parent_id = dt.discipline_id
            )
            SELECT DISTINCT t.term_id, t.term_name, t.definition, t.formulaic_expression
            FROM tbl_term t
            INNER JOIN tbl_term_discipline td ON t.term_id = td.term_id
            INNER JOIN discipline_tree dt ON td.discipline_id = dt.discipline_id
            ORDER BY t.term_name;
        """, (discipline_ids,))
    else:
        cursor.execute("""
            SELECT DISTINCT t.term_id, t.term_name, t.definition, t.formulaic_expression
            FROM tbl_term t
            INNER JOIN tbl_term_discipline td ON t.term_id = td.term_id
            WHERE td.discipline_id = ANY(%s)
            ORDER BY t.term_name;
        """, (discipline_ids,))
    terms = cursor.fetchall()
    result = [{"id": row[0], "term_name": row[1], "definition": row[2], "formulaic_expression": row[3]} for row in terms]
    cursor.close()
    conn.close()
    return result


def get_term_by_id(term_id):
    """Get a single term by ID."""
    sslmode = "require" if DATABASE_URL.startswith("postgres://") else "disable"
    conn = psycopg2.connect(DATABASE_URL, sslmode=sslmode)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT term_id, term_name, definition, formulaic_expression
        FROM tbl_term
        WHERE term_id = %s;
    """, (term_id,))
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    if not row:
        return None
    return {"id": row[0], "term_name": row[1], "definition": row[2], "formulaic_expression": row[3]}


def get_questions_by_term_id(term_id):
    """Get all quiz questions linked to a term (top-level only). Same structure as get_questions_by_formula_id."""
    sslmode = "require" if DATABASE_URL.startswith("postgres://") else "disable"
    conn = psycopg2.connect(DATABASE_URL, sslmode=sslmode)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT q.question_id, q.question_type, q.stem, q.explanation, q.display_order
        FROM tbl_question q
        INNER JOIN tbl_term_question tq ON tq.question_id = q.question_id
        WHERE tq.term_id = %s AND q.parent_question_id IS NULL
        ORDER BY q.display_order, q.question_id;
    """, (term_id,))
    rows = cursor.fetchall()
    result = []
    for r in rows:
        qid, qtype, stem, explanation, display_order = r
        cursor.execute("""
            SELECT a.answer_id, a.answer_text, a.answer_numeric, qa.is_correct, qa.display_order
            FROM tbl_question_answer qa
            INNER JOIN tbl_answer a ON a.answer_id = qa.answer_id
            WHERE qa.question_id = %s
            ORDER BY qa.display_order, qa.question_answer_id;
        """, (qid,))
        answers = [{"answer_id": row[0], "answer_text": row[1], "answer_numeric": float(row[2]) if row[2] is not None else None, "is_correct": row[3], "display_order": row[4]} for row in cursor.fetchall()]
        item = {"question_id": qid, "question_type": qtype, "stem": stem, "explanation": explanation, "display_order": display_order, "answers": answers}
        if qtype == "multipart":
            cursor.execute("""
                SELECT question_id, part_label, stem, display_order
                FROM tbl_question
                WHERE parent_question_id = %s
                ORDER BY display_order, question_id;
            """, (qid,))
            parts = []
            for pr in cursor.fetchall():
                pid, plabel, pstem, pord = pr
                cursor.execute("""
                    SELECT a.answer_id, a.answer_text, a.answer_numeric, qa.is_correct, qa.display_order
                    FROM tbl_question_answer qa
                    INNER JOIN tbl_answer a ON a.answer_id = qa.answer_id
                    WHERE qa.question_id = %s
                    ORDER BY qa.display_order;
                """, (pid,))
                part_answers = [{"answer_id": row[0], "answer_text": row[1], "answer_numeric": float(row[2]) if row[2] is not None else None, "is_correct": row[3], "display_order": row[4]} for row in cursor.fetchall()]
                parts.append({"question_id": pid, "part_label": plabel, "stem": pstem, "display_order": pord, "answers": part_answers})
            item["parts"] = parts
        result.append(item)
    cursor.close()
    conn.close()
    return result


# Terms export/import (admin only) - must be before /api/terms/<int:term_id>
@app.route('/api/terms/export', methods=['GET'])
def api_terms_export():
    """Export all terms with discipline links as JSON (admin only)."""
    claims, err = _require_admin()
    if err:
        return err
    sslmode = "require" if DATABASE_URL.startswith("postgres://") else "disable"
    conn = psycopg2.connect(DATABASE_URL, sslmode=sslmode)
    cur = conn.cursor()
    cur.execute("""
        SELECT t.term_id, t.term_name, t.definition, t.formulaic_expression
        FROM tbl_term t
        ORDER BY t.term_name;
    """)
    terms_rows = cur.fetchall()
    cur.execute("""
        SELECT td.term_id, td.discipline_id, d.discipline_handle
        FROM tbl_term_discipline td
        INNER JOIN tbl_discipline d ON d.discipline_id = td.discipline_id;
    """)
    links = cur.fetchall()
    cur.close()
    conn.close()
    disc_by_term = {}
    for tid, did, handle in links:
        disc_by_term.setdefault(tid, []).append({"discipline_id": did, "discipline_handle": handle})
    terms = []
    for row in terms_rows:
        tid, name, definition, formulaic_expr = row
        terms.append({
            "term_id": tid,
            "term_name": name,
            "definition": definition or "",
            "formulaic_expression": formulaic_expr,
            "discipline_ids": [d["discipline_id"] for d in disc_by_term.get(tid, [])],
            "discipline_handles": [d["discipline_handle"] for d in disc_by_term.get(tid, [])],
        })
    return jsonify({"exported_at": __import__("datetime").datetime.utcnow().isoformat() + "Z", "terms": terms})


@app.route('/api/terms/import', methods=['POST'])
def api_terms_import():
    """Bulk import terms from JSON (admin only). Existing IDs are updated; new records (null/absent id) are inserted."""
    claims, err = _require_admin()
    if err:
        return err
    data = request.get_json()
    if not data or not isinstance(data, dict):
        return jsonify({"error": "JSON body required"}), 400
    items = data.get("terms")
    if not isinstance(items, list):
        return jsonify({"error": "terms array required"}), 400

    seen_ids = set()
    for i, row in enumerate(items):
        if not isinstance(row, dict):
            return jsonify({
                "error": "Invalid file format.",
                "details": [f"Record {i + 1} is not a valid object. Each term must be a JSON object with term_name and definition."]
            }), 400
        tid = row.get("term_id") or row.get("id")
        if tid is not None:
            try:
                tid = int(tid)
            except (TypeError, ValueError):
                return jsonify({
                    "error": "Invalid term_id.",
                    "details": [f"Record {i + 1} has an invalid term_id. It must be a number, or omit the field to create a new record."]
                }), 400
            if tid in seen_ids:
                return jsonify({
                    "error": "Duplicate term_id.",
                    "details": [f"Record {i + 1} uses term_id {tid}, which appears more than once."]
                }), 400
            seen_ids.add(tid)

    sslmode = "require" if DATABASE_URL.startswith("postgres://") else "disable"
    conn = psycopg2.connect(DATABASE_URL, sslmode=sslmode)
    cur = conn.cursor()
    cur.execute("SELECT term_id FROM tbl_term;")
    existing_ids = {r[0] for r in cur.fetchall()}
    cur.execute("SELECT discipline_id, discipline_handle FROM tbl_discipline;")
    disc_rows = cur.fetchall()
    handle_to_id = {(r[1].strip().lower() if r[1] else ""): r[0] for r in disc_rows if r[1]}
    existing_disc_ids = {r[0] for r in disc_rows}

    inserted = 0
    updated = 0
    errors = []
    skipped_handles = set()

    for i, row in enumerate(items):
        tid = row.get("term_id") or row.get("id")
        if tid is not None:
            tid = int(tid)
        name = (str(row.get("term_name") or row.get("name") or "")).strip()
        definition = (str(row.get("definition") or "")).strip()
        formulaic_expr = row.get("formulaic_expression")
        if formulaic_expr is not None and formulaic_expr != "":
            formulaic_expr = str(formulaic_expr).strip() or None
        else:
            formulaic_expr = None

        disc_ids = []
        for d in row.get("discipline_ids") or []:
            try:
                did = int(d) if not isinstance(d, int) else d
                if did in existing_disc_ids and did not in disc_ids:
                    disc_ids.append(did)
            except (TypeError, ValueError):
                pass
        for h in row.get("discipline_handles") or []:
            if isinstance(h, str) and h.strip():
                did = handle_to_id.get(h.strip().lower())
                if did is not None and did not in disc_ids:
                    disc_ids.append(did)
                elif did is None:
                    skipped_handles.add(h.strip())

        if not name:
            errors.append(f"Record {i + 1}: Missing term_name.")
            continue
        if not definition:
            errors.append(f"Record {i + 1} (\"{name}\"): Missing definition.")
            continue

        if tid is not None:
            if tid not in existing_ids:
                errors.append(
                    f"Record {i + 1} (\"{name}\"): term_id {tid} does not exist. Omit term_id to create a new term."
                )
                continue
            try:
                cur.execute("""
                    UPDATE tbl_term SET term_name = %s, definition = %s, formulaic_expression = %s,
                    updated_at = CURRENT_TIMESTAMP WHERE term_id = %s;
                """, (name, definition, formulaic_expr, tid))
                updated += 1
                cur.execute("DELETE FROM tbl_term_discipline WHERE term_id = %s;", (tid,))
                for did in disc_ids:
                    cur.execute(
                        "INSERT INTO tbl_term_discipline (term_id, discipline_id, term_discipline_is_primary, term_discipline_rank) VALUES (%s, %s, false, NULL);",
                        (tid, did)
                    )
            except psycopg2.IntegrityError as e:
                conn.rollback()
                cur.close()
                conn.close()
                return jsonify({"error": str(e)}), 400
        else:
            try:
                cur.execute("""
                    INSERT INTO tbl_term (term_name, definition, formulaic_expression)
                    VALUES (%s, %s, %s) RETURNING term_id;
                """, (name, definition, formulaic_expr))
                new_id = cur.fetchone()[0]
                existing_ids.add(new_id)
                inserted += 1
                for did in disc_ids:
                    cur.execute(
                        "INSERT INTO tbl_term_discipline (term_id, discipline_id, term_discipline_is_primary, term_discipline_rank) VALUES (%s, %s, false, NULL);",
                        (new_id, did)
                    )
            except psycopg2.IntegrityError as e:
                conn.rollback()
                cur.close()
                conn.close()
                return jsonify({"error": str(e)}), 400

    if errors:
        conn.rollback()
        cur.close()
        conn.close()
        return jsonify({
            "error": "The file could not be imported. Please fix the following and try again.",
            "details": errors
        }), 400

    conn.commit()
    cur.close()
    conn.close()
    resp = {"message": "Import complete", "inserted": inserted, "updated": updated}
    if skipped_handles:
        resp["skipped_discipline_handles"] = sorted(skipped_handles)
        available = sorted(r[1] for r in disc_rows if r[1])
        resp["available_discipline_handles"] = available
        resp["warning"] = f"Skipped {len(skipped_handles)} discipline handle(s) not found. Requested: {sorted(skipped_handles)}. In database: {available}."
    return jsonify(resp), 200


# Route to fetch all terms (with optional discipline filtering)
@app.route('/api/terms', methods=['GET'])
def fetch_terms():
    try:
        discipline_ids = request.args.getlist('discipline_id', type=int)
        include_children = request.args.get('include_children', 'true').lower() == 'true'
        if discipline_ids:
            terms = get_terms_by_disciplines(discipline_ids, include_children)
        else:
            terms = get_terms()
        return jsonify(terms)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/terms/<int:term_id>', methods=['GET'])
def fetch_term_by_id(term_id):
    try:
        term = get_term_by_id(term_id)
        if term:
            return jsonify(term)
        return jsonify({"error": "Term not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/terms/<int:term_id>/questions', methods=['GET'])
def fetch_term_questions(term_id):
    try:
        questions = get_questions_by_term_id(term_id)
        return jsonify({"questions": questions})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/terms/<int:term_id>', methods=['DELETE'])
def api_term_delete(term_id):
    """Delete a term (admin only). Cascades to tbl_term_discipline, tbl_term_question."""
    claims, err = _require_admin()
    if err:
        return err
    sslmode = "require" if DATABASE_URL.startswith("postgres://") else "disable"
    conn = psycopg2.connect(DATABASE_URL, sslmode=sslmode)
    cur = conn.cursor()
    cur.execute("DELETE FROM tbl_term WHERE term_id = %s RETURNING term_id;", (term_id,))
    deleted = cur.rowcount
    conn.commit()
    cur.close()
    conn.close()
    if deleted == 0:
        return jsonify({"error": "Term not found"}), 404
    return jsonify({"message": "Term deleted"}), 200


@app.route('/api/terms/<int:term_id>', methods=['PATCH'])
def api_term_update(term_id):
    """Update a term (admin only). Accepts partial updates."""
    claims, err = _require_admin()
    if err:
        return err
    data = request.get_json()
    if not data or not isinstance(data, dict):
        return jsonify({"error": "JSON body required"}), 400
    allowed = {"term_name", "definition", "formulaic_expression"}
    updates = {}
    for k in allowed:
        if k not in data:
            continue
        v = data[k]
        if k == "term_name":
            s = (str(v) if v is not None else "").strip()
            if not s:
                return jsonify({"error": "term_name cannot be empty"}), 400
            updates[k] = s
        elif k == "definition":
            s = (str(v) if v is not None else "").strip()
            if not s:
                return jsonify({"error": "definition cannot be empty"}), 400
            updates[k] = s
        else:
            updates[k] = None if v is None or (isinstance(v, str) and not v.strip()) else (v.strip() if isinstance(v, str) else v)
    if not updates:
        return jsonify({"error": "No valid fields to update"}), 400
    sslmode = "require" if DATABASE_URL.startswith("postgres://") else "disable"
    conn = psycopg2.connect(DATABASE_URL, sslmode=sslmode)
    cur = conn.cursor()
    cur.execute("SELECT term_id FROM tbl_term WHERE term_id = %s;", (term_id,))
    if cur.fetchone() is None:
        cur.close()
        conn.close()
        return jsonify({"error": "Term not found"}), 404
    set_parts = [f"{k} = %s" for k in updates]
    set_clause = ", ".join(set_parts) + ", updated_at = CURRENT_TIMESTAMP"
    vals = [updates[k] for k in updates]
    cur.execute(f"UPDATE tbl_term SET {set_clause} WHERE term_id = %s;", vals + [term_id])
    conn.commit()
    cur.close()
    conn.close()
    term = get_term_by_id(term_id)
    return jsonify(term), 200


# ---------------------------------------------------------------------------
# Constants and Units (setup / admin)
# ---------------------------------------------------------------------------

def _get_constants():
    sslmode = "require" if DATABASE_URL.startswith("postgres://") else "disable"
    conn = psycopg2.connect(DATABASE_URL, sslmode=sslmode)
    cur = conn.cursor()
    cur.execute("""
        SELECT constant_id, constant_name, symbol, value_text, description
        FROM tbl_constant ORDER BY constant_name;
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [{"id": r[0], "constant_name": r[1], "symbol": r[2], "value_text": r[3], "description": r[4]} for r in rows]


def _get_units():
    sslmode = "require" if DATABASE_URL.startswith("postgres://") else "disable"
    conn = psycopg2.connect(DATABASE_URL, sslmode=sslmode)
    cur = conn.cursor()
    cur.execute("""
        SELECT unit_id, unit_name, symbol, unit_system, description
        FROM tbl_unit ORDER BY unit_name;
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [{"id": r[0], "unit_name": r[1], "symbol": r[2], "unit_system": r[3], "description": r[4]} for r in rows]


@app.route('/api/constants', methods=['GET'])
def fetch_constants():
    try:
        constants = _get_constants()
        return jsonify(constants)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/constants', methods=['POST'])
def api_constant_create():
    """Create a constant (admin only)."""
    claims, err = _require_admin()
    if err:
        return err
    data = request.get_json()
    if not data or not isinstance(data, dict):
        return jsonify({"error": "JSON body required"}), 400
    name = (data.get("constant_name") or "").strip()
    if not name:
        return jsonify({"error": "constant_name is required"}), 400
    symbol = (data.get("symbol") or "").strip() or None
    value_text = (data.get("value_text") or "").strip() or None
    description = (data.get("description") or "").strip() or None
    sslmode = "require" if DATABASE_URL.startswith("postgres://") else "disable"
    conn = psycopg2.connect(DATABASE_URL, sslmode=sslmode)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO tbl_constant (constant_name, symbol, value_text, description)
        VALUES (%s, %s, %s, %s) RETURNING constant_id;
    """, (name, symbol, value_text, description))
    cid = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    constants = _get_constants()
    obj = next((c for c in constants if c["id"] == cid), None)
    return jsonify(obj or {"id": cid, "constant_name": name, "symbol": symbol, "value_text": value_text, "description": description}), 201


@app.route('/api/constants/<int:constant_id>', methods=['PATCH'])
def api_constant_update(constant_id):
    """Update a constant (admin only)."""
    claims, err = _require_admin()
    if err:
        return err
    data = request.get_json()
    if not data or not isinstance(data, dict):
        return jsonify({"error": "JSON body required"}), 400
    updates = {}
    if "constant_name" in data:
        s = (str(data["constant_name"]) or "").strip()
        if not s:
            return jsonify({"error": "constant_name cannot be empty"}), 400
        updates["constant_name"] = s
    if "symbol" in data:
        updates["symbol"] = (str(data["symbol"]) or "").strip() or None
    if "value_text" in data:
        updates["value_text"] = (str(data["value_text"]) or "").strip() or None
    if "description" in data:
        updates["description"] = (str(data["description"]) or "").strip() or None
    if not updates:
        return jsonify({"error": "No valid fields to update"}), 400
    sslmode = "require" if DATABASE_URL.startswith("postgres://") else "disable"
    conn = psycopg2.connect(DATABASE_URL, sslmode=sslmode)
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM tbl_constant WHERE constant_id = %s;", (constant_id,))
    if cur.fetchone() is None:
        cur.close()
        conn.close()
        return jsonify({"error": "Constant not found"}), 404
    set_clause = ", ".join(f"{k} = %s" for k in updates) + ", updated_at = CURRENT_TIMESTAMP"
    vals = [updates[k] for k in updates]
    cur.execute(f"UPDATE tbl_constant SET {set_clause} WHERE constant_id = %s;", vals + [constant_id])
    conn.commit()
    cur.close()
    conn.close()
    constants = _get_constants()
    obj = next((c for c in constants if c["id"] == constant_id), None)
    return jsonify(obj), 200


@app.route('/api/constants/<int:constant_id>', methods=['DELETE'])
def api_constant_delete(constant_id):
    """Delete a constant (admin only)."""
    claims, err = _require_admin()
    if err:
        return err
    sslmode = "require" if DATABASE_URL.startswith("postgres://") else "disable"
    conn = psycopg2.connect(DATABASE_URL, sslmode=sslmode)
    cur = conn.cursor()
    cur.execute("DELETE FROM tbl_constant WHERE constant_id = %s RETURNING constant_id;", (constant_id,))
    deleted = cur.rowcount
    conn.commit()
    cur.close()
    conn.close()
    if deleted == 0:
        return jsonify({"error": "Constant not found"}), 404
    return jsonify({"message": "Constant deleted"}), 200


@app.route('/api/units', methods=['GET'])
def fetch_units():
    try:
        units = _get_units()
        return jsonify(units)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/units', methods=['POST'])
def api_unit_create():
    """Create a unit (admin only)."""
    claims, err = _require_admin()
    if err:
        return err
    data = request.get_json()
    if not data or not isinstance(data, dict):
        return jsonify({"error": "JSON body required"}), 400
    name = (data.get("unit_name") or "").strip()
    if not name:
        return jsonify({"error": "unit_name is required"}), 400
    symbol = (data.get("symbol") or "").strip() or None
    unit_system = (data.get("unit_system") or "").strip() or None
    description = (data.get("description") or "").strip() or None
    sslmode = "require" if DATABASE_URL.startswith("postgres://") else "disable"
    conn = psycopg2.connect(DATABASE_URL, sslmode=sslmode)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO tbl_unit (unit_name, symbol, unit_system, description)
        VALUES (%s, %s, %s, %s) RETURNING unit_id;
    """, (name, symbol, unit_system, description))
    uid = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    units = _get_units()
    obj = next((u for u in units if u["id"] == uid), None)
    return jsonify(obj or {"id": uid, "unit_name": name, "symbol": symbol, "unit_system": unit_system, "description": description}), 201


@app.route('/api/units/<int:unit_id>', methods=['PATCH'])
def api_unit_update(unit_id):
    """Update a unit (admin only)."""
    claims, err = _require_admin()
    if err:
        return err
    data = request.get_json()
    if not data or not isinstance(data, dict):
        return jsonify({"error": "JSON body required"}), 400
    updates = {}
    if "unit_name" in data:
        s = (str(data["unit_name"]) or "").strip()
        if not s:
            return jsonify({"error": "unit_name cannot be empty"}), 400
        updates["unit_name"] = s
    if "symbol" in data:
        updates["symbol"] = (str(data["symbol"]) or "").strip() or None
    if "unit_system" in data:
        updates["unit_system"] = (str(data["unit_system"]) or "").strip() or None
    if "description" in data:
        updates["description"] = (str(data["description"]) or "").strip() or None
    if not updates:
        return jsonify({"error": "No valid fields to update"}), 400
    sslmode = "require" if DATABASE_URL.startswith("postgres://") else "disable"
    conn = psycopg2.connect(DATABASE_URL, sslmode=sslmode)
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM tbl_unit WHERE unit_id = %s;", (unit_id,))
    if cur.fetchone() is None:
        cur.close()
        conn.close()
        return jsonify({"error": "Unit not found"}), 404
    set_clause = ", ".join(f"{k} = %s" for k in updates) + ", updated_at = CURRENT_TIMESTAMP"
    vals = [updates[k] for k in updates]
    cur.execute(f"UPDATE tbl_unit SET {set_clause} WHERE unit_id = %s;", vals + [unit_id])
    conn.commit()
    cur.close()
    conn.close()
    units = _get_units()
    obj = next((u for u in units if u["id"] == unit_id), None)
    return jsonify(obj), 200


@app.route('/api/units/<int:unit_id>', methods=['DELETE'])
def api_unit_delete(unit_id):
    """Delete a unit (admin only)."""
    claims, err = _require_admin()
    if err:
        return err
    sslmode = "require" if DATABASE_URL.startswith("postgres://") else "disable"
    conn = psycopg2.connect(DATABASE_URL, sslmode=sslmode)
    cur = conn.cursor()
    cur.execute("DELETE FROM tbl_unit WHERE unit_id = %s RETURNING unit_id;", (unit_id,))
    deleted = cur.rowcount
    conn.commit()
    cur.close()
    conn.close()
    if deleted == 0:
        return jsonify({"error": "Unit not found"}), 404
    return jsonify({"message": "Unit deleted"}), 200


# Formulas export/import (admin only) - must be before /api/formulas/<int:formula_id>
@app.route('/api/formulas/export', methods=['GET'])
def api_formulas_export():
    """Export all formulas with discipline links as JSON (admin only)."""
    claims, err = _require_admin()
    if err:
        return err
    sslmode = "require" if DATABASE_URL.startswith("postgres://") else "disable"
    conn = psycopg2.connect(DATABASE_URL, sslmode=sslmode)
    cur = conn.cursor()
    cur.execute("""
        SELECT formula_id, formula_name, latex, formula_description, english_verbalization,
               symbolic_verbalization, units, example, historical_context
        FROM tbl_formula
        ORDER BY formula_name;
    """)
    formulas_rows = cur.fetchall()
    cur.execute("""
        SELECT fd.formula_id, fd.discipline_id, d.discipline_handle
        FROM tbl_formula_discipline fd
        INNER JOIN tbl_discipline d ON d.discipline_id = fd.discipline_id;
    """)
    links = cur.fetchall()
    cur.close()
    conn.close()
    disc_by_formula = {}
    for fid, did, handle in links:
        disc_by_formula.setdefault(fid, []).append({"discipline_id": did, "discipline_handle": handle})
    formulas = []
    for row in formulas_rows:
        fid, name, latex, desc, eng_verb, sym_verb, units, example, hist = row
        formulas.append({
            "formula_id": fid,
            "formula_name": name,
            "latex": latex or "",
            "formula_description": desc,
            "english_verbalization": eng_verb,
            "symbolic_verbalization": sym_verb,
            "units": units,
            "example": example,
            "historical_context": hist,
            "discipline_ids": [d["discipline_id"] for d in disc_by_formula.get(fid, [])],
            "discipline_handles": [d["discipline_handle"] for d in disc_by_formula.get(fid, [])],
        })
    return jsonify({"exported_at": __import__("datetime").datetime.utcnow().isoformat() + "Z", "formulas": formulas})


@app.route('/api/formulas/import', methods=['POST'])
def api_formulas_import():
    """Bulk import formulas from JSON (admin only). Existing IDs are updated; new records (null/absent id) are inserted."""
    claims, err = _require_admin()
    if err:
        return err
    data = request.get_json()
    if not data or not isinstance(data, dict):
        return jsonify({"error": "JSON body required"}), 400
    items = data.get("formulas")
    if not isinstance(items, list):
        return jsonify({"error": "formulas array required"}), 400

    seen_ids = set()
    for i, row in enumerate(items):
        if not isinstance(row, dict):
            return jsonify({
                "error": "Invalid file format.",
                "details": [f"Record {i + 1} is not a valid object. Each formula must have formula_name and latex."]
            }), 400
        fid = row.get("formula_id") or row.get("id")
        if fid is not None:
            try:
                fid = int(fid)
            except (TypeError, ValueError):
                return jsonify({
                    "error": "Invalid formula_id.",
                    "details": [f"Record {i + 1} has an invalid formula_id. Omit to create a new record."]
                }), 400
            if fid in seen_ids:
                return jsonify({
                    "error": "Duplicate formula_id.",
                    "details": [f"Record {i + 1} uses formula_id {fid} more than once."]
                }), 400
            seen_ids.add(fid)

    sslmode = "require" if DATABASE_URL.startswith("postgres://") else "disable"
    conn = psycopg2.connect(DATABASE_URL, sslmode=sslmode)
    cur = conn.cursor()
    cur.execute("SELECT formula_id FROM tbl_formula;")
    existing_ids = {r[0] for r in cur.fetchall()}
    cur.execute("SELECT discipline_id, discipline_handle FROM tbl_discipline;")
    disc_rows = cur.fetchall()
    handle_to_id = {(r[1].strip().lower() if r[1] else ""): r[0] for r in disc_rows if r[1]}
    existing_disc_ids = {r[0] for r in disc_rows}

    inserted = 0
    updated = 0
    errors = []
    skipped_handles = set()

    def _opt(v):
        return None if v is None or v == "" else (str(v).strip() or None)

    for i, row in enumerate(items):
        fid = row.get("formula_id") or row.get("id")
        if fid is not None:
            fid = int(fid)
        name = (str(row.get("formula_name") or row.get("name") or "")).strip()
        latex = (str(row.get("latex") or "")).strip()
        desc = _opt(row.get("formula_description") or row.get("description"))
        eng_verb = _opt(row.get("english_verbalization"))
        sym_verb = _opt(row.get("symbolic_verbalization"))
        units = _opt(row.get("units"))
        example = _opt(row.get("example"))
        hist = _opt(row.get("historical_context"))

        disc_ids = []
        for d in row.get("discipline_ids") or []:
            try:
                did = int(d) if not isinstance(d, int) else d
                if did in existing_disc_ids and did not in disc_ids:
                    disc_ids.append(did)
            except (TypeError, ValueError):
                pass
        for h in row.get("discipline_handles") or []:
            if isinstance(h, str) and h.strip():
                did = handle_to_id.get(h.strip().lower())
                if did is not None and did not in disc_ids:
                    disc_ids.append(did)
                elif did is None:
                    skipped_handles.add(h.strip())

        if not name:
            errors.append(f"Record {i + 1}: Missing formula_name.")
            continue
        if not latex:
            errors.append(f"Record {i + 1} (\"{name}\"): Missing latex.")
            continue

        if fid is not None:
            if fid not in existing_ids:
                errors.append(
                    f"Record {i + 1} (\"{name}\"): formula_id {fid} does not exist. Omit formula_id to create a new formula."
                )
                continue
            try:
                cur.execute("""
                    UPDATE tbl_formula SET formula_name = %s, latex = %s, formula_description = %s,
                    english_verbalization = %s, symbolic_verbalization = %s, units = %s, example = %s, historical_context = %s,
                    updated_at = CURRENT_TIMESTAMP WHERE formula_id = %s;
                """, (name, latex, desc, eng_verb, sym_verb, units, example, hist, fid))
                updated += 1
                cur.execute("DELETE FROM tbl_formula_discipline WHERE formula_id = %s;", (fid,))
                for did in disc_ids:
                    cur.execute(
                        "INSERT INTO tbl_formula_discipline (formula_id, discipline_id, formula_discipline_is_primary, formula_discipline_rank) VALUES (%s, %s, false, NULL);",
                        (fid, did)
                    )
            except psycopg2.IntegrityError as e:
                conn.rollback()
                cur.close()
                conn.close()
                return jsonify({"error": str(e)}), 400
        else:
            try:
                cur.execute("""
                    INSERT INTO tbl_formula (formula_name, latex, formula_description,
                    english_verbalization, symbolic_verbalization, units, example, historical_context)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING formula_id;
                """, (name, latex, desc, eng_verb, sym_verb, units, example, hist))
                new_id = cur.fetchone()[0]
                existing_ids.add(new_id)
                inserted += 1
                for did in disc_ids:
                    cur.execute(
                        "INSERT INTO tbl_formula_discipline (formula_id, discipline_id, formula_discipline_is_primary, formula_discipline_rank) VALUES (%s, %s, false, NULL);",
                        (new_id, did)
                    )
            except psycopg2.IntegrityError as e:
                conn.rollback()
                cur.close()
                conn.close()
                return jsonify({"error": str(e)}), 400

    if errors:
        conn.rollback()
        cur.close()
        conn.close()
        return jsonify({
            "error": "The file could not be imported. Please fix the following and try again.",
            "details": errors
        }), 400

    conn.commit()
    cur.close()
    conn.close()
    resp = {"message": "Import complete", "inserted": inserted, "updated": updated}
    if skipped_handles:
        resp["skipped_discipline_handles"] = sorted(skipped_handles)
        available = sorted(r[1] for r in disc_rows if r[1])
        resp["available_discipline_handles"] = available
        resp["warning"] = f"Skipped {len(skipped_handles)} discipline handle(s) not found. Requested: {sorted(skipped_handles)}. In database: {available}."
    return jsonify(resp), 200


# Route to fetch all formulas (with optional discipline filtering)
@app.route('/api/formulas', methods=['GET'])
def fetch_formulas():
    try:
        # Check for discipline filter in query parameters
        discipline_ids = request.args.getlist('discipline_id', type=int)
        include_children = request.args.get('include_children', 'true').lower() == 'true'
        
        if discipline_ids:
            formulas = get_formulas_by_disciplines(discipline_ids, include_children)
        else:
            formulas = get_formulas()
        return jsonify(formulas)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/formulas/with-questions', methods=['GET'])
def fetch_formulas_with_questions():
    """Return all formulas with their linked questions and answers. Public, no auth required."""
    try:
        formulas = get_formulas()
        result = []
        for f in formulas:
            questions = get_questions_by_formula_id(f["id"])
            result.append({"formula": f, "questions": questions})
        return jsonify({"formulas": result})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/formulas/<int:formula_id>', methods=['DELETE'])
def api_formula_delete(formula_id):
    """Delete a formula (admin only). Cascades to related tables."""
    claims, err = _require_admin()
    if err:
        return err
    sslmode = "require" if DATABASE_URL.startswith("postgres://") else "disable"
    conn = psycopg2.connect(DATABASE_URL, sslmode=sslmode)
    cur = conn.cursor()
    cur.execute("DELETE FROM tbl_formula WHERE formula_id = %s RETURNING formula_id;", (formula_id,))
    deleted = cur.rowcount
    conn.commit()
    cur.close()
    conn.close()
    if deleted == 0:
        return jsonify({"error": "Formula not found"}), 404
    return jsonify({"message": "Formula deleted"}), 200


@app.route('/api/formulas/<int:formula_id>', methods=['PATCH'])
def api_formula_update(formula_id):
    """Update a formula (admin only). Accepts partial updates."""
    claims, err = _require_admin()
    if err:
        return err
    data = request.get_json()
    if not data or not isinstance(data, dict):
        return jsonify({"error": "JSON body required"}), 400
    allowed = {"formula_name", "latex", "formula_description", "english_verbalization",
               "symbolic_verbalization", "example", "historical_context", "units"}
    updates = {}
    for k in allowed:
        if k not in data:
            continue
        v = data[k]
        if k == "formula_name":
            s = (str(v) if v is not None else "").strip()
            if not s:
                return jsonify({"error": "formula_name cannot be empty"}), 400
            updates[k] = s
        elif k == "latex":
            s = (str(v) if v is not None else "").strip()
            if not s:
                return jsonify({"error": "latex cannot be empty"}), 400
            updates[k] = s
        else:
            updates[k] = None if v is None or (isinstance(v, str) and not v.strip()) else v.strip() if isinstance(v, str) else v
    if not updates:
        return jsonify({"error": "No valid fields to update"}), 400
    sslmode = "require" if DATABASE_URL.startswith("postgres://") else "disable"
    conn = psycopg2.connect(DATABASE_URL, sslmode=sslmode)
    cur = conn.cursor()
    cur.execute("SELECT formula_id FROM tbl_formula WHERE formula_id = %s;", (formula_id,))
    if cur.fetchone() is None:
        cur.close()
        conn.close()
        return jsonify({"error": "Formula not found"}), 404
    set_clause = ", ".join(f"{k} = %s" for k in updates)
    set_clause += ", updated_at = CURRENT_TIMESTAMP"
    vals = [updates[k] for k in updates]
    cur.execute(f"UPDATE tbl_formula SET {set_clause} WHERE formula_id = %s;", vals + [formula_id])
    conn.commit()
    cur.close()
    conn.close()
    formula = get_formula_by_id(formula_id)
    return jsonify(formula), 200


# Route to fetch a single formula by ID
@app.route('/api/formulas/<int:formula_id>', methods=['GET'])
def fetch_formula_by_id(formula_id):
    try:
        formula = get_formula_by_id(formula_id)
        if formula:
            return jsonify(formula)
        else:
            return jsonify({"error": "Formula not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def get_questions_by_formula_id(formula_id):
    """Get all quiz questions linked to a formula (top-level only). Includes answers; multipart includes parts."""
    sslmode = "require" if DATABASE_URL.startswith("postgres://") else "disable"
    conn = psycopg2.connect(DATABASE_URL, sslmode=sslmode)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT q.question_id, q.question_type, q.stem, q.explanation, q.display_order
        FROM tbl_question q
        INNER JOIN tbl_formula_question fq ON fq.question_id = q.question_id
        WHERE fq.formula_id = %s AND q.parent_question_id IS NULL
        ORDER BY q.display_order, q.question_id;
    """, (formula_id,))
    rows = cursor.fetchall()
    result = []
    for r in rows:
        qid, qtype, stem, explanation, display_order = r
        # Answers for this question
        cursor.execute("""
            SELECT a.answer_id, a.answer_text, a.answer_numeric, qa.is_correct, qa.display_order
            FROM tbl_question_answer qa
            INNER JOIN tbl_answer a ON a.answer_id = qa.answer_id
            WHERE qa.question_id = %s
            ORDER BY qa.display_order, qa.question_answer_id;
        """, (qid,))
        answers = [{"answer_id": row[0], "answer_text": row[1], "answer_numeric": float(row[2]) if row[2] is not None else None, "is_correct": row[3], "display_order": row[4]} for row in cursor.fetchall()]
        item = {"question_id": qid, "question_type": qtype, "stem": stem, "explanation": explanation, "display_order": display_order, "answers": answers}
        if qtype == "multipart":
            cursor.execute("""
                SELECT question_id, part_label, stem, display_order
                FROM tbl_question
                WHERE parent_question_id = %s
                ORDER BY display_order, question_id;
            """, (qid,))
            parts = []
            for pr in cursor.fetchall():
                pid, plabel, pstem, pord = pr
                cursor.execute("""
                    SELECT a.answer_id, a.answer_text, a.answer_numeric, qa.is_correct, qa.display_order
                    FROM tbl_question_answer qa
                    INNER JOIN tbl_answer a ON a.answer_id = qa.answer_id
                    WHERE qa.question_id = %s
                    ORDER BY qa.display_order;
                """, (pid,))
                part_answers = [{"answer_id": row[0], "answer_text": row[1], "answer_numeric": float(row[2]) if row[2] is not None else None, "is_correct": row[3], "display_order": row[4]} for row in cursor.fetchall()]
                parts.append({"question_id": pid, "part_label": plabel, "stem": pstem, "display_order": pord, "answers": part_answers})
            item["parts"] = parts
        result.append(item)
    cursor.close()
    conn.close()
    return result


@app.route('/api/formulas/<int:formula_id>/questions', methods=['GET'])
def fetch_formula_questions(formula_id):
    try:
        questions = get_questions_by_formula_id(formula_id)
        return jsonify({"questions": questions})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Questions export/import (admin only)
@app.route('/api/questions/export', methods=['GET'])
def api_questions_export():
    """Export all questions with answers and formula/term links as JSON (admin only)."""
    claims, err = _require_admin()
    if err:
        return err
    sslmode = "require" if DATABASE_URL.startswith("postgres://") else "disable"
    conn = psycopg2.connect(DATABASE_URL, sslmode=sslmode)
    cur = conn.cursor()
    cur.execute("""
        SELECT q.question_id, q.question_type, q.stem, q.explanation, q.display_order
        FROM tbl_question q
        WHERE q.parent_question_id IS NULL
        ORDER BY q.display_order, q.question_id;
    """)
    rows = cur.fetchall()
    formula_links = {}
    cur.execute("SELECT formula_id, question_id FROM tbl_formula_question;")
    for fid, qid in cur.fetchall():
        formula_links.setdefault(qid, []).append(fid)
    term_links = {}
    cur.execute("SELECT term_id, question_id FROM tbl_term_question;")
    for tid, qid in cur.fetchall():
        term_links.setdefault(qid, []).append(tid)
    questions_out = []
    for r in rows:
        qid, qtype, stem, explanation, display_order = r
        cur.execute("""
            SELECT a.answer_text, a.answer_numeric, qa.is_correct, qa.display_order
            FROM tbl_question_answer qa
            INNER JOIN tbl_answer a ON a.answer_id = qa.answer_id
            WHERE qa.question_id = %s
            ORDER BY qa.display_order, qa.question_answer_id;
        """, (qid,))
        answers = [
            {"answer_text": row[0] or "", "answer_numeric": float(row[1]) if row[1] is not None else None, "is_correct": row[2], "display_order": row[3]}
            for row in cur.fetchall()
        ]
        item = {
            "question_id": qid,
            "question_type": qtype,
            "stem": stem or "",
            "explanation": explanation or "",
            "display_order": display_order,
            "answers": answers,
            "formula_ids": formula_links.get(qid, []),
            "term_ids": term_links.get(qid, []),
        }
        if qtype == "multipart":
            cur.execute("""
                SELECT question_id, part_label, stem, display_order
                FROM tbl_question
                WHERE parent_question_id = %s
                ORDER BY display_order, question_id;
            """, (qid,))
            parts = []
            for pr in cur.fetchall():
                pid, plabel, pstem, pord = pr
                cur.execute("""
                    SELECT a.answer_text, a.answer_numeric, qa.is_correct, qa.display_order
                    FROM tbl_question_answer qa
                    INNER JOIN tbl_answer a ON a.answer_id = qa.answer_id
                    WHERE qa.question_id = %s
                    ORDER BY qa.display_order;
                """, (pid,))
                part_answers = [
                    {"answer_text": row[0] or "", "answer_numeric": float(row[1]) if row[1] is not None else None, "is_correct": row[2], "display_order": row[3]}
                    for row in cur.fetchall()
                ]
                parts.append({"question_id": pid, "part_label": plabel or "", "stem": pstem or "", "display_order": pord, "answers": part_answers})
            item["parts"] = parts
        questions_out.append(item)
    cur.close()
    conn.close()
    return jsonify({"exported_at": __import__("datetime").datetime.utcnow().isoformat() + "Z", "questions": questions_out})


@app.route('/api/questions/import', methods=['POST'])
def api_questions_import():
    """Bulk import questions with answers from JSON (admin only). Existing question_id → update; null/absent → insert."""
    claims, err = _require_admin()
    if err:
        return err
    data = request.get_json()
    if not data or not isinstance(data, dict):
        return jsonify({"error": "JSON body required"}), 400
    items = data.get("questions")
    if not isinstance(items, list):
        return jsonify({"error": "questions array required"}), 400

    seen_ids = set()
    for i, row in enumerate(items):
        if not isinstance(row, dict):
            return jsonify({
                "error": "Invalid file format.",
                "details": [f"Record {i + 1} is not a valid object. Each question must have question_type and stem."]
            }), 400
        qid = row.get("question_id") or row.get("id")
        if qid is not None:
            try:
                qid = int(qid)
            except (TypeError, ValueError):
                return jsonify({
                    "error": "Invalid question_id.",
                    "details": [f"Record {i + 1} has an invalid question_id. Omit to create a new record."]
                }), 400
            if qid in seen_ids:
                return jsonify({
                    "error": "Duplicate question_id.",
                    "details": [f"Record {i + 1} uses question_id {qid} more than once."]
                }), 400
            seen_ids.add(qid)

    sslmode = "require" if DATABASE_URL.startswith("postgres://") else "disable"
    conn = psycopg2.connect(DATABASE_URL, sslmode=sslmode)
    cur = conn.cursor()
    cur.execute("SELECT question_id FROM tbl_question;")
    existing_ids = {r[0] for r in cur.fetchall()}
    cur.execute("SELECT formula_id FROM tbl_formula;")
    existing_formula_ids = {r[0] for r in cur.fetchall()}
    cur.execute("SELECT term_id FROM tbl_term;")
    existing_term_ids = {r[0] for r in cur.fetchall()}

    inserted = 0
    updated = 0
    errors = []

    def _upsert_question_answers(cur, question_id, answers):
        cur.execute("DELETE FROM tbl_question_answer WHERE question_id = %s;", (question_id,))
        for a in answers or []:
            atext = (str(a.get("answer_text") or "")).strip()
            anum = a.get("answer_numeric")
            if anum is not None:
                try:
                    anum = float(anum)
                except (TypeError, ValueError):
                    anum = None
            is_correct = bool(a.get("is_correct"))
            dord = a.get("display_order")
            try:
                dord = int(dord) if dord is not None else 0
            except (TypeError, ValueError):
                dord = 0
            cur.execute("INSERT INTO tbl_answer (answer_text, answer_numeric) VALUES (%s, %s) RETURNING answer_id;", (atext, anum))
            aid = cur.fetchone()[0]
            cur.execute("INSERT INTO tbl_question_answer (question_id, answer_id, is_correct, display_order) VALUES (%s, %s, %s, %s);", (question_id, aid, is_correct, dord))

    def _set_formula_term_links(cur, question_id, formula_ids, term_ids):
        cur.execute("DELETE FROM tbl_formula_question WHERE question_id = %s;", (question_id,))
        cur.execute("DELETE FROM tbl_term_question WHERE question_id = %s;", (question_id,))
        for fid in formula_ids or []:
            try:
                fid = int(fid)
                if fid in existing_formula_ids:
                    cur.execute("INSERT INTO tbl_formula_question (formula_id, question_id, formula_question_is_primary) VALUES (%s, %s, true);", (fid, question_id))
            except (TypeError, ValueError):
                pass
        for tid in term_ids or []:
            try:
                tid = int(tid)
                if tid in existing_term_ids:
                    cur.execute("INSERT INTO tbl_term_question (term_id, question_id, term_question_is_primary) VALUES (%s, %s, true);", (tid, question_id))
            except (TypeError, ValueError):
                pass

    for i, row in enumerate(items):
        qid = row.get("question_id") or row.get("id")
        if qid is not None:
            qid = int(qid)
        qtype = (str(row.get("question_type") or "")).strip()
        stem = (str(row.get("stem") or "")).strip()
        explanation = row.get("explanation")
        explanation = (str(explanation).strip() or None) if explanation is not None else None
        display_order = row.get("display_order")
        try:
            display_order = int(display_order) if display_order is not None else 0
        except (TypeError, ValueError):
            display_order = 0
        formula_ids = row.get("formula_ids") or []
        term_ids = row.get("term_ids") or []

        if qtype not in ("multiple_choice", "true_false", "word_problem", "multipart"):
            errors.append(f"Record {i + 1}: question_type must be one of: multiple_choice, true_false, word_problem, multipart.")
            continue
        if not stem:
            errors.append(f"Record {i + 1}: Missing stem.")
            continue

        if qid is not None:
            if qid not in existing_ids:
                errors.append(f"Record {i + 1}: question_id {qid} does not exist. Omit to create a new question.")
                continue
            try:
                cur.execute(
                    "UPDATE tbl_question SET question_type = %s, stem = %s, explanation = %s, display_order = %s, updated_at = CURRENT_TIMESTAMP WHERE question_id = %s;",
                    (qtype, stem, explanation, display_order, qid),
                )
                updated += 1
                _upsert_question_answers(cur, qid, row.get("answers"))
                if qtype == "multipart":
                    parts = row.get("parts") or []
                    cur.execute("SELECT question_id FROM tbl_question WHERE parent_question_id = %s;", (qid,))
                    existing_parts = {r[0] for r in cur.fetchall()}
                    for pi, p in enumerate(parts):
                        if not isinstance(p, dict):
                            continue
                        pid = p.get("question_id") or p.get("id")
                        pid = int(pid) if pid is not None else None
                        plabel = (str(p.get("part_label") or "")).strip() or None
                        pstem = (str(p.get("stem") or "")).strip()
                        pord = p.get("display_order")
                        try:
                            pord = int(pord) if pord is not None else pi
                        except (TypeError, ValueError):
                            pord = pi
                        if pid is not None and pid in existing_parts:
                            cur.execute(
                                "UPDATE tbl_question SET part_label = %s, stem = %s, display_order = %s, updated_at = CURRENT_TIMESTAMP WHERE question_id = %s;",
                                (plabel, pstem, pord, pid),
                            )
                            _upsert_question_answers(cur, pid, p.get("answers"))
                        else:
                            cur.execute(
                                "INSERT INTO tbl_question (question_type, stem, parent_question_id, part_label, display_order) VALUES ('multipart', %s, %s, %s, %s) RETURNING question_id;",
                                (pstem, qid, plabel, pord),
                            )
                            new_pid = cur.fetchone()[0]
                            _upsert_question_answers(cur, new_pid, p.get("answers"))
                _set_formula_term_links(cur, qid, formula_ids, term_ids)
            except psycopg2.IntegrityError as e:
                conn.rollback()
                cur.close()
                conn.close()
                return jsonify({"error": str(e)}), 400
        else:
            try:
                cur.execute(
                    "INSERT INTO tbl_question (question_type, stem, explanation, display_order) VALUES (%s, %s, %s, %s) RETURNING question_id;",
                    (qtype, stem, explanation, display_order),
                )
                new_id = cur.fetchone()[0]
                existing_ids.add(new_id)
                inserted += 1
                _upsert_question_answers(cur, new_id, row.get("answers"))
                if qtype == "multipart":
                    parts = row.get("parts") or []
                    for pi, p in enumerate(parts):
                        if not isinstance(p, dict):
                            continue
                        plabel = (str(p.get("part_label") or "")).strip() or None
                        pstem = (str(p.get("stem") or "")).strip()
                        pord = p.get("display_order")
                        try:
                            pord = int(pord) if pord is not None else pi
                        except (TypeError, ValueError):
                            pord = pi
                        cur.execute(
                            "INSERT INTO tbl_question (question_type, stem, parent_question_id, part_label, display_order) VALUES ('multipart', %s, %s, %s, %s) RETURNING question_id;",
                            (pstem, new_id, plabel, pord),
                        )
                        part_id = cur.fetchone()[0]
                        _upsert_question_answers(cur, part_id, p.get("answers"))
                _set_formula_term_links(cur, new_id, formula_ids, term_ids)
            except psycopg2.IntegrityError as e:
                conn.rollback()
                cur.close()
                conn.close()
                return jsonify({"error": str(e)}), 400

    if errors:
        conn.rollback()
        cur.close()
        conn.close()
        return jsonify({
            "error": "The file could not be imported. Please fix the following and try again.",
            "details": errors
        }), 400

    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"message": "Import complete", "inserted": inserted, "updated": updated}), 200


# ---------------------------------------------------------------------------
# Auth: register, login, logout, me
# ---------------------------------------------------------------------------

@app.route('/api/auth/register', methods=['POST'])
def auth_register():
    try:
        data = request.get_json() or {}
        email = (data.get("email") or "").strip().lower()
        password = data.get("password") or ""
        display_name = (data.get("display_name") or "").strip() or None
        if not email or not password:
            return jsonify({"error": "Email and password are required"}), 400
        if len(password) < 8:
            return jsonify({"error": "Password must be at least 8 characters"}), 400
        conn = _auth_db()
        cur = conn.cursor()
        cur.execute("SELECT user_id, email, display_name FROM tbl_user WHERE email = %s;", (email,))
        existing = cur.fetchone()
        if existing:
            cur.close()
            conn.close()
            return jsonify({"error": "An account with this email already exists"}), 409
        password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        cur.execute(
            "INSERT INTO tbl_user (email, password_hash, display_name) VALUES (%s, %s, %s) RETURNING user_id, email, display_name;",
            (email, password_hash, display_name),
        )
        row = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        token = _create_jwt(row[0], row[1])
        resp = make_response(jsonify({"user": _user_response((row[0], row[1], row[2], False)), "token": token}))
        resp.set_cookie(
            AUTH_COOKIE_NAME,
            token,
            path="/",
            httponly=True,
            secure=request.is_secure or not app.debug,
            samesite="None" if (request.is_secure or not app.debug) else "Lax",
            max_age=7 * 24 * 3600,
        )
        return resp
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/auth/login', methods=['POST'])
def auth_login():
    try:
        data = request.get_json() or {}
        email = (data.get("email") or "").strip().lower()
        password = data.get("password") or ""
        if not email or not password:
            return jsonify({"error": "Email and password are required"}), 400
        conn = _auth_db()
        cur = conn.cursor()
        cur.execute("SELECT user_id, email, display_name, password_hash, COALESCE(is_admin, false) FROM tbl_user WHERE email = %s;", (email,))
        row = cur.fetchone()
        cur.close()
        conn.close()
        if not row or not bcrypt.checkpw(password.encode("utf-8"), row[3].encode("utf-8")):
            return jsonify({"error": "Invalid email or password"}), 401
        token = _create_jwt(row[0], row[1])
        resp = make_response(jsonify({"user": _user_response((row[0], row[1], row[2], row[4])), "token": token}))
        resp.set_cookie(
            AUTH_COOKIE_NAME,
            token,
            path="/",
            httponly=True,
            secure=request.is_secure or not app.debug,
            samesite="None" if (request.is_secure or not app.debug) else "Lax",
            max_age=7 * 24 * 3600,
        )
        return resp
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/auth/logout', methods=['POST'])
def auth_logout():
    resp = make_response(jsonify({"ok": True}))
    # Clear cookie with same path/secure/samesite as when set, so the browser actually removes it
    resp.set_cookie(
        AUTH_COOKIE_NAME,
        "",
        path="/",
        httponly=True,
        max_age=0,
        secure=request.is_secure or not app.debug,
        samesite="None" if (request.is_secure or not app.debug) else "Lax",
    )
    return resp


@app.route('/api/auth/me', methods=['GET'])
def auth_me():
    try:
        claims = _get_current_user()
        if not claims:
            return jsonify({"user": None}), 200
        conn = _auth_db()
        cur = conn.cursor()
        cur.execute("SELECT user_id, email, display_name, COALESCE(is_admin, false) FROM tbl_user WHERE user_id = %s;", (claims["user_id"],))
        row = cur.fetchone()
        cur.close()
        conn.close()
        if not row:
            return jsonify({"user": None}), 200
        return jsonify({"user": _user_response(row)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/auth/me', methods=['PATCH'])
def auth_me_update():
    try:
        claims = _get_current_user()
        if not claims:
            return jsonify({"error": "Not authenticated"}), 401
        data = request.get_json() or {}
        conn = _auth_db()
        cur = conn.cursor()
        if "new_password" in data and data["new_password"]:
            new_password = data["new_password"]
            current_password = data.get("current_password") or ""
            if len(new_password) < 8:
                cur.close()
                conn.close()
                return jsonify({"error": "New password must be at least 8 characters"}), 400
            cur.execute("SELECT password_hash FROM tbl_user WHERE user_id = %s;", (claims["user_id"],))
            row_pw = cur.fetchone()
            if not row_pw or not bcrypt.checkpw(current_password.encode("utf-8"), row_pw[0].encode("utf-8")):
                cur.close()
                conn.close()
                return jsonify({"error": "Current password is incorrect"}), 401
            password_hash = bcrypt.hashpw(new_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
            cur.execute("UPDATE tbl_user SET password_hash = %s, updated_at = CURRENT_TIMESTAMP WHERE user_id = %s;", (password_hash, claims["user_id"]))
        if "email" in data:
            email = (data.get("email") or "").strip().lower()
            if not email:
                cur.close()
                conn.close()
                return jsonify({"error": "Email cannot be empty"}), 400
            cur.execute("SELECT user_id FROM tbl_user WHERE email = %s AND user_id != %s;", (email, claims["user_id"]))
            if cur.fetchone():
                cur.close()
                conn.close()
                return jsonify({"error": "That email is already in use"}), 409
            cur.execute("UPDATE tbl_user SET email = %s, updated_at = CURRENT_TIMESTAMP WHERE user_id = %s;", (email, claims["user_id"]))
        if "display_name" in data:
            display_name = (data.get("display_name") or "").strip() or None
            cur.execute("UPDATE tbl_user SET display_name = %s, updated_at = CURRENT_TIMESTAMP WHERE user_id = %s;", (display_name, claims["user_id"]))
        cur.execute("SELECT user_id, email, display_name, COALESCE(is_admin, false) FROM tbl_user WHERE user_id = %s;", (claims["user_id"],))
        row = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"user": _user_response(row)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/admin/users', methods=['GET'])
def admin_list_users():
    """List all users (admin only). Returns id, email, display_name, is_admin."""
    claims, err = _require_admin()
    if err:
        return err[0], err[1]
    try:
        conn = _auth_db()
        cur = conn.cursor()
        cur.execute(
            "SELECT user_id, email, display_name, COALESCE(is_admin, false) FROM tbl_user ORDER BY email;"
        )
        rows = cur.fetchall()
        cur.close()
        conn.close()
        users = [_user_response(r) for r in rows]
        return jsonify({"users": users})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/admin/users/<int:target_user_id>', methods=['PATCH'])
def admin_update_user(target_user_id):
    """Update a user's is_admin flag (admin only). Cannot revoke own admin when sole admin."""
    claims, err = _require_admin()
    if err:
        return err[0], err[1]
    data = request.get_json() or {}
    is_admin = data.get("is_admin")
    if is_admin is None:
        return jsonify({"error": "is_admin is required"}), 400
    is_admin = bool(is_admin)

    try:
        conn = _auth_db()
        cur = conn.cursor()

        # If revoking own admin, ensure at least one other admin remains
        if not is_admin and target_user_id == claims["user_id"]:
            cur.execute("SELECT COUNT(*) FROM tbl_user WHERE is_admin = true;")
            admin_count = cur.fetchone()[0]
            if admin_count <= 1:
                cur.close()
                conn.close()
                return jsonify({"error": "Cannot revoke your own admin rights when you are the only admin."}), 400

        cur.execute(
            "UPDATE tbl_user SET is_admin = %s, updated_at = CURRENT_TIMESTAMP WHERE user_id = %s RETURNING user_id, email, display_name, is_admin;",
            (is_admin, target_user_id),
        )
        row = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        if not row:
            return jsonify({"error": "User not found"}), 404
        return jsonify({"user": _user_response(row)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:3000")
RESET_EXPIRY_HOURS = 1


def _send_password_reset_email(to_email: str, reset_link: str) -> bool:
    """Send password reset email. Returns True if sent (or skipped in dev). Logs link if no email config."""
    sendgrid_key = os.environ.get("SENDGRID_API_KEY")
    if sendgrid_key:
        try:
            import urllib.request
            personalizations = [{"to": [{"email": to_email}]}]
            bcc = (os.environ.get("SENDGRID_BCC") or "").strip()
            if bcc:
                personalizations[0]["bcc"] = [{"email": bcc}]
            req = urllib.request.Request(
                "https://api.sendgrid.com/v3/mail/send",
                data=json.dumps({
                    "personalizations": personalizations,
                    "from": {"email": os.environ.get("RESET_EMAIL_FROM", "noreply@example.com"), "name": "Lingua Formula"},
                    "subject": "Reset your password",
                    "content": [{"type": "text/plain", "value": f"Use this link to set a new password (valid for {RESET_EXPIRY_HOURS} hour):\n\n{reset_link}\n\nIf you didn't request this, you can ignore this email."}]
                }).encode(),
                headers={"Authorization": f"Bearer {sendgrid_key}", "Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                return resp.status in (200, 202)
        except Exception as e:
            app.logger.warning("SendGrid send failed: %s", e)
            return False
    app.logger.info("Password reset link (no SENDGRID_API_KEY): %s", reset_link)
    return True


@app.route('/api/auth/forgot-password', methods=['POST'])
def auth_forgot_password():
    try:
        data = request.get_json() or {}
        email = (data.get("email") or "").strip().lower()
        if not email:
            return jsonify({"error": "Email is required"}), 400
        conn = _auth_db()
        cur = conn.cursor()
        cur.execute("SELECT user_id FROM tbl_user WHERE email = %s;", (email,))
        if not cur.fetchone():
            cur.close()
            conn.close()
            return jsonify({"ok": True, "sent": False, "message": "That email has not been registered."})
        cur.execute("DELETE FROM tbl_password_reset WHERE email = %s;", (email,))
        token = secrets.token_urlsafe(32)
        token_lookup = hashlib.sha256(token.encode()).hexdigest()
        token_hash = bcrypt.hashpw(token.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        expires_at = datetime.utcnow() + timedelta(hours=RESET_EXPIRY_HOURS)
        cur.execute(
            "INSERT INTO tbl_password_reset (email, token_lookup, token_hash, expires_at) VALUES (%s, %s, %s, %s);",
            (email, token_lookup, token_hash, expires_at),
        )
        conn.commit()
        cur.close()
        conn.close()
        reset_link = f"{FRONTEND_URL.rstrip('/')}/reset-password?token={token}"
        _send_password_reset_email(email, reset_link)
        return jsonify({"ok": True, "sent": True, "message": "An email has been sent."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/auth/reset-password', methods=['POST'])
def auth_reset_password():
    try:
        data = request.get_json() or {}
        token = (data.get("token") or "").strip()
        new_password = data.get("new_password") or ""
        if not token:
            return jsonify({"error": "Reset token is required"}), 400
        if len(new_password) < 8:
            return jsonify({"error": "New password must be at least 8 characters"}), 400
        token_lookup = hashlib.sha256(token.encode()).hexdigest()
        conn = _auth_db()
        cur = conn.cursor()
        cur.execute(
            "SELECT id, email, token_hash, expires_at FROM tbl_password_reset WHERE token_lookup = %s AND expires_at > %s;",
            (token_lookup, datetime.utcnow()),
        )
        row = cur.fetchone()
        if not row:
            cur.close()
            conn.close()
            return jsonify({"error": "Invalid or expired reset link. Request a new one."}), 400
        _id, email, stored_hash, _exp = row
        if not bcrypt.checkpw(token.encode("utf-8"), stored_hash.encode("utf-8")):
            cur.close()
            conn.close()
            return jsonify({"error": "Invalid or expired reset link. Request a new one."}), 400
        password_hash = bcrypt.hashpw(new_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        cur.execute("UPDATE tbl_user SET password_hash = %s, updated_at = CURRENT_TIMESTAMP WHERE email = %s;", (password_hash, email))
        cur.execute("DELETE FROM tbl_password_reset WHERE id = %s;", (_id,))
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"ok": True, "message": "Password has been reset. You can sign in with your new password."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ---------- Institutions (auth required) ----------
@app.route('/api/institutions', methods=['GET'])
def api_institutions_list():
    """List all institutions (for dropdown / select). Auth required."""
    try:
        claims = _get_current_user()
        if not claims:
            return jsonify({"error": "Not authenticated"}), 401
        conn = _auth_db()
        cur = conn.cursor()
        cur.execute(
            "SELECT institution_id, institution_name, institution_handle, country, region FROM tbl_institution ORDER BY institution_name;"
        )
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return jsonify({
            "institutions": [
                {
                    "id": r[0],
                    "institution_name": r[1],
                    "institution_handle": r[2],
                    "country": r[3],
                    "region": r[4],
                }
                for r in rows
            ]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/institutions', methods=['POST'])
def api_institutions_create():
    """Create an institution. Auth required."""
    try:
        claims = _get_current_user()
        if not claims:
            return jsonify({"error": "Not authenticated"}), 401
        data = request.get_json() or {}
        name = (data.get("institution_name") or "").strip()
        if not name:
            return jsonify({"error": "institution_name is required"}), 400
        handle = (data.get("institution_handle") or "").strip() or None
        country = (data.get("country") or "").strip() or None
        region = (data.get("region") or "").strip() or None
        conn = _auth_db()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO tbl_institution (institution_name, institution_handle, country, region) VALUES (%s, %s, %s, %s) RETURNING institution_id, institution_name, institution_handle, country, region;",
            (name, handle, country, region),
        )
        row = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({
            "institution": {
                "id": row[0],
                "institution_name": row[1],
                "institution_handle": row[2],
                "country": row[3],
                "region": row[4],
            }
        }), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ---------- Courses (auth required) ----------
@app.route('/api/courses', methods=['GET'])
def api_courses_list():
    """List courses the current user is enrolled in (with institution name). Auth required."""
    try:
        claims = _get_current_user()
        if not claims:
            return jsonify({"error": "Not authenticated"}), 401
        user_id = claims["user_id"]
        conn = _auth_db()
        cur = conn.cursor()
        cur.execute("""
            SELECT c.course_id, c.course_name, c.course_code, c.institution_id, c.course_type,
                   i.institution_name
            FROM tbl_user_course uc
            JOIN tbl_course c ON c.course_id = uc.course_id
            LEFT JOIN tbl_institution i ON i.institution_id = c.institution_id
            WHERE uc.user_id = %s
            ORDER BY c.course_name;
        """, (user_id,))
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return jsonify({
            "courses": [
                {
                    "course_id": r[0],
                    "course_name": r[1],
                    "course_code": r[2],
                    "institution_id": r[3],
                    "course_type": r[4],
                    "institution_name": r[5],
                }
                for r in rows
            ]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/courses', methods=['POST'])
def api_courses_create():
    """Create a course and enroll the current user. Auth required."""
    try:
        claims = _get_current_user()
        if not claims:
            return jsonify({"error": "Not authenticated"}), 401
        user_id = claims["user_id"]
        data = request.get_json() or {}
        course_name = (data.get("course_name") or "").strip()
        if not course_name:
            return jsonify({"error": "course_name is required"}), 400
        course_code = (data.get("course_code") or "").strip() or None
        institution_id = data.get("institution_id")  # can be null for personal
        if institution_id is not None:
            institution_id = int(institution_id)
        course_type = (data.get("course_type") or "").strip() or None
        if not course_type and institution_id is None:
            course_type = "personal"
        elif not course_type:
            course_type = "academic"
        conn = _auth_db()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO tbl_course (course_name, course_code, institution_id, course_type) VALUES (%s, %s, %s, %s) RETURNING course_id, course_name, course_code, institution_id, course_type;",
            (course_name, course_code, institution_id, course_type),
        )
        row = cur.fetchone()
        course_id = row[0]
        cur.execute("INSERT INTO tbl_user_course (user_id, course_id) VALUES (%s, %s) ON CONFLICT (user_id, course_id) DO NOTHING;", (user_id, course_id))
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({
            "course": {
                "course_id": course_id,
                "course_name": row[1],
                "course_code": row[2],
                "institution_id": row[3],
                "course_type": row[4],
            }
        }), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/courses/<int:course_id>', methods=['PATCH'])
def api_course_update(course_id):
    """Update a course the current user is enrolled in. Auth required."""
    try:
        claims = _get_current_user()
        if not claims:
            return jsonify({"error": "Not authenticated"}), 401
        user_id = claims["user_id"]
        conn = _auth_db()
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM tbl_user_course WHERE user_id = %s AND course_id = %s;", (user_id, course_id))
        if cur.fetchone() is None:
            cur.close()
            conn.close()
            return jsonify({"error": "Course not found or you are not enrolled"}), 404
        data = request.get_json() or {}
        course_name = (data.get("course_name") or "").strip()
        course_code = (data.get("course_code") or "").strip() or None
        institution_id = data.get("institution_id")
        if institution_id is not None:
            institution_id = int(institution_id)
        if not course_name:
            cur.close()
            conn.close()
            return jsonify({"error": "course_name is required"}), 400
        cur.execute(
            """UPDATE tbl_course SET course_name = %s, course_code = %s, institution_id = %s, updated_at = CURRENT_TIMESTAMP
               WHERE course_id = %s RETURNING course_id, course_name, course_code, institution_id, course_type;""",
            (course_name, course_code, institution_id, course_id),
        )
        row = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        if not row:
            return jsonify({"error": "Course not found"}), 404
        return jsonify({
            "course": {
                "course_id": row[0],
                "course_name": row[1],
                "course_code": row[2],
                "institution_id": row[3],
                "course_type": row[4],
            }
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/courses/<int:course_id>', methods=['DELETE'])
def api_course_delete(course_id):
    """Remove current user's enrollment and their course-formula links. If no other enrollments, delete the course. Auth required."""
    try:
        claims = _get_current_user()
        if not claims:
            return jsonify({"error": "Not authenticated"}), 401
        user_id = claims["user_id"]
        conn = _auth_db()
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM tbl_user_course WHERE user_id = %s AND course_id = %s;", (user_id, course_id))
        if cur.fetchone() is None:
            cur.close()
            conn.close()
            return jsonify({"error": "Course not found or you are not enrolled"}), 404
        cur.execute("DELETE FROM tbl_user_course_formula WHERE user_id = %s AND course_id = %s;", (user_id, course_id))
        cur.execute("DELETE FROM tbl_user_course_term WHERE user_id = %s AND course_id = %s;", (user_id, course_id))
        cur.execute("DELETE FROM tbl_user_course WHERE user_id = %s AND course_id = %s;", (user_id, course_id))
        cur.execute("SELECT 1 FROM tbl_user_course WHERE course_id = %s;", (course_id,))
        if cur.fetchone() is None:
            cur.execute("DELETE FROM tbl_course WHERE course_id = %s;", (course_id,))
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"message": "Course removed"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/courses/formulas', methods=['GET'])
def api_all_course_formulas_list():
    """List all course-formula links for the current user (all courses). Auth required."""
    try:
        claims = _get_current_user()
        if not claims:
            return jsonify({"error": "Not authenticated"}), 401
        user_id = claims["user_id"]
        conn = _auth_db()
        cur = conn.cursor()
        cur.execute("""
            SELECT c.course_id, c.course_name, c.course_code, ucf.formula_id, f.formula_name, f.latex,
                   ucf.segment_type, ucf.segment_label
            FROM tbl_user_course_formula ucf
            JOIN tbl_course c ON c.course_id = ucf.course_id
            JOIN tbl_formula f ON f.formula_id = ucf.formula_id
            WHERE ucf.user_id = %s
            ORDER BY c.course_name, ucf.segment_type NULLS LAST, ucf.segment_label NULLS LAST, f.formula_name;
        """, (user_id,))
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return jsonify({
            "items": [
                {
                    "course_id": r[0],
                    "course_name": r[1],
                    "course_code": r[2],
                    "formula_id": r[3],
                    "formula_name": r[4],
                    "latex": r[5],
                    "segment_type": r[6],
                    "segment_label": r[7],
                }
                for r in rows
            ]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/courses/<int:course_id>/questions', methods=['GET'])
def api_course_questions(course_id):
    """Get all quiz questions for formulas linked to this course for the current user. Auth required; user must be enrolled.
    Query params: segment_type (chapter|module|examination), segment_label (optional filter)."""
    try:
        claims = _get_current_user()
        if not claims:
            return jsonify({"error": "Not authenticated"}), 401
        user_id = claims["user_id"]
        segment_type = request.args.get("segment_type", "").strip() or None
        if segment_type and segment_type not in ("chapter", "module", "examination"):
            segment_type = None
        segment_label = request.args.get("segment_label", "").strip() or None
        conn = _auth_db()
        cur = conn.cursor()
        cur.execute("""
            SELECT c.course_name, c.course_code FROM tbl_user_course uc
            JOIN tbl_course c ON c.course_id = uc.course_id
            WHERE uc.user_id = %s AND uc.course_id = %s;
        """, (user_id, course_id))
        row = cur.fetchone()
        if row is None:
            cur.close()
            conn.close()
            return jsonify({"error": "Course not found or you are not enrolled"}), 404
        course_name, course_code = row
        cur.execute("""
            SELECT ucf.formula_id FROM tbl_user_course_formula ucf
            WHERE ucf.user_id = %s AND ucf.course_id = %s
            AND (%s::text IS NULL OR ucf.segment_type = %s)
            AND (%s::text IS NULL OR TRIM(ucf.segment_label) = TRIM(%s));
        """, (user_id, course_id, segment_type, segment_type, segment_label, segment_label))
        formula_ids = [r[0] for r in cur.fetchall()]
        cur.close()
        conn.close()
        all_questions = []
        for fid in formula_ids:
            qs = get_questions_by_formula_id(fid)
            for q in qs:
                q["formula_id"] = fid
                all_questions.append(q)
        return jsonify({
            "course_name": course_name,
            "course_code": course_code,
            "questions": all_questions,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/courses/<int:course_id>/formulas', methods=['GET'])
def api_course_formulas_list(course_id):
    """List formulas linked to this course for the current user. Auth required; user must be enrolled."""
    try:
        claims = _get_current_user()
        if not claims:
            return jsonify({"error": "Not authenticated"}), 401
        user_id = claims["user_id"]
        conn = _auth_db()
        cur = conn.cursor()
        cur.execute("""
            SELECT uc.user_id FROM tbl_user_course uc WHERE uc.user_id = %s AND uc.course_id = %s;
        """, (user_id, course_id))
        if cur.fetchone() is None:
            cur.close()
            conn.close()
            return jsonify({"error": "Course not found or you are not enrolled"}), 404
        cur.execute("""
            SELECT f.formula_id, f.formula_name, f.latex, ucf.display_order, ucf.segment_type, ucf.segment_label
            FROM tbl_user_course_formula ucf
            JOIN tbl_formula f ON f.formula_id = ucf.formula_id
            WHERE ucf.user_id = %s AND ucf.course_id = %s
            ORDER BY ucf.display_order NULLS LAST, f.formula_name;
        """, (user_id, course_id))
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return jsonify({
            "formulas": [
                {"id": r[0], "formula_name": r[1], "latex": r[2], "display_order": r[3], "segment_type": r[4], "segment_label": r[5]}
                for r in rows
            ]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/courses/<int:course_id>/formulas/<int:formula_id>', methods=['POST'])
def api_course_formula_add(course_id, formula_id):
    """Add a formula to a course for the current user. Auth required; user must be enrolled."""
    try:
        claims = _get_current_user()
        if not claims:
            return jsonify({"error": "Not authenticated"}), 401
        user_id = claims["user_id"]
        conn = _auth_db()
        cur = conn.cursor()
        cur.execute("""
            SELECT 1 FROM tbl_user_course WHERE user_id = %s AND course_id = %s;
        """, (user_id, course_id))
        if cur.fetchone() is None:
            cur.close()
            conn.close()
            return jsonify({"error": "Course not found or you are not enrolled"}), 404
        cur.execute("""
            SELECT 1 FROM tbl_formula WHERE formula_id = %s;
        """, (formula_id,))
        if cur.fetchone() is None:
            cur.close()
            conn.close()
            return jsonify({"error": "Formula not found"}), 404
        data = request.get_json() or {}
        segment_type = (data.get("segment_type") or "").strip() or None
        if segment_type and segment_type not in ("chapter", "module", "examination"):
            segment_type = None
        segment_label = (data.get("segment_label") or "").strip() or None
        cur.execute("""
            INSERT INTO tbl_user_course_formula (user_id, course_id, formula_id, segment_type, segment_label)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (user_id, course_id, formula_id) DO UPDATE SET
                segment_type = EXCLUDED.segment_type,
                segment_label = EXCLUDED.segment_label;
        """, (user_id, course_id, formula_id, segment_type, segment_label))
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"message": "Formula added to course"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/courses/<int:course_id>/formulas/<int:formula_id>', methods=['PATCH'])
def api_course_formula_update(course_id, formula_id):
    """Update segment_type and segment_label for a course-formula link. Auth required; user must be enrolled."""
    try:
        claims = _get_current_user()
        if not claims:
            return jsonify({"error": "Not authenticated"}), 401
        user_id = claims["user_id"]
        conn = _auth_db()
        cur = conn.cursor()
        cur.execute("""
            SELECT 1 FROM tbl_user_course WHERE user_id = %s AND course_id = %s;
        """, (user_id, course_id))
        if cur.fetchone() is None:
            cur.close()
            conn.close()
            return jsonify({"error": "Course not found or you are not enrolled"}), 404
        data = request.get_json() or {}
        segment_type = (data.get("segment_type") or "").strip() or None
        if segment_type and segment_type not in ("chapter", "module", "examination"):
            segment_type = None
        segment_label = (data.get("segment_label") or "").strip() or None
        cur.execute("""
            UPDATE tbl_user_course_formula
            SET segment_type = %s, segment_label = %s
            WHERE user_id = %s AND course_id = %s AND formula_id = %s;
        """, (segment_type, segment_label, user_id, course_id, formula_id))
        conn.commit()
        updated = cur.rowcount
        cur.close()
        conn.close()
        if updated == 0:
            return jsonify({"error": "Formula not linked to this course"}), 404
        return jsonify({"message": "Segment updated"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/courses/<int:course_id>/formulas/<int:formula_id>', methods=['DELETE'])
def api_course_formula_remove(course_id, formula_id):
    """Remove a formula from a course for the current user. Auth required; user must be enrolled."""
    try:
        claims = _get_current_user()
        if not claims:
            return jsonify({"error": "Not authenticated"}), 401
        user_id = claims["user_id"]
        conn = _auth_db()
        cur = conn.cursor()
        cur.execute("""
            SELECT 1 FROM tbl_user_course WHERE user_id = %s AND course_id = %s;
        """, (user_id, course_id))
        if cur.fetchone() is None:
            cur.close()
            conn.close()
            return jsonify({"error": "Course not found or you are not enrolled"}), 404
        cur.execute("""
            DELETE FROM tbl_user_course_formula
            WHERE user_id = %s AND course_id = %s AND formula_id = %s;
        """, (user_id, course_id, formula_id))
        conn.commit()
        deleted = cur.rowcount
        cur.close()
        conn.close()
        if deleted == 0:
            return jsonify({"error": "Formula not linked to this course"}), 404
        return jsonify({"message": "Formula removed from course"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/courses/terms', methods=['GET'])
def api_all_course_terms_list():
    """List all course-term links for the current user (all courses). Auth required."""
    try:
        claims = _get_current_user()
        if not claims:
            return jsonify({"error": "Not authenticated"}), 401
        user_id = claims["user_id"]
        conn = _auth_db()
        cur = conn.cursor()
        cur.execute("""
            SELECT c.course_id, c.course_name, c.course_code, uct.term_id, t.term_name, t.definition,
                   uct.segment_type, uct.segment_label
            FROM tbl_user_course_term uct
            JOIN tbl_course c ON c.course_id = uct.course_id
            JOIN tbl_term t ON t.term_id = uct.term_id
            WHERE uct.user_id = %s
            ORDER BY c.course_name, uct.segment_type NULLS LAST, uct.segment_label NULLS LAST, t.term_name;
        """, (user_id,))
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return jsonify({
            "items": [
                {
                    "course_id": r[0],
                    "course_name": r[1],
                    "course_code": r[2],
                    "term_id": r[3],
                    "term_name": r[4],
                    "definition": r[5],
                    "segment_type": r[6],
                    "segment_label": r[7],
                }
                for r in rows
            ]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/courses/<int:course_id>/terms', methods=['GET'])
def api_course_terms_list(course_id):
    """List terms linked to this course for the current user. Auth required; user must be enrolled."""
    try:
        claims = _get_current_user()
        if not claims:
            return jsonify({"error": "Not authenticated"}), 401
        user_id = claims["user_id"]
        conn = _auth_db()
        cur = conn.cursor()
        cur.execute("""
            SELECT uc.user_id FROM tbl_user_course uc WHERE uc.user_id = %s AND uc.course_id = %s;
        """, (user_id, course_id))
        if cur.fetchone() is None:
            cur.close()
            conn.close()
            return jsonify({"error": "Course not found or you are not enrolled"}), 404
        cur.execute("""
            SELECT t.term_id, t.term_name, t.definition, uct.display_order, uct.segment_type, uct.segment_label
            FROM tbl_user_course_term uct
            JOIN tbl_term t ON t.term_id = uct.term_id
            WHERE uct.user_id = %s AND uct.course_id = %s
            ORDER BY uct.display_order NULLS LAST, t.term_name;
        """, (user_id, course_id))
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return jsonify({
            "terms": [
                {"term_id": r[0], "term_name": r[1], "definition": r[2], "display_order": r[3], "segment_type": r[4], "segment_label": r[5]}
                for r in rows
            ]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/courses/<int:course_id>/terms/<int:term_id>', methods=['POST'])
def api_course_term_add(course_id, term_id):
    """Add a term to a course for the current user. Auth required; user must be enrolled."""
    try:
        claims = _get_current_user()
        if not claims:
            return jsonify({"error": "Not authenticated"}), 401
        user_id = claims["user_id"]
        conn = _auth_db()
        cur = conn.cursor()
        cur.execute("""
            SELECT 1 FROM tbl_user_course WHERE user_id = %s AND course_id = %s;
        """, (user_id, course_id))
        if cur.fetchone() is None:
            cur.close()
            conn.close()
            return jsonify({"error": "Course not found or you are not enrolled"}), 404
        cur.execute("""
            SELECT 1 FROM tbl_term WHERE term_id = %s;
        """, (term_id,))
        if cur.fetchone() is None:
            cur.close()
            conn.close()
            return jsonify({"error": "Term not found"}), 404
        data = request.get_json() or {}
        segment_type = (data.get("segment_type") or "").strip() or None
        if segment_type and segment_type not in ("chapter", "module", "examination"):
            segment_type = None
        segment_label = (data.get("segment_label") or "").strip() or None
        cur.execute("""
            INSERT INTO tbl_user_course_term (user_id, course_id, term_id, segment_type, segment_label)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (user_id, course_id, term_id) DO UPDATE SET
                segment_type = EXCLUDED.segment_type,
                segment_label = EXCLUDED.segment_label;
        """, (user_id, course_id, term_id, segment_type, segment_label))
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"message": "Term added to course"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/courses/<int:course_id>/terms/<int:term_id>', methods=['PATCH'])
def api_course_term_update(course_id, term_id):
    """Update segment_type and segment_label for a course-term link. Auth required; user must be enrolled."""
    try:
        claims = _get_current_user()
        if not claims:
            return jsonify({"error": "Not authenticated"}), 401
        user_id = claims["user_id"]
        conn = _auth_db()
        cur = conn.cursor()
        cur.execute("""
            SELECT 1 FROM tbl_user_course WHERE user_id = %s AND course_id = %s;
        """, (user_id, course_id))
        if cur.fetchone() is None:
            cur.close()
            conn.close()
            return jsonify({"error": "Course not found or you are not enrolled"}), 404
        data = request.get_json() or {}
        segment_type = (data.get("segment_type") or "").strip() or None
        if segment_type and segment_type not in ("chapter", "module", "examination"):
            segment_type = None
        segment_label = (data.get("segment_label") or "").strip() or None
        cur.execute("""
            UPDATE tbl_user_course_term
            SET segment_type = %s, segment_label = %s
            WHERE user_id = %s AND course_id = %s AND term_id = %s;
        """, (segment_type, segment_label, user_id, course_id, term_id))
        conn.commit()
        updated = cur.rowcount
        cur.close()
        conn.close()
        if updated == 0:
            return jsonify({"error": "Term not linked to this course"}), 404
        return jsonify({"message": "Segment updated"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/courses/<int:course_id>/terms/<int:term_id>', methods=['DELETE'])
def api_course_term_remove(course_id, term_id):
    """Remove a term from a course for the current user. Auth required; user must be enrolled."""
    try:
        claims = _get_current_user()
        if not claims:
            return jsonify({"error": "Not authenticated"}), 401
        user_id = claims["user_id"]
        conn = _auth_db()
        cur = conn.cursor()
        cur.execute("""
            SELECT 1 FROM tbl_user_course WHERE user_id = %s AND course_id = %s;
        """, (user_id, course_id))
        if cur.fetchone() is None:
            cur.close()
            conn.close()
            return jsonify({"error": "Course not found or you are not enrolled"}), 404
        cur.execute("""
            DELETE FROM tbl_user_course_term
            WHERE user_id = %s AND course_id = %s AND term_id = %s;
        """, (user_id, course_id, term_id))
        conn.commit()
        deleted = cur.rowcount
        cur.close()
        conn.close()
        if deleted == 0:
            return jsonify({"error": "Term not linked to this course"}), 404
        return jsonify({"message": "Term removed from course"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/courses/<int:course_id>/term-questions', methods=['GET'])
def api_course_term_questions(course_id):
    """Get all quiz questions for terms linked to this course for the current user. Auth required; user must be enrolled.
    Query params: segment_type (chapter|module|examination), segment_label (optional filter)."""
    try:
        claims = _get_current_user()
        if not claims:
            return jsonify({"error": "Not authenticated"}), 401
        user_id = claims["user_id"]
        segment_type = request.args.get("segment_type", "").strip() or None
        if segment_type and segment_type not in ("chapter", "module", "examination"):
            segment_type = None
        segment_label = request.args.get("segment_label", "").strip() or None
        conn = _auth_db()
        cur = conn.cursor()
        cur.execute("""
            SELECT c.course_name, c.course_code FROM tbl_user_course uc
            JOIN tbl_course c ON c.course_id = uc.course_id
            WHERE uc.user_id = %s AND uc.course_id = %s;
        """, (user_id, course_id))
        row = cur.fetchone()
        if row is None:
            cur.close()
            conn.close()
            return jsonify({"error": "Course not found or you are not enrolled"}), 404
        course_name, course_code = row
        cur.execute("""
            SELECT uct.term_id FROM tbl_user_course_term uct
            WHERE uct.user_id = %s AND uct.course_id = %s
            AND (%s::text IS NULL OR uct.segment_type = %s)
            AND (%s::text IS NULL OR TRIM(uct.segment_label) = TRIM(%s));
        """, (user_id, course_id, segment_type, segment_type, segment_label, segment_label))
        term_ids = [r[0] for r in cur.fetchall()]
        cur.close()
        conn.close()
        all_questions = []
        for tid in term_ids:
            qs = get_questions_by_term_id(tid)
            for q in qs:
                q["term_id"] = tid
                all_questions.append(q)
        return jsonify({
            "course_name": course_name,
            "course_code": course_code,
            "questions": all_questions,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/admin/update-multipart-mean', methods=['GET'])
def admin_update_multipart_mean():
    """One-off: run the multipart mean question update and return result (no heroku run timeout)."""
    try:
        success, message = run_multipart_mean_update()
        return jsonify({"ok": success, "message": message})
    except Exception as e:
        return jsonify({"ok": False, "message": str(e)}), 500


@app.route('/api/admin/seed-all-formula-questions', methods=['GET'])
def admin_seed_all_formula_questions():
    """Run seed_all_formula_questions (add one question per formula for formulas that don't have one). Returns count and message."""
    try:
        count_added, message = run_seed_all_formula_questions()
        return jsonify({"ok": True, "added": count_added, "message": message})
    except Exception as e:
        return jsonify({"ok": False, "added": 0, "message": str(e)}), 500


# Route to fetch all applications
@app.route('/api/applications', methods=['GET'])
def fetch_applications():
    try:
        applications = get_applications()
        return jsonify(applications)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Route to fetch a single application by ID
@app.route('/api/applications/<int:application_id>', methods=['GET'])
def fetch_application_by_id(application_id):
    try:
        application = get_application_by_id(application_id)
        if application:
            return jsonify(application)
        else:
            return jsonify({"error": "Application not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Route to fetch formulas linked to an application
@app.route('/api/applications/<int:application_id>/formulas', methods=['GET'])
def fetch_application_formulas(application_id):
    try:
        formulas = get_application_formulas(application_id)
        return jsonify(formulas)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Route to create a new application
@app.route('/api/applications', methods=['POST'])
def create_new_application():
    try:
        data = request.get_json()
        if not data or 'title' not in data or 'problem_text' not in data:
            return jsonify({"error": "Title and problem_text are required"}), 400
        
        application_id = create_application(
            data['title'],
            data['problem_text'],
            data.get('subject_area')
        )
        
        return jsonify({"id": application_id, "message": "Application created successfully"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Route to link an application to a formula
@app.route('/api/applications/<int:application_id>/formulas/<int:formula_id>', methods=['POST'])
def link_application_to_formula(application_id, formula_id):
    try:
        data = request.get_json() or {}
        relevance_score = data.get('relevance_score')
        
        link_application_formula(application_id, formula_id, relevance_score)
        
        return jsonify({"message": "Application linked to formula successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Route to get AI suggestions for formula mapping
@app.route('/api/applications/<int:application_id>/suggest-formulas', methods=['POST'])
def suggest_formulas_for_application(application_id):
    try:
        if not OPENAI_API_KEY:
            return jsonify({"error": "OpenAI API key not configured"}), 500
        
        application = get_application_by_id(application_id)
        if not application:
            return jsonify({"error": "Application not found"}), 404
        
        formulas = get_formulas()
        
        # Create prompt for OpenAI
        formula_list = "\n".join([f"ID {f['id']}: {f['formula_name']} - {f['latex']}" for f in formulas])
        
        prompt = f"""
        Given this problem/application:
        Title: {application['title']}
        Problem: {application['problem_text']}
        Subject: {application.get('subject_area', 'Unknown')}
        
        And these available formulas:
        {formula_list}
        
        Please suggest which formulas would be most relevant for solving this problem. 
        Return a JSON array with objects containing 'formula_id' and 'relevance_score' (0-1).
        Only include formulas that are actually relevant.
        """
        
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )
        
        # Parse the AI response
        ai_suggestions = response.choices[0].message.content
        
        return jsonify({"suggestions": ai_suggestions})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Route to upload and process image for application creation
@app.route('/api/applications/upload-image', methods=['POST'])
def upload_and_process_image():
    try:
        if 'image' not in request.files:
            return jsonify({"error": "No image file provided"}), 400
        
        file = request.files['image']
        if file.filename == '':
            return jsonify({"error": "No image file selected"}), 400
        
        # Read image data
        image_data = file.read()
        
        # Extract text using both OCR and OpenAI Vision
        ocr_text = extract_text_from_image(image_data)
        ai_text = extract_text_with_openai(image_data)
        
        # Combine results, preferring AI text if available
        extracted_text = ai_text if ai_text else ocr_text
        
        return jsonify({
            "image_filename": file.filename,
            "extracted_text": extracted_text,
            "ocr_text": ocr_text,
            "ai_text": ai_text,
            "message": "Image processed successfully"
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Route to create application with image
@app.route('/api/applications/with-image', methods=['POST'])
def create_application_with_image():
    try:
        if 'image' not in request.files:
            return jsonify({"error": "No image file provided"}), 400
        
        file = request.files['image']
        title = request.form.get('title')
        problem_text = request.form.get('problem_text', '')
        subject_area = request.form.get('subject_area')
        
        if not title:
            return jsonify({"error": "Title is required"}), 400
        
        # Read and process image
        image_data = file.read()
        
        # Extract text using both methods
        ocr_text = extract_text_from_image(image_data)
        ai_text = extract_text_with_openai(image_data)
        
        # Use AI text if available, otherwise OCR
        extracted_text = ai_text if ai_text else ocr_text
        
        # If problem_text is empty, use extracted text
        if not problem_text and extracted_text:
            problem_text = extracted_text
        
        # Create application with image data
        application_id = create_application(
            title=title,
            problem_text=problem_text,
            subject_area=subject_area,
            image_filename=file.filename,
            image_data=image_data,
            image_text=extracted_text
        )
        
        return jsonify({
            "id": application_id,
            "message": "Application created successfully with image",
            "extracted_text": extracted_text
        }), 201
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Route to get image for an application
@app.route('/api/applications/<int:application_id>/image', methods=['GET'])
def get_application_image(application_id):
    try:
        sslmode = "require" if DATABASE_URL.startswith("postgres://") else "disable"
        conn = psycopg2.connect(DATABASE_URL, sslmode=sslmode)
        cursor = conn.cursor()
        cursor.execute("SELECT image_data, image_filename FROM application WHERE id = %s;", (application_id,))
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not result or not result[0]:
            return jsonify({"error": "No image found for this application"}), 404
        
        image_data, filename = result
        
        # Return image as base64 encoded string
        image_base64 = base64.b64encode(image_data).decode('utf-8')
        
        return jsonify({
            "image_data": image_base64,
            "filename": filename
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)
