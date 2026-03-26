#!/usr/bin/env python3
"""
Import sample formulas into the LinguaFormula database
"""
import subprocess
import sys
import os
import getpass

DB_NAME = "linguaformula"
DB_USER = "dev_user"
DB_PASSWORD = "dev123"

def run_sql_file(filename, description):
    """Run a SQL migration file"""
    migrations_dir = os.path.join(os.path.dirname(__file__), "migrations")
    filepath = os.path.join(migrations_dir, filename)
    
    if not os.path.exists(filepath):
        print(f"⚠️  Migration file not found: {filepath}")
        return False
    
    print(f"  → {description}...")
    
    # Try with PGPASSWORD first
    env = os.environ.copy()
    env["PGPASSWORD"] = DB_PASSWORD
    
    cmd = ["psql", "-d", DB_NAME, "-U", DB_USER, "-f", filepath]
    
    try:
        result = subprocess.run(cmd, env=env, capture_output=True, text=True, check=True)
        print(f"    ✅ {description} completed")
        if result.stdout:
            print(f"    {result.stdout.strip()}")
        return True
    except subprocess.CalledProcessError as e:
        if "password authentication failed" in e.stderr.lower():
            print(f"    ⚠️  Password authentication required")
            # Try interactive
            try:
                subprocess.run(cmd, check=True)
                print(f"    ✅ {description} completed")
                return True
            except:
                print(f"    ❌ {description} failed: {e.stderr}")
                return False
        else:
            print(f"    ❌ {description} failed: {e.stderr}")
            return False

def verify_import():
    """Verify formulas were imported"""
    env = os.environ.copy()
    env["PGPASSWORD"] = DB_PASSWORD
    
    cmd = ["psql", "-d", DB_NAME, "-U", DB_USER, "-c", "SELECT COUNT(*) as total_formulas FROM formula;"]
    
    try:
        result = subprocess.run(cmd, env=env, capture_output=True, text=True, check=True)
        print(f"\n📊 Database status:")
        print(result.stdout)
        return True
    except:
        # Try interactive
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            print(f"\n📊 Database status:")
            print(result.stdout)
            return True
        except Exception as e:
            print(f"⚠️  Could not verify: {e}")
            return False

def main():
    print("📥 Importing sample formulas into database...")
    print()
    
    # Import production formulas
    if not run_sql_file("import_production_formulas.sql", "Importing production formulas"):
        print("\n❌ Failed to import production formulas")
        sys.exit(1)
    
    # Add simple linear regression
    run_sql_file("add_simple_linear_regression.sql", "Adding simple linear regression")
    
    # Verify
    verify_import()
    
    print()
    print("✅ Formula import complete!")
    print()
    print("💡 Your formulas should now be visible at http://localhost:3000")
    print("   (Make sure both backend and frontend are running)")

if __name__ == "__main__":
    main()
