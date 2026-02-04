#!/usr/bin/env python3
"""
Update Kinetic energy formula on Heroku database.
This script is designed to run on Heroku where DATABASE_URL is set automatically.
"""
import os
import sys
import psycopg2

# Get DATABASE_URL from environment (set by Heroku)
DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    print("❌ DATABASE_URL not found in environment")
    print("   This script should be run on Heroku with: heroku run python update_kinetic_energy_heroku.py")
    sys.exit(1)

def update_kinetic_energy():
    """Update Kinetic energy formula with all enhanced fields."""
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
        
        # Update english_verbalization with one English expression
        english_verbalization = "Kinetic energy equals one-half times mass times velocity squared."
        
        # Update symbolic_verbalization with pronunciation examples
        symbolic_verbalization = """Pronunciation examples: "E equals one-half m v squared" or "Kinetic energy equals one-half times mass times velocity squared" or "E sub kinetic equals one-half m v squared"."""
        
        # Update units with SI units first, then alternatives
        units = """SI units: Joules (J) or kg·m²/s². Alternative units: ergs (g·cm²/s²) in CGS system, or foot-pounds (ft·lb) in imperial system."""
        
        # Update example with a calculation
        example = """If a bicycle weighing 20 kg is moving at 3 meters per second, the kinetic energy is calculated as: E = (1/2) × m × v² = (1/2) × 20 kg × (3 m/s)² = (1/2) × 20 × 9 = 90 J."""
        
        # Update historical context
        historical_context = """The concept of kinetic energy (originally called 'vis viva' or 'living force') was first proposed by Gottfried Wilhelm Leibniz (1646-1716) around 1686. Leibniz initially proposed mv² as the measure of 'living force', but the modern form E = (1/2)mv² with the factor of 1/2 was established in the 19th century through the work-energy theorem. The formula was developed to quantify the energy of motion and solve problems in mechanics, particularly in understanding collisions and the conservation of energy in physical systems."""
        
        cur.execute("""
            UPDATE tbl_formula
            SET english_verbalization = %s,
                symbolic_verbalization = %s,
                units = %s,
                example = %s,
                historical_context = %s
            WHERE formula_id = 35;
        """, (english_verbalization, symbolic_verbalization, units, example, historical_context))
        
        conn.commit()
        
        # Verify the update
        cur.execute("""
            SELECT formula_id, formula_name, latex, english_verbalization, symbolic_verbalization, units, example, historical_context
            FROM tbl_formula
            WHERE formula_id = 35;
        """)
        
        result = cur.fetchone()
        print("=" * 70)
        print("Updated Kinetic Energy Formula on Heroku")
        print("=" * 70)
        print(f"Formula ID: {result[0]}")
        print(f"Formula Name: {result[1]}")
        print(f"LaTeX: {result[2]}")
        print(f"\nEnglish Verbalization:")
        print(result[3])
        print(f"\nSymbolic Verbalization (Pronunciation Examples):")
        print(result[4])
        print(f"\nUnits:")
        print(result[5])
        print(f"\nExample:")
        print(result[6])
        print(f"\nHistorical Context:")
        print(result[7])
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
    update_kinetic_energy()
