"""
Elimu Centric - Database Health & Auto-Heal Module

Analyzes the database (tables, columns, row counts), checks for missing tables
on both local and hosted environments, and auto-creates them on startup.

Usage:
  - Runs automatically when the app starts (local + hosted)
  - CLI: python db_health.py [--analyze] [--check]
"""
import os
import sys
import json
from datetime import datetime

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load .env before importing app
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# All required tables for Elimu Centric (from init_db + migrations)
REQUIRED_TABLES = [
    'users', 'students', 'parents', 'admissions', 'news', 'gallery',
    'employees', 'employee_salaries', 'employee_salary_payments',
    'employee_salary_audits', 'employee_permissions', 'school_settings',
    'integration_settings', 'academic_coordinator_settings',
    'academic_levels', 'subjects', 'teacher_subject_assignments',
    'academic_years', 'terms', 'term_academic_levels',
    'fee_structures', 'fee_items', 'student_payments', 'student_payment_audit',
    'timetables', 'exams', 'exam_supervisors', 'student_marks',
    'backup_settings', 'backup_history', 'student_attendance_records',
    'migrations',
]


def get_db_connection():
    """Get database connection - lazy import to avoid circular deps."""
    from app import get_db_connection as _conn
    return _conn()


def ensure_database_exists():
    """Ensure the database exists, create if missing."""
    from app import ensure_database_exists as _ensure
    return _ensure()


def init_db():
    """Initialize database tables."""
    from app import init_db as _init
    return _init()


def run_all_migrations():
    """Run all pending migrations."""
    from migrations.migration_manager import run_all_migrations as _run
    return _run()


def analyze_db(connection=None):
    """
    Analyze the database: list tables, columns, and row counts.
    Returns a dict with tables, columns per table, row counts, and status.
    """
    close_conn = False
    if connection is None:
        connection = get_db_connection()
        close_conn = connection is not None

    if not connection:
        return {'ok': False, 'error': 'Could not connect to database', 'tables': []}

    result = {
        'ok': True,
        'database': None,
        'analyzed_at': datetime.now().isoformat(),
        'tables': [],
        'missing_tables': [],
        'total_rows': 0,
    }

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT DATABASE()")
            db = cursor.fetchone()
            result['database'] = db['DATABASE()'] if isinstance(db, dict) else (db[0] if db else None)

            # Get all tables
            cursor.execute("""
                SELECT TABLE_NAME, TABLE_ROWS
                FROM information_schema.TABLES
                WHERE TABLE_SCHEMA = DATABASE()
                ORDER BY TABLE_NAME
            """)
            tables_data = cursor.fetchall() or []

            for row in tables_data:
                if isinstance(row, dict):
                    table_name = row.get('TABLE_NAME') or row.get('table_name') or list(row.values())[0]
                    row_count = row.get('TABLE_ROWS') or row.get('table_rows')
                else:
                    table_name = row[0] if row else ''
                    row_count = row[1] if len(row) > 1 else None
                if row_count is None:
                    row_count = 0
                try:
                    row_count = int(row_count)
                except (TypeError, ValueError):
                    row_count = 0

                # Get columns for this table
                cursor.execute("""
                    SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_KEY, COLUMN_DEFAULT
                    FROM information_schema.COLUMNS
                    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s
                    ORDER BY ORDINAL_POSITION
                """, (table_name,))
                cols = cursor.fetchall() or []
                columns = []
                for c in cols:
                    if isinstance(c, dict):
                        col_name = c.get('COLUMN_NAME') or c.get('column_name') or ''
                        col_type = c.get('DATA_TYPE') or c.get('data_type') or ''
                        col_null = (c.get('IS_NULLABLE') or c.get('is_nullable') or '') == 'YES'
                        col_key = c.get('COLUMN_KEY') or c.get('column_key') or ''
                    else:
                        col_name = c[0] if len(c) > 0 else ''
                        col_type = c[1] if len(c) > 1 else ''
                        col_null = (c[2] if len(c) > 2 else '') == 'YES'
                        col_key = c[3] if len(c) > 3 else ''
                    columns.append({'name': col_name, 'type': col_type, 'nullable': col_null, 'key': col_key})

                result['tables'].append({
                    'name': table_name,
                    'rows': int(row_count),
                    'column_count': len(columns),
                    'columns': columns,
                })
                result['total_rows'] += int(row_count)

            # Find missing required tables
            existing = {t['name'] for t in result['tables']}
            result['missing_tables'] = [t for t in REQUIRED_TABLES if t not in existing]

    except Exception as e:
        result['ok'] = False
        result['error'] = f"{type(e).__name__}: {e}"
    finally:
        if close_conn and connection:
            try:
                connection.close()
            except Exception:
                pass

    return result


def check_and_heal():
    """
    Check database health and auto-create missing tables.
    Runs on both local and hosted. Safe to call on every startup.
    Returns (success: bool, message: str)
    """
    # 1. Ensure database exists
    if not ensure_database_exists():
        return False, "Failed to ensure database exists"

    # 2. Run init_db (creates core tables)
    if not init_db():
        return False, "Failed to initialize database tables"

    # 3. Run migrations (adds migration-only tables/columns)
    if not run_all_migrations():
        return False, "Some migrations failed"

    # 4. Verify no required tables are missing
    conn = get_db_connection()
    if not conn:
        return False, "Could not connect to verify"

    try:
        analysis = analyze_db(conn)
        if analysis.get('missing_tables'):
            return False, f"Missing tables after heal: {', '.join(analysis['missing_tables'])}"
        return True, f"Database ready. {len(analysis.get('tables', []))} tables verified."
    except Exception as e:
        return False, str(e)
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass


def print_analysis(analysis):
    """Print analysis report to stdout."""
    if not analysis.get('ok'):
        print(f"Error: {analysis.get('error', 'Unknown')}")
        return

    print("=" * 70)
    print("Elimu Centric - Database Analysis")
    print("=" * 70)
    print(f"Database: {analysis.get('database', 'N/A')}")
    print(f"Analyzed: {analysis.get('analyzed_at', 'N/A')}")
    print(f"Total rows: {analysis.get('total_rows', 0):,}")
    print()

    if analysis.get('missing_tables'):
        print("Missing required tables:")
        for t in analysis['missing_tables']:
            print(f"  - {t}")
        print()

    print("Tables:")
    print("-" * 70)
    for t in sorted(analysis.get('tables', []), key=lambda x: x['name']):
        status = "OK" if t['name'] in REQUIRED_TABLES else "extra"
        print(f"  {t['name']:40} {t['rows']:>10,} rows  {t['column_count']:>3} cols  [{status}]")
    print("=" * 70)


def main():
    """CLI entry point."""
    import argparse
    parser = argparse.ArgumentParser(description='Elimu Centric DB Health & Analysis')
    parser.add_argument('--analyze', action='store_true', help='Analyze DB and print report')
    parser.add_argument('--check', action='store_true', help='Check and heal (create missing tables)')
    parser.add_argument('--json', action='store_true', help='Output analysis as JSON')
    args = parser.parse_args()

    if args.check:
        print("Checking and healing database...")
        ok, msg = check_and_heal()
        print(msg)
        sys.exit(0 if ok else 1)

    # Default: analyze
    conn = get_db_connection()
    if not conn:
        print("Failed to connect to database")
        sys.exit(1)

    analysis = analyze_db(conn)
    if conn:
        try:
            conn.close()
        except Exception:
            pass

    if args.json:
        print(json.dumps(analysis, indent=2, default=str))
    else:
        print_analysis(analysis)

    sys.exit(0 if analysis.get('ok') else 1)


if __name__ == '__main__':
    main()
