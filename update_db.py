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
    print("Elimu Centric - Database Check & Update")
    print("=" * 60)

    try:
        from db_health import check_and_heal, analyze_db, print_analysis, get_db_connection
        ok, msg = check_and_heal()
        if ok:
            print(f"[OK] {msg}")
            # Show brief analysis
            conn = get_db_connection()
            if conn:
                analysis = analyze_db(conn)
                print(f"\nTables: {len(analysis.get('tables', []))} | Total rows: {analysis.get('total_rows', 0):,}")
                if analysis.get('missing_tables'):
                    print(f"Missing: {', '.join(analysis['missing_tables'])}")
                try:
                    conn.close()
                except Exception:
                    pass
        else:
            print(f"[FAIL] {msg}")
            sys.exit(1)
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    print("=" * 60)
    print("Database update finished. You can start the app.")
    print("=" * 60)

if __name__ == "__main__":
    main()
