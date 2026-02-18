#!/usr/bin/env python3
"""
Seed tbl_constant and tbl_unit with initial data.
Constants: pi, e, c, Boltzmann constant, Planck constant
Units: SI base units (meter, kilogram, second, ampere, kelvin, mole, candela)

Run: python3 seed_constants_and_units.py
"""
import os

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    DATABASE_URL = "postgresql://dev_user:dev123@localhost:5432/linguaformula?sslmode=disable"

sslmode = "require" if DATABASE_URL.startswith("postgres://") else "disable"
db_url = (
    DATABASE_URL.replace("postgres://", "postgresql://", 1)
    if DATABASE_URL.startswith("postgres://")
    else DATABASE_URL
)

CONSTANTS = [
    ("pi", r"\pi", "3.14159...", "Ratio of a circle's circumference to its diameter.", 1),
    ("e", "e", "2.71828...", "Euler's number; base of natural logarithms.", 2),
    ("c", "c", "299792458 m/s", "Speed of light in vacuum.", 3),
    ("Boltzmann constant", "k_B", "1.380649×10⁻²³ J/K", "Relates energy to temperature at the particle level.", 4),
    ("Planck constant", "h", "6.62607015×10⁻³⁴ J⋅s", "Relates energy of a photon to its frequency.", 5),
]

SI_UNITS = [
    ("meter", "m", "SI", "Base unit of length.", 1),
    ("kilogram", "kg", "SI", "Base unit of mass.", 2),
    ("second", "s", "SI", "Base unit of time.", 3),
    ("ampere", "A", "SI", "Base unit of electric current.", 4),
    ("kelvin", "K", "SI", "Base unit of thermodynamic temperature.", 5),
    ("mole", "mol", "SI", "Base unit of amount of substance.", 6),
    ("candela", "cd", "SI", "Base unit of luminous intensity.", 7),
]


def run():
    import psycopg2

    conn = psycopg2.connect(db_url, sslmode=sslmode)
    cur = conn.cursor()

    for name, symbol, value_text, description, display_order in CONSTANTS:
        cur.execute(
            "SELECT constant_id FROM tbl_constant WHERE constant_name = %s;",
            (name,),
        )
        if cur.fetchone():
            continue
        cur.execute(
            """
            INSERT INTO tbl_constant (constant_name, symbol, value_text, description, display_order)
            VALUES (%s, %s, %s, %s, %s);
            """,
            (name, symbol, value_text, description, display_order),
        )
        print(f"  Added constant: {name}")

    for name, symbol, unit_system, description, display_order in SI_UNITS:
        cur.execute(
            "SELECT unit_id FROM tbl_unit WHERE unit_name = %s AND (unit_system = %s OR (unit_system IS NULL AND %s IS NULL));",
            (name, unit_system, unit_system),
        )
        if cur.fetchone():
            continue
        cur.execute(
            """
            INSERT INTO tbl_unit (unit_name, symbol, unit_system, description, display_order)
            VALUES (%s, %s, %s, %s, %s);
            """,
            (name, symbol, unit_system, description, display_order),
        )
        print(f"  Added unit: {name}")

    conn.commit()
    cur.close()
    conn.close()
    print("Done.")


if __name__ == "__main__":
    run()
