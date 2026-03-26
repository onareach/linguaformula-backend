#!/usr/bin/env python3
"""
Python-based database setup script for LinguaFormula
This script handles password authentication better than bash
"""
import subprocess
import sys
import getpass
import os

DB_NAME = "linguaformula"
DB_USER = "dev_user"
DB_PASSWORD = "dev123"

def run_psql(command, database="postgres", user=None, password=None):
    """Run a psql command"""
    cmd = ["psql"]
    if database:
        cmd.extend(["-d", database])
    if user:
        cmd.extend(["-U", user])
    if password:
        env = os.environ.copy()
        env["PGPASSWORD"] = password
    else:
        env = os.environ.copy()
    
    cmd.extend(["-c", command])
    
    try:
        result = subprocess.run(cmd, env=env, capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        if "password authentication failed" in e.stderr.lower():
            print(f"❌ Authentication failed. Please check your PostgreSQL password.")
            sys.exit(1)
        raise

def run_sql_file(filename, database, user, password):
    """Run a SQL file"""
    cmd = ["psql", "-d", database, "-U", user, "-f", filename]
    env = os.environ.copy()
    env["PGPASSWORD"] = password
    
    try:
        subprocess.run(cmd, env=env, check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to run {filename}")
        print(f"   Error: {e.stderr if hasattr(e, 'stderr') else str(e)}")
        return False

def main():
    print("🗄️  Setting up LinguaFormula database...")
    print()
    
    # Get PostgreSQL password
    pg_password = os.environ.get("PGPASSWORD")
    if not pg_password:
        print("⚠️  PostgreSQL password required")
        print("   You can set PGPASSWORD environment variable to avoid this prompt")
        pg_password = getpass.getpass("Enter PostgreSQL password (for 'postgres' user): ")
    
    # Check if database exists
    print("📋 Checking if database exists...")
    try:
        result = run_psql(f"SELECT 1 FROM pg_database WHERE datname='{DB_NAME}'", 
                         password=pg_password)
        if "1" in result:
            print(f"✅ Database '{DB_NAME}' already exists")
        else:
            print(f"📦 Creating database '{DB_NAME}'...")
            subprocess.run(["createdb", "-U", "postgres", DB_NAME], 
                         env={**os.environ, "PGPASSWORD": pg_password}, check=True)
            print(f"✅ Database '{DB_NAME}' created")
    except Exception as e:
        print(f"❌ Error checking/creating database: {e}")
        sys.exit(1)
    
    # Check if user exists
    print("📋 Checking if user exists...")
    try:
        result = run_psql(f"SELECT 1 FROM pg_roles WHERE rolname='{DB_USER}'", 
                         password=pg_password)
        if "1" in result:
            print(f"✅ User '{DB_USER}' already exists")
        else:
            print(f"👤 Creating user '{DB_USER}'...")
            run_psql(f"CREATE USER {DB_USER} WITH PASSWORD '{DB_PASSWORD}';", 
                    password=pg_password)
            print(f"✅ User '{DB_USER}' created")
    except Exception as e:
        print(f"❌ Error checking/creating user: {e}")
        sys.exit(1)
    
    # Grant privileges
    print("🔐 Granting privileges...")
    try:
        run_psql(f"GRANT ALL PRIVILEGES ON DATABASE {DB_NAME} TO {DB_USER};", 
                password=pg_password)
        run_psql(f"GRANT ALL ON SCHEMA public TO {DB_USER};", 
                database=DB_NAME, password=pg_password)
        print("✅ Privileges granted")
    except Exception as e:
        print(f"❌ Error granting privileges: {e}")
        sys.exit(1)
    
    # Run migrations
    print("📝 Running migrations...")
    migrations_dir = os.path.join(os.path.dirname(__file__), "migrations")
    
    migrations = [
        "initial_schema.sql",
        "schema_migration.sql"
    ]
    
    for migration in migrations:
        migration_path = os.path.join(migrations_dir, migration)
        if not os.path.exists(migration_path):
            print(f"⚠️  Migration file not found: {migration_path}")
            continue
        
        print(f"  → Running {migration}...")
        if run_sql_file(migration_path, DB_NAME, DB_USER, DB_PASSWORD):
            print(f"    ✅ {migration} completed")
        else:
            print(f"    ❌ {migration} failed")
            sys.exit(1)
    
    print()
    print("✅ Database setup complete!")
    print()
    print("📋 Connection string:")
    print(f"   postgresql://{DB_USER}:{DB_PASSWORD}@localhost:5432/{DB_NAME}?sslmode=disable")
    print()
    print("💡 To use this in your app, set:")
    print(f"   export DATABASE_URL=\"postgresql://{DB_USER}:{DB_PASSWORD}@localhost:5432/{DB_NAME}?sslmode=disable\"")

if __name__ == "__main__":
    main()
