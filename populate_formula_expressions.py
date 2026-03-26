#!/usr/bin/env python3
"""
Populate formula_expression column with plain text representations of LaTeX formulas.
"""
import os
import sys
import psycopg2
import re

# Get database URL from environment or use defaults
DATABASE_URL = os.environ.get('DATABASE_URL')

if not DATABASE_URL:
    # Default to local database
    DB_NAME = os.environ.get('DB_NAME', 'linguaformula')
    DB_USER = os.environ.get('DB_USER', 'dev_user')
    DB_PASSWORD = os.environ.get('DB_PASSWORD') or os.environ.get('PGPASSWORD')
    DB_HOST = os.environ.get('DB_HOST', 'localhost')
    DB_PORT = os.environ.get('DB_PORT', '5432')
    
    if not DB_PASSWORD:
        try:
            DB_PASSWORD = input(f"Enter password for database user '{DB_USER}': ")
        except (EOFError, KeyboardInterrupt):
            print("❌ Password required. Set DB_PASSWORD or PGPASSWORD environment variable.")
            sys.exit(1)
    
    DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

def latex_to_plain_text(latex):
    """
    Convert LaTeX formula to plain text representation.
    Handles common LaTeX patterns.
    """
    if not latex:
        return None
    
    # Remove LaTeX display delimiters
    text = latex.replace('\\[', '').replace('\\]', '').replace('$$', '').replace('$', '')
    
    # Handle vector commands: \vec{...} -> ... (remove vec, keep content)
    text = re.sub(r'\\vec\{([^}]+)\}', r'\1', text)
    text = text.replace('\\vec', '')
    
    # Handle text commands: \text{...} -> ...
    text = re.sub(r'\\text\{([^}]+)\}', r'\1', text)
    
    # Handle fractions: \frac{a}{b} -> (a/b)
    text = re.sub(r'\\frac\{([^}]+)\}\{([^}]+)\}', r'(\1/\2)', text)
    
    # Handle binomial coefficients: \binom{n}{r} -> C(n,r) or (n choose r)
    text = re.sub(r'\\binom\{([^}]+)\}\{([^}]+)\}', r'C(\1,\2)', text)
    
    # Handle square roots: \sqrt{x} -> sqrt(x)
    text = re.sub(r'\\sqrt\{([^}]+)\}', r'sqrt(\1)', text)
    text = re.sub(r'\\sqrt([^{])', r'sqrt\1', text)
    
    # Handle limits: \lim_{x \to y} -> lim(x->y)
    text = re.sub(r'\\lim_\{([^}]+)\s*\\to\s*([^}]+)\}', r'lim(\1->\2)', text)
    
    # Handle overline: \overline{...} -> ~...
    text = re.sub(r'\\overline\{([^}]+)\}', r'~\1', text)
    
    # Handle set operations and symbols
    replacements = {
        '\\cdot': '*',
        '\\times': '*',
        '\\div': '/',
        '\\pm': '±',
        '\\mp': '∓',
        '\\leq': '<=',
        '\\geq': '>=',
        '\\neq': '!=',
        '\\approx': '≈',
        '\\equiv': '≡',
        '\\propto': '∝',
        '\\cup': '∪',
        '\\cap': '∩',
        '\\emptyset': '∅',
        '\\in': '∈',
        '\\notin': '∉',
        '\\subset': '⊂',
        '\\supset': '⊃',
        '\\subseteq': '⊆',
        '\\supseteq': '⊇',
        '\\mid': '|',
        '\\sum': 'Σ',
        '\\prod': 'Π',
        '\\int': '∫',
        '\\partial': '∂',
        '\\nabla': '∇',
        '\\infty': '∞',
        '\\mathbb{R}': 'R',
        '\\mathbb{R}^+': 'R+',
        '\\mathbb{N}': 'N',
        '\\mathbb{Z}': 'Z',
        '\\mathbb{Q}': 'Q',
        '\\mathbb{C}': 'C',
        '\\mathrm{E}': 'E',
        '\\mathrm{Var}': 'Var',
        '\\alpha': 'α',
        '\\beta': 'β',
        '\\gamma': 'γ',
        '\\delta': 'δ',
        '\\epsilon': 'ε',
        '\\theta': 'θ',
        '\\lambda': 'λ',
        '\\mu': 'μ',
        '\\pi': 'π',
        '\\sigma': 'σ',
        '\\phi': 'φ',
        '\\omega': 'ω',
        '\\Delta': 'Δ',
        '\\Gamma': 'Γ',
        '\\Lambda': 'Λ',
        '\\Pi': 'Π',
        '\\Sigma': 'Σ',
        '\\Theta': 'Θ',
        '\\Phi': 'Φ',
        '\\Omega': 'Ω',
        '\\left(': '(',
        '\\right)': ')',
        '\\left[': '[',
        '\\right]': ']',
        '\\left\\{': '{',
        '\\right\\}': '}',
        '\\left|': '|',
        '\\right|': '|',
        '\\quad': ' ',
        '\\,': ' ',
        '\\;': ' ',
        '\\!': '',
    }
    
    for latex_cmd, replacement in replacements.items():
        text = text.replace(latex_cmd, replacement)
    
    # Handle subscripts: _{x} -> _x (but preserve braces for complex expressions)
    # First handle simple subscripts
    text = re.sub(r'_\{([^}]+)\}', r'_\1', text)
    
    # Handle superscripts: ^{2} -> ^2
    text = re.sub(r'\^\{([^}]+)\}', r'^\1', text)
    
    # Remove remaining braces that are just grouping
    text = re.sub(r'\{([^}]+)\}', r'\1', text)
    
    # Clean up extra spaces and normalize
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    
    # Handle multiplication: "m v" -> "m * v" (but be careful with subscripts/superscripts)
    # Only add * between variables/numbers, not after subscripts/superscripts
    text = re.sub(r'([a-zA-Z0-9_\)\]\}])\s+([a-zA-Z0-9_\(\[\{])', r'\1 * \2', text)
    
    # Clean up multiple operators and spaces
    text = re.sub(r'\*\s*\*', '*', text)
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'\s*\*\s*', ' * ', text)
    text = re.sub(r'\s*\+\s*', ' + ', text)
    text = re.sub(r'\s*-\s*', ' - ', text)
    text = re.sub(r'\s*=\s*', ' = ', text)
    text = re.sub(r'\s*/\s*', ' / ', text)
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    
    return text

def populate_expressions():
    """Populate formula_expression for all formulas."""
    conn = None
    try:
        # Parse DATABASE_URL
        if DATABASE_URL.startswith('postgres://'):
            db_url = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
        else:
            db_url = DATABASE_URL
        
        # Determine SSL mode
        sslmode = "require" if DATABASE_URL.startswith("postgres://") else "disable"
        
        conn = psycopg2.connect(db_url, sslmode=sslmode)
        cur = conn.cursor()
        
        print("=" * 70)
        print("Populating formula_expression for all formulas")
        print("=" * 70)
        
        # Get all formulas
        cur.execute("""
            SELECT formula_id, formula_name, latex, formula_expression
            FROM tbl_formula
            ORDER BY formula_id;
        """)
        
        formulas = cur.fetchall()
        
        updated_count = 0
        skipped_count = 0
        
        for formula_id, formula_name, latex, existing_expression in formulas:
            if existing_expression:
                print(f"⏭️  Skipping {formula_id}: {formula_name} (already has expression)")
                skipped_count += 1
                continue
            
            if not latex:
                print(f"⚠️  Skipping {formula_id}: {formula_name} (no LaTeX)")
                skipped_count += 1
                continue
            
            # Convert LaTeX to plain text
            plain_text = latex_to_plain_text(latex)
            
            if plain_text:
                cur.execute("""
                    UPDATE tbl_formula
                    SET formula_expression = %s
                    WHERE formula_id = %s;
                """, (plain_text, formula_id))
                
                print(f"✅ Updated {formula_id}: {formula_name}")
                print(f"   LaTeX: {latex}")
                print(f"   Plain: {plain_text}")
                updated_count += 1
            else:
                print(f"⚠️  Could not convert {formula_id}: {formula_name}")
                skipped_count += 1
        
        conn.commit()
        
        print("\n" + "=" * 70)
        print(f"✅ Successfully updated {updated_count} formulas")
        print(f"⏭️  Skipped {skipped_count} formulas")
        print("=" * 70)
        
        cur.close()
        conn.close()
        
    except psycopg2.Error as e:
        print(f"\n❌ Database error occurred:")
        print(f"  {e}")
        if conn:
            conn.rollback()
            conn.close()
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        if conn:
            conn.rollback()
            conn.close()
        sys.exit(1)

if __name__ == '__main__':
    populate_expressions()
