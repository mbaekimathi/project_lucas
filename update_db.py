#!/usr/bin/env python3
"""
Run this after 'git pull' to create/update database tables and run migrations.
Usage: python update_db.py

Safe for existing data: only creates missing tables, adds missing columns,
and runs migration scripts. It does NOT delete, truncate, or overwrite
your existing data.
"""
import sys
import os

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def main():
    print("=" * 60)
    print("Updating database (tables + migrations)...")
    print("=" * 60)
    
    # 1. Create/update tables via init_db
    try:
        from app import init_db
        if init_db():
            print("[OK] init_db completed - tables created/verified")
        else:
            print("[WARN] init_db returned False (check DB connection)")
    except Exception as e:
        print(f"[ERROR] init_db failed: {e}")
        sys.exit(1)
    
    # 2. Run migration files
    try:
        from migrations.migration_manager import run_all_migrations
        if run_all_migrations():
            print("[OK] All migrations applied")
        else:
            print("[WARN] Some migrations failed - check output above")
    except Exception as e:
        print(f"[ERROR] Migrations failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    print("=" * 60)
    print("Database update finished. You can start the app.")
    print("=" * 60)

if __name__ == "__main__":
    main()
