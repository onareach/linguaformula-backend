#!/usr/bin/env python3
"""
Populate the discipline tables with hierarchical structure.

This script creates:
- Parent disciplines: Physics, Mathematics
- Child disciplines under each parent
- Links formulas to appropriate disciplines

Usage:
    Local: python populate_disciplines.py
    Heroku: heroku run python populate_disciplines.py -a linguaformula-backend
"""

import os
import sys
import psycopg2

# Get database URL from environment or use defaults
DATABASE_URL = os.environ.get('DATABASE_URL')

if not DATABASE_URL:
    # Default to local database
    DB_NAME = os.environ.get('DB_NAME', 'linguaformula')
    DB_USER = os.environ.get('DB_USER', 'dev_user')
    DB_PASSWORD = os.environ.get('DB_PASSWORD', 'dev123')
    DB_HOST = os.environ.get('DB_HOST', 'localhost')
    DB_PORT = os.environ.get('DB_PORT', '5432')
    
    DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Parse DATABASE_URL if needed
if DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

# Define the hierarchical discipline structure
DISCIPLINES = [
    # Parent disciplines
    {
        'handle': 'physics',
        'name': 'Physics',
        'description': 'The study of matter, motion, energy, and force',
        'parent_id': None
    },
    {
        'handle': 'mathematics',
        'name': 'Mathematics',
        'description': 'The study of numbers, quantities, structures, and relationships',
        'parent_id': None
    },
    # Child disciplines under Physics
    {
        'handle': 'classical_mechanics',
        'name': 'Classical Mechanics',
        'description': 'The branch of physics that deals with the motion of objects under the influence of forces',
        'parent_handle': 'physics'
    },
    {
        'handle': 'relativity',
        'name': 'Relativity',
        'description': 'Einstein\'s theories of special and general relativity',
        'parent_handle': 'physics'
    },
    # Child disciplines under Mathematics
    {
        'handle': 'pure_mathematics',
        'name': 'Pure Mathematics',
        'description': 'The study of mathematical concepts independent of application',
        'parent_handle': 'mathematics'
    },
    {
        'handle': 'combinatorics',
        'name': 'Combinatorics',
        'description': 'The study of counting, arrangement, and combination of objects',
        'parent_handle': 'mathematics'
    },
    {
        'handle': 'probability',
        'name': 'Probability',
        'description': 'The study of likelihood and uncertainty in random events',
        'parent_handle': 'mathematics'
    },
    {
        'handle': 'statistics',
        'name': 'Statistics',
        'description': 'The study of collection, analysis, interpretation, and presentation of data',
        'parent_handle': 'mathematics'
    }
]

# Formula to discipline mappings (by formula name)
FORMULA_DISCIPLINES = {
    # Classical Mechanics
    'Momentum': ['classical_mechanics'],
    'Conservation of momentum': ['classical_mechanics'],
    'Kinetic energy': ['classical_mechanics'],
    'Potential energy': ['classical_mechanics'],
    "Newton's Second Law": ['classical_mechanics'],
    
    # Relativity
    'Mass-energy equivalence': ['relativity'],
    
    # Pure Mathematics
    "Euler's Number": ['pure_mathematics'],
    
    # Combinatorics
    'Number of Ways to Arrange n Objects': ['combinatorics'],
    'Permutations: Counting the Ways to Arrange r DISTINCT Objects Selected from n with No Replacement': ['combinatorics'],
    'Permutations of n Objects with Repeated Types': ['combinatorics'],
    'Number of Ways to Choose from n with No Replacement and Order Does Not Matter': ['combinatorics'],
    'Multiplication Rule (for statistical counting techniques)': ['combinatorics'],
    
    # Probability
    'Sample: Individual Outcome': ['probability'],
    'Event': ['probability'],
    'Events – Union': ['probability'],
    'Events – Intersection': ['probability'],
    'Event – Complement': ['probability'],
    'Events – Mutually Exclusive': ['probability'],
    'Double Complement Law': ['probability'],
    'Distributive Law of Intersection over Union': ['probability'],
    'Distributive Law of Union over Intersection': ['probability'],
    "De Morgan's Law (1)": ['probability'],
    "De Morgan's Law (2)": ['probability'],
    'Probability of an Event': ['probability'],
    'Probability of Equally Likely Outcomes': ['probability'],
    'Probability of Equally Likely Outcomes (2)': ['probability'],
    'Probability: Addition Rule for Discrete Probability': ['probability'],
    'Probability: Relative Frequency Approximation of Probability': ['probability'],
    'Probability: Addition Rule for Unions – Overlapping and Mutually Exclusive': ['probability'],
    'Probability: Mutually Exclusive Events': ['probability'],
    'Probability: Conditional Events': ['probability'],
    'Probability: Multiplication Rule for Conditional, Or Dependent, Events': ['probability'],
    'Probability: Total Probability Rule (for Two Mutually Exclusive Events)': ['probability'],
    'Probability: Success of Independent Series Components': ['probability'],
    'Probability: Success of Independent Parallel Components': ['probability'],
    'Probability: Zero Contaminated Samples (Independent Trials)': ['probability'],
    'Probability Mass Function (PMF)': ['probability'],
    'Cumulative Distribution Function (CDF)': ['probability'],
    'Mean (Or Expected Value) of a Discrete Random Variable': ['probability'],
    'Variance of a Discrete Random Variable': ['probability'],
    'Standard Deviation of a Discrete Random Variable': ['probability'],
    'Binomial Formula': ['probability'],
    'Binomial Probability Mass Function (PMF)': ['probability'],
    
    # Statistics
    'Size of Population (of Data)': ['statistics'],
    'Size of a Sample (of Data)': ['statistics'],
    'Sample Space: A Set of All Possible Outcomes': ['statistics', 'probability'],  # Appears in both
    'Positive Real Sample Space': ['statistics', 'probability'],  # Appears in both
}

def populate_disciplines():
    """Populate the discipline tables."""
    conn = None
    try:
        conn = psycopg2.connect(DATABASE_URL)
        conn.autocommit = False
        cur = conn.cursor()
        
        print("=" * 70)
        print("Populating Discipline Tables")
        print("=" * 70)
        print()
        
        # First, insert parent disciplines
        parent_ids = {}
        for disc in DISCIPLINES:
            if 'parent_handle' not in disc:
                print(f"Inserting parent discipline: {disc['name']} ({disc['handle']})")
                cur.execute("""
                    INSERT INTO tbl_discipline (discipline_handle, discipline_name, discipline_description, discipline_parent_id)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (discipline_handle) DO UPDATE
                    SET discipline_name = EXCLUDED.discipline_name,
                        discipline_description = EXCLUDED.discipline_description
                    RETURNING discipline_id;
                """, (disc['handle'], disc['name'], disc['description'], None))
                parent_ids[disc['handle']] = cur.fetchone()[0]
                print(f"  ✓ Created with ID: {parent_ids[disc['handle']]}")
        
        print()
        
        # Then, insert child disciplines
        child_ids = {}
        for disc in DISCIPLINES:
            if disc.get('parent_handle'):
                parent_id = parent_ids.get(disc['parent_handle'])
                if not parent_id:
                    print(f"  ✗ ERROR: Parent '{disc['parent_handle']}' not found for {disc['handle']}")
                    continue
                
                print(f"Inserting child discipline: {disc['name']} ({disc['handle']}) under {disc['parent_handle']}")
                cur.execute("""
                    INSERT INTO tbl_discipline (discipline_handle, discipline_name, discipline_description, discipline_parent_id)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (discipline_handle) DO UPDATE
                    SET discipline_name = EXCLUDED.discipline_name,
                        discipline_description = EXCLUDED.discipline_description,
                        discipline_parent_id = EXCLUDED.discipline_parent_id
                    RETURNING discipline_id;
                """, (disc['handle'], disc['name'], disc['description'], parent_id))
                child_ids[disc['handle']] = cur.fetchone()[0]
                print(f"  ✓ Created with ID: {child_ids[disc['handle']]}")
        
        # Combine parent and child IDs
        all_discipline_ids = {**parent_ids, **child_ids}
        
        print()
        print("=" * 70)
        print("Linking Formulas to Disciplines")
        print("=" * 70)
        print()
        
        # Get all formulas
        cur.execute("SELECT formula_id, formula_name FROM tbl_formula ORDER BY formula_id;")
        formulas = cur.fetchall()
        
        linked_count = 0
        for formula_id, formula_name in formulas:
            disciplines = FORMULA_DISCIPLINES.get(formula_name, [])
            
            if not disciplines:
                print(f"  ⚠ {formula_name}: No discipline mapping found")
                continue
            
            # Link formula to each discipline
            for i, disc_handle in enumerate(disciplines):
                disc_id = all_discipline_ids.get(disc_handle)
                if not disc_id:
                    print(f"  ✗ Discipline '{disc_handle}' not found for {formula_name}")
                    continue
                
                is_primary = (i == 0)  # First discipline is primary
                rank = i + 1
                
                cur.execute("""
                    INSERT INTO tbl_formula_discipline 
                    (formula_id, discipline_id, formula_discipline_is_primary, formula_discipline_rank)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (formula_id, discipline_id) DO UPDATE
                    SET formula_discipline_is_primary = EXCLUDED.formula_discipline_is_primary,
                        formula_discipline_rank = EXCLUDED.formula_discipline_rank;
                """, (formula_id, disc_id, is_primary, rank))
                
                linked_count += 1
                if i == 0:
                    print(f"  ✓ {formula_name}: Linked to {disc_handle} (primary)")
                else:
                    print(f"    → Also linked to {disc_handle}")
        
        conn.commit()
        
        print()
        print("=" * 70)
        print("Summary")
        print("=" * 70)
        print(f"Total disciplines created: {len(all_discipline_ids)}")
        print(f"Total formula-discipline links: {linked_count}")
        print()
        
        # Verify the structure
        print("Discipline Hierarchy:")
        cur.execute("""
            SELECT 
                d.discipline_id,
                d.discipline_name,
                d.discipline_handle,
                COALESCE(p.discipline_name, 'ROOT') as parent_name
            FROM tbl_discipline d
            LEFT JOIN tbl_discipline p ON d.discipline_parent_id = p.discipline_id
            ORDER BY COALESCE(d.discipline_parent_id, 0), d.discipline_name;
        """)
        
        for row in cur.fetchall():
            indent = "  " if row[3] != 'ROOT' else ""
            print(f"{indent}{row[1]} ({row[2]}) - Parent: {row[3]}")
        
        cur.close()
        conn.close()
        
        print()
        print("✓ Discipline population complete!")
        
    except psycopg2.Error as e:
        print(f"\n✗ Database error: {e}")
        if conn:
            conn.rollback()
            conn.close()
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        if conn:
            conn.rollback()
            conn.close()
        sys.exit(1)

if __name__ == '__main__':
    populate_disciplines()
