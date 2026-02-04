#!/usr/bin/env python3
"""
Backup the linguaformula database.

Usage:
    Local: python backup_database.py
    Heroku: heroku run python backup_database.py -a linguaformula-backend
"""

import os
import sys
import subprocess
from datetime import datetime

# Get database URL from environment or use defaults
DATABASE_URL = os.environ.get('DATABASE_URL')

if not DATABASE_URL:
    # Default to local database
    DB_NAME = os.environ.get('DB_NAME', 'linguaformula')
    DB_USER = os.environ.get('DB_USER', 'dev_user')
    DB_PASSWORD = os.environ.get('DB_PASSWORD')
    DB_HOST = os.environ.get('DB_HOST', 'localhost')
    DB_PORT = os.environ.get('DB_PORT', '5432')
    
    if not DB_PASSWORD:
        import getpass
        DB_PASSWORD = getpass.getpass(f"Enter password for database user '{DB_USER}': ")
    
    # Set PGPASSWORD for pg_dump
    if DB_PASSWORD:
        os.environ['PGPASSWORD'] = DB_PASSWORD
    
    # Build connection string for pg_dump
    conn_string = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
else:
    # Parse DATABASE_URL for pg_dump
    if DATABASE_URL.startswith('postgres://'):
        DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
    
    # Extract components from DATABASE_URL
    # Format: postgresql://user:password@host:port/dbname
    import urllib.parse
    parsed = urllib.parse.urlparse(DATABASE_URL)
    DB_USER = parsed.username
    DB_PASSWORD = parsed.password
    DB_HOST = parsed.hostname
    DB_PORT = parsed.port or '5432'
    DB_NAME = parsed.path.lstrip('/')
    
    if DB_PASSWORD:
        os.environ['PGPASSWORD'] = DB_PASSWORD
    
    conn_string = DATABASE_URL

def create_backup():
    """Create a backup of the database."""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = f"linguaformula_backup_{timestamp}.sql"
    
    print("=" * 70)
    print("Creating Database Backup")
    print("=" * 70)
    print(f"Database: {DB_NAME}")
    print(f"Backup file: {backup_file}")
    print()
    
    try:
        # Use pg_dump to create backup
        cmd = [
            'pg_dump',
            '-h', DB_HOST,
            '-p', str(DB_PORT),
            '-U', DB_USER,
            '-d', DB_NAME,
            '-F', 'c',  # Custom format (compressed)
            '-f', backup_file
        ]
        
        print("Running pg_dump...")
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        # Check file was created
        if os.path.exists(backup_file):
            file_size = os.path.getsize(backup_file)
            print(f"\n✓ Backup created successfully!")
            print(f"  File: {backup_file}")
            print(f"  Size: {file_size:,} bytes ({file_size / 1024:.2f} KB)")
            return backup_file
        else:
            print("\n✗ ERROR: Backup file was not created")
            sys.exit(1)
            
    except subprocess.CalledProcessError as e:
        print(f"\n✗ ERROR: pg_dump failed")
        print(f"  {e.stderr}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        sys.exit(1)

if __name__ == '__main__':
    backup_file = create_backup()
    print(f"\nBackup complete: {backup_file}")
    print("\nYou can restore this backup with:")
    print(f"  pg_restore -d linguaformula -U dev_user {backup_file}")
