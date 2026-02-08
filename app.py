# app.py
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
CORS(app, origins=_default_origins + _extra_origins, supports_credentials=True)

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
    token = request.cookies.get(AUTH_COOKIE_NAME)
    return _verify_jwt(token)

def _user_response(user_row):
    return {"id": user_row[0], "email": user_row[1], "display_name": user_row[2]}

def get_formulas():
    # Use sslmode=require for production (Heroku uses postgres://), disable for local development
    # Heroku DATABASE_URL starts with postgres://, local uses postgresql://
    sslmode = "require" if DATABASE_URL.startswith("postgres://") else "disable"
    conn = psycopg2.connect(DATABASE_URL, sslmode=sslmode)
    cursor = conn.cursor()
    cursor.execute("SELECT formula_id, formula_name, latex, display_order, formula_description, english_verbalization, symbolic_verbalization FROM tbl_formula ORDER BY display_order;")
    formulas = cursor.fetchall()
    result = [{"id": row[0], "formula_name": row[1], "latex": row[2], "display_order": row[3], 
               "formula_description": row[4], "english_verbalization": row[5], "symbolic_verbalization": row[6]} for row in formulas]
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
            SELECT DISTINCT f.formula_id, f.formula_name, f.latex, f.display_order, 
                   f.formula_description, f.english_verbalization, f.symbolic_verbalization
            FROM tbl_formula f
            INNER JOIN tbl_formula_discipline fd ON f.formula_id = fd.formula_id
            INNER JOIN discipline_tree dt ON fd.discipline_id = dt.discipline_id
            ORDER BY f.display_order;
        """, (discipline_ids,))
    else:
        # Only get formulas directly linked to the selected disciplines
        cursor.execute("""
            SELECT DISTINCT f.formula_id, f.formula_name, f.latex, f.display_order,
                   f.formula_description, f.english_verbalization, f.symbolic_verbalization
            FROM tbl_formula f
            INNER JOIN tbl_formula_discipline fd ON f.formula_id = fd.formula_id
            WHERE fd.discipline_id = ANY(%s)
            ORDER BY f.display_order;
        """, (discipline_ids,))
    
    formulas = cursor.fetchall()
    result = [{"id": row[0], "formula_name": row[1], "latex": row[2], "display_order": row[3], 
               "formula_description": row[4], "english_verbalization": row[5], "symbolic_verbalization": row[6]} for row in formulas]
    cursor.close()
    conn.close()
    return result

# Function to fetch a single formula by ID
def get_formula_by_id(formula_id):
    # Use sslmode=require for production (Heroku uses postgres://), disable for local development
    sslmode = "require" if DATABASE_URL.startswith("postgres://") else "disable"
    conn = psycopg2.connect(DATABASE_URL, sslmode=sslmode)
    cursor = conn.cursor()
    cursor.execute("SELECT formula_id, formula_name, latex, display_order, formula_description, english_verbalization, symbolic_verbalization, units, example, historical_context FROM tbl_formula WHERE formula_id = %s;", (formula_id,))
    formula = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if formula:
        return {
            "id": formula[0],
            "formula_name": formula[1],
            "latex": formula[2],
            "display_order": formula[3],
            "formula_description": formula[4],
            "english_verbalization": formula[5],
            "symbolic_verbalization": formula[6],
            "units": formula[7],
            "example": formula[8],
            "historical_context": formula[9]
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
        
        # Fetch all disciplines with parent info and formula counts
        cursor.execute("""
            SELECT 
                d.discipline_id,
                d.discipline_name,
                d.discipline_handle,
                d.discipline_description,
                d.discipline_parent_id,
                COALESCE(p.discipline_name, NULL) as parent_name,
                COALESCE(p.discipline_handle, NULL) as parent_handle,
                (SELECT COUNT(*) FROM tbl_formula_discipline WHERE discipline_id = d.discipline_id) as formula_count
            FROM tbl_discipline d
            LEFT JOIN tbl_discipline p ON d.discipline_parent_id = p.discipline_id
            ORDER BY COALESCE(d.discipline_parent_id, 0), d.discipline_name;
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
                "formula_count": row[7]
            })
        
        cursor.close()
        conn.close()
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

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
        resp = make_response(jsonify({"user": _user_response(row)}))
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
        cur.execute("SELECT user_id, email, display_name, password_hash FROM tbl_user WHERE email = %s;", (email,))
        row = cur.fetchone()
        cur.close()
        conn.close()
        if not row or not bcrypt.checkpw(password.encode("utf-8"), row[3].encode("utf-8")):
            return jsonify({"error": "Invalid email or password"}), 401
        token = _create_jwt(row[0], row[1])
        resp = make_response(jsonify({"user": _user_response(row)}))
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
        cur.execute("SELECT user_id, email, display_name FROM tbl_user WHERE user_id = %s;", (claims["user_id"],))
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
        cur.execute("SELECT user_id, email, display_name FROM tbl_user WHERE user_id = %s;", (claims["user_id"],))
        row = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
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
            req = urllib.request.Request(
                "https://api.sendgrid.com/v3/mail/send",
                data=json.dumps({
                    "personalizations": [{"to": [{"email": to_email}]}],
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
            return jsonify({"ok": True, "message": "If an account exists with that email, we've sent a reset link."})
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
        return jsonify({"ok": True, "message": "If an account exists with that email, we've sent a reset link."})
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
