"""
Database Migration Manager
Automatically runs database migrations on deployment
"""
import os
from datetime import datetime
from app import get_db_connection


def _migrations_columns(cursor):
    """Return set of column names on `migrations` (lowercase)."""
    cursor.execute(
        """
        SELECT COLUMN_NAME FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'migrations'
        """
    )
    rows = cursor.fetchall() or []
    out = set()
    for row in rows:
        name = row["COLUMN_NAME"] if isinstance(row, dict) else row[0]
        if name:
            out.add(name.lower())
    return out


def _add_column_if_missing(cursor, connection, col_name, ddl_fragment):
    """Run ALTER ADD COLUMN if col_name is missing. ddl_fragment is e.g. 'INT NULL' or \"ENUM('a') DEFAULT 'a'\"."""
    cols = _migrations_columns(cursor)
    if col_name.lower() in cols:
        return
    try:
        cursor.execute(f"ALTER TABLE migrations ADD COLUMN {col_name} {ddl_fragment}")
        connection.commit()
        print(f"Added '{col_name}' column to migrations table")
    except Exception as e:
        print(f"Note: Could not add {col_name} column: {e}")


def create_migrations_table(connection):
    """Create the migrations tracking table if it doesn't exist, and add missing columns."""
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS migrations (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    migration_name VARCHAR(255) UNIQUE NOT NULL,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    applied_by VARCHAR(255) DEFAULT 'system',
                    execution_time_ms INT NULL,
                    status ENUM('success', 'failed', 'partial') DEFAULT 'success',
                    error_message TEXT,
                    INDEX idx_migration_name (migration_name),
                    INDEX idx_applied_at (applied_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """
            )
            connection.commit()

            # Legacy tables: add columns in an order that never references a missing AFTER target.
            _add_column_if_missing(cursor, connection, "applied_by", "VARCHAR(255) DEFAULT 'system'")
            _add_column_if_missing(cursor, connection, "execution_time_ms", "INT NULL")
            _add_column_if_missing(
                cursor,
                connection,
                "status",
                "ENUM('success', 'failed', 'partial') DEFAULT 'success'",
            )
            _add_column_if_missing(cursor, connection, "error_message", "TEXT NULL")

            return True
    except Exception as e:
        print(f"Error creating migrations table: {e}")
        return False


def get_applied_migrations(connection):
    """Get list of already applied migrations (successful only when status column exists)."""
    try:
        with connection.cursor() as cursor:
            cols = _migrations_columns(cursor)
            if "status" in cols:
                if "applied_at" in cols:
                    cursor.execute(
                        """
                        SELECT migration_name
                        FROM migrations
                        WHERE status = 'success'
                        ORDER BY applied_at
                        """
                    )
                else:
                    cursor.execute(
                        """
                        SELECT migration_name
                        FROM migrations
                        WHERE status = 'success'
                        ORDER BY id
                        """
                    )
            else:
                if "applied_at" in cols:
                    cursor.execute(
                        """
                        SELECT migration_name
                        FROM migrations
                        ORDER BY applied_at
                        """
                    )
                else:
                    cursor.execute("SELECT migration_name FROM migrations ORDER BY id")
            results = cursor.fetchall()
            return [row["migration_name"] if isinstance(row, dict) else row[0] for row in results]
    except Exception as e:
        print(f"Error getting applied migrations: {e}")
        return []


def record_migration(connection, migration_name, status="success", execution_time=0, error_message=None):
    """Record a migration in the migrations table (columns chosen from what exists)."""
    try:
        # Ensure columns exist before opening a cursor (avoids nested cursor + stale metadata).
        create_migrations_table(connection)
        with connection.cursor() as cursor:
            cols = _migrations_columns(cursor)

            fields = ["migration_name"]
            values = [migration_name]
            placeholders = ["%s"]

            if "status" in cols:
                fields.append("status")
                values.append(status)
                placeholders.append("%s")
            if "execution_time_ms" in cols:
                fields.append("execution_time_ms")
                values.append(execution_time)
                placeholders.append("%s")
            if "error_message" in cols:
                fields.append("error_message")
                values.append(error_message)
                placeholders.append("%s")
            if "applied_by" in cols:
                fields.append("applied_by")
                values.append("system")
                placeholders.append("%s")

            updates = []
            if "status" in cols:
                updates.append("status = VALUES(status)")
            if "execution_time_ms" in cols:
                updates.append("execution_time_ms = VALUES(execution_time_ms)")
            if "error_message" in cols:
                updates.append("error_message = VALUES(error_message)")
            if "applied_at" in cols:
                updates.append("applied_at = CURRENT_TIMESTAMP")

            if not updates:
                sql = (
                    f"INSERT INTO migrations ({', '.join(fields)}) VALUES ({', '.join(placeholders)}) "
                    "ON DUPLICATE KEY UPDATE migration_name = VALUES(migration_name)"
                )
            else:
                sql = (
                    f"INSERT INTO migrations ({', '.join(fields)}) VALUES ({', '.join(placeholders)}) "
                    f"ON DUPLICATE KEY UPDATE {', '.join(updates)}"
                )

            cursor.execute(sql, tuple(values))
            connection.commit()
            return True
    except Exception as e:
        print(f"Error recording migration: {e}")
        return False


def run_sql_migration(connection, migration_name, sql_statements):
    """Run SQL migration statements"""
    start_time = datetime.now()
    try:
        with connection.cursor() as cursor:
            for statement in sql_statements:
                if statement.strip():
                    cursor.execute(statement)
            connection.commit()

            execution_time = int((datetime.now() - start_time).total_seconds() * 1000)
            record_migration(connection, migration_name, "success", execution_time)
            print(f"[OK] Migration '{migration_name}' applied successfully ({execution_time}ms)")
            return True
    except Exception as e:
        execution_time = int((datetime.now() - start_time).total_seconds() * 1000)
        error_msg = str(e)
        record_migration(connection, migration_name, "failed", execution_time, error_msg)
        print(f"[FAIL] Migration '{migration_name}' failed: {error_msg}")
        return False


def run_python_migration(connection, migration_func, migration_name):
    """Run Python-based migration function. migration_name is the module stem (e.g. 003_add_theme_columns)."""
    start_time = datetime.now()
    try:
        result = migration_func(connection)
        execution_time = int((datetime.now() - start_time).total_seconds() * 1000)

        if result:
            record_migration(connection, migration_name, "success", execution_time)
            print(f"[OK] Migration '{migration_name}' applied successfully ({execution_time}ms)")
            return True
        record_migration(
            connection, migration_name, "failed", execution_time, "Migration function returned False"
        )
        print(f"[FAIL] Migration '{migration_name}' failed: Migration function returned False")
        return False
    except Exception as e:
        execution_time = int((datetime.now() - start_time).total_seconds() * 1000)
        error_msg = str(e)
        record_migration(connection, migration_name, "failed", execution_time, error_msg)
        print(f"[FAIL] Migration '{migration_name}' failed: {error_msg}")
        return False


def load_migration_files():
    """Load all migration files from the migrations directory"""
    migrations = []
    migrations_dir = os.path.join(os.path.dirname(__file__))

    if not os.path.exists(migrations_dir):
        return migrations

    for filename in sorted(os.listdir(migrations_dir)):
        if filename.endswith(".py") and filename not in (
            "__init__.py",
            "migration_manager.py",
            "create_migration.py",
        ):
            migration_name = filename[:-3]
            migrations.append(
                {"name": migration_name, "file": filename, "path": os.path.join(migrations_dir, filename)}
            )

    return migrations


def run_all_migrations():
    """Run all pending migrations automatically"""
    connection = get_db_connection()
    if not connection:
        print("[FAIL] Failed to connect to database")
        return False

    try:
        if not create_migrations_table(connection):
            print("[FAIL] Failed to create migrations table")
            return False

        applied_migrations = set(get_applied_migrations(connection))
        migration_files = load_migration_files()

        if not migration_files:
            print("[DB] No migration files found.")
            return True

        pending = [m for m in migration_files if m["name"] not in applied_migrations]
        skipped_count = len(migration_files) - len(pending)

        if not pending:
            print(
                f"[DB] Migrations up to date "
                f"({skipped_count} applied, {len(migration_files)} files)."
            )
            return True

        print("=" * 60)
        print("Running Database Migrations...")
        print("=" * 60)
        print(
            f"Pending: {len(pending)}  |  Already applied: {skipped_count}  |  "
            f"Files: {len(migration_files)}"
        )

        success_count = 0
        failed_count = 0

        for migration in pending:
            migration_name = migration["name"]
            print(f"\n>> Running migration: {migration_name}")

            try:
                import importlib.util

                spec = importlib.util.spec_from_file_location(migration_name, migration["path"])
                migration_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(migration_module)

                if hasattr(migration_module, "up"):
                    sql_statements = migration_module.up()
                    if isinstance(sql_statements, str):
                        sql_statements = [sql_statements]
                    if run_sql_migration(connection, migration_name, sql_statements):
                        success_count += 1
                    else:
                        failed_count += 1
                elif hasattr(migration_module, "migrate"):
                    if run_python_migration(connection, migration_module.migrate, migration_name):
                        success_count += 1
                    else:
                        failed_count += 1
                else:
                    print(f"[FAIL] Migration '{migration_name}' has no 'up' or 'migrate' function")
                    failed_count += 1

            except Exception as e:
                print(f"[FAIL] Error loading migration '{migration_name}': {e}")
                failed_count += 1

        print("\n" + "=" * 60)
        print("Migration Summary:")
        print(f"  Success: {success_count}")
        print(f"  Failed: {failed_count}")
        print("=" * 60)

        return failed_count == 0

    except Exception as e:
        print(f"[FAIL] Error running migrations: {e}")
        import traceback

        traceback.print_exc()
        return False
    finally:
        if connection:
            try:
                connection.close()
            except Exception:
                pass


if __name__ == "__main__":
    run_all_migrations()
