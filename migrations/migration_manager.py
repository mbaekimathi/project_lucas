"""
Database Migration Manager
Automatically runs database migrations on deployment
"""
import pymysql
import os
from datetime import datetime
from app import DB_CONFIG, get_db_connection

def create_migrations_table(connection):
    """Create the migrations tracking table if it doesn't exist, and add missing columns"""
    try:
        with connection.cursor() as cursor:
            # Create table if it doesn't exist
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS migrations (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    migration_name VARCHAR(255) UNIQUE NOT NULL,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    applied_by VARCHAR(255) DEFAULT 'system',
                    execution_time_ms INT,
                    status ENUM('success', 'failed', 'partial') DEFAULT 'success',
                    error_message TEXT,
                    INDEX idx_migration_name (migration_name),
                    INDEX idx_applied_at (applied_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            
            # Check if status column exists, add it if it doesn't
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE()
                AND TABLE_NAME = 'migrations'
                AND COLUMN_NAME = 'status'
            """)
            result = cursor.fetchone()
            status_exists = (result[0] if isinstance(result, (list, tuple)) else result.get('count', 0)) > 0
            
            if not status_exists:
                try:
                    cursor.execute("""
                        ALTER TABLE migrations
                        ADD COLUMN status ENUM('success', 'failed', 'partial') DEFAULT 'success'
                        AFTER execution_time_ms
                    """)
                    print("Added 'status' column to migrations table")
                except Exception as e:
                    print(f"Note: Could not add status column (may already exist): {e}")
            
            # Check if other columns exist and add them if missing
            # Check applied_by first (doesn't depend on other columns)
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE()
                AND TABLE_NAME = 'migrations'
                AND COLUMN_NAME = 'applied_by'
            """)
            result = cursor.fetchone()
            applied_by_exists = (result[0] if isinstance(result, (list, tuple)) else result.get('count', 0)) > 0
            if not applied_by_exists:
                try:
                    cursor.execute("""
                        ALTER TABLE migrations
                        ADD COLUMN applied_by VARCHAR(255) DEFAULT 'system'
                        AFTER applied_at
                    """)
                    print("Added 'applied_by' column to migrations table")
                except Exception as e:
                    print(f"Note: Could not add applied_by column: {e}")
            
            # Check execution_time_ms (doesn't depend on status)
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE()
                AND TABLE_NAME = 'migrations'
                AND COLUMN_NAME = 'execution_time_ms'
            """)
            result = cursor.fetchone()
            execution_time_exists = (result[0] if isinstance(result, (list, tuple)) else result.get('count', 0)) > 0
            if not execution_time_exists:
                try:
                    # Position after applied_by if it exists, otherwise after applied_at
                    position = 'AFTER applied_by' if applied_by_exists else 'AFTER applied_at'
                    cursor.execute(f"""
                        ALTER TABLE migrations
                        ADD COLUMN execution_time_ms INT {position}
                    """)
                    print("Added 'execution_time_ms' column to migrations table")
                except Exception as e:
                    print(f"Note: Could not add execution_time_ms column: {e}")
            
            # Check error_message (depends on status, so check after status is added)
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE()
                AND TABLE_NAME = 'migrations'
                AND COLUMN_NAME = 'error_message'
            """)
            result = cursor.fetchone()
            error_message_exists = (result[0] if isinstance(result, (list, tuple)) else result.get('count', 0)) > 0
            if not error_message_exists:
                try:
                    # Position after status if it exists, otherwise after execution_time_ms
                    if status_exists:
                        position = 'AFTER status'
                    else:
                        position = 'AFTER execution_time_ms' if execution_time_exists else 'AFTER applied_at'
                    cursor.execute(f"""
                        ALTER TABLE migrations
                        ADD COLUMN error_message TEXT {position}
                    """)
                    print("Added 'error_message' column to migrations table")
                except Exception as e:
                    print(f"Note: Could not add error_message column: {e}")
            
            connection.commit()
            return True
    except Exception as e:
        print(f"Error creating migrations table: {e}")
        return False

def get_applied_migrations(connection):
    """Get list of already applied migrations"""
    try:
        with connection.cursor() as cursor:
            # Check if status column exists
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE()
                AND TABLE_NAME = 'migrations'
                AND COLUMN_NAME = 'status'
            """)
            result = cursor.fetchone()
            status_exists = (result[0] if isinstance(result, (list, tuple)) else result.get('count', 0)) > 0
            
            if status_exists:
                cursor.execute("""
                    SELECT migration_name 
                    FROM migrations 
                    WHERE status = 'success'
                    ORDER BY applied_at
                """)
            else:
                # Fallback: get all migrations if status column doesn't exist
                cursor.execute("""
                    SELECT migration_name 
                    FROM migrations 
                    ORDER BY applied_at
                """)
            results = cursor.fetchall()
            return [row['migration_name'] if isinstance(row, dict) else row[0] for row in results]
    except Exception as e:
        print(f"Error getting applied migrations: {e}")
        return []

def record_migration(connection, migration_name, status='success', execution_time=0, error_message=None):
    """Record a migration in the migrations table"""
    try:
        with connection.cursor() as cursor:
            # Check if status column exists
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE()
                AND TABLE_NAME = 'migrations'
                AND COLUMN_NAME = 'status'
            """)
            result = cursor.fetchone()
            status_exists = (result[0] if isinstance(result, (list, tuple)) else result.get('count', 0)) > 0
            
            if status_exists:
                # Use status column if it exists
                cursor.execute("""
                    INSERT INTO migrations (migration_name, status, execution_time_ms, error_message, applied_by)
                    VALUES (%s, %s, %s, %s, 'system')
                    ON DUPLICATE KEY UPDATE
                        status = VALUES(status),
                        execution_time_ms = VALUES(execution_time_ms),
                        error_message = VALUES(error_message),
                        applied_at = CURRENT_TIMESTAMP
                """, (migration_name, status, execution_time, error_message))
            else:
                # Fallback: don't include status column
                cursor.execute("""
                    INSERT INTO migrations (migration_name, execution_time_ms, error_message, applied_by)
                    VALUES (%s, %s, %s, 'system')
                    ON DUPLICATE KEY UPDATE
                        execution_time_ms = VALUES(execution_time_ms),
                        error_message = VALUES(error_message),
                        applied_at = CURRENT_TIMESTAMP
                """, (migration_name, execution_time, error_message))
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
            # Execute each SQL statement
            for statement in sql_statements:
                if statement.strip():
                    cursor.execute(statement)
            connection.commit()
            
            execution_time = int((datetime.now() - start_time).total_seconds() * 1000)
            record_migration(connection, migration_name, 'success', execution_time)
            print(f"✓ Migration '{migration_name}' applied successfully ({execution_time}ms)")
            return True
    except Exception as e:
        execution_time = int((datetime.now() - start_time).total_seconds() * 1000)
        error_msg = str(e)
        record_migration(connection, migration_name, 'failed', execution_time, error_msg)
        print(f"✗ Migration '{migration_name}' failed: {error_msg}")
        return False

def run_python_migration(connection, migration_func):
    """Run Python-based migration function"""
    migration_name = migration_func.__name__
    start_time = datetime.now()
    try:
        result = migration_func(connection)
        execution_time = int((datetime.now() - start_time).total_seconds() * 1000)
        
        if result:
            record_migration(connection, migration_name, 'success', execution_time)
            print(f"✓ Migration '{migration_name}' applied successfully ({execution_time}ms)")
            return True
        else:
            record_migration(connection, migration_name, 'failed', execution_time, 'Migration function returned False')
            print(f"✗ Migration '{migration_name}' failed: Migration function returned False")
            return False
    except Exception as e:
        execution_time = int((datetime.now() - start_time).total_seconds() * 1000)
        error_msg = str(e)
        record_migration(connection, migration_name, 'failed', execution_time, error_msg)
        print(f"✗ Migration '{migration_name}' failed: {error_msg}")
        return False

def load_migration_files():
    """Load all migration files from the migrations directory"""
    migrations = []
    migrations_dir = os.path.join(os.path.dirname(__file__))
    
    if not os.path.exists(migrations_dir):
        return migrations
    
    # Get all Python files in migrations directory (excluding __init__.py)
    for filename in sorted(os.listdir(migrations_dir)):
        if filename.endswith('.py') and filename != '__init__.py' and filename != 'migration_manager.py':
            migration_name = filename[:-3]  # Remove .py extension
            migrations.append({
                'name': migration_name,
                'file': filename,
                'path': os.path.join(migrations_dir, filename)
            })
    
    return migrations

def run_all_migrations():
    """Run all pending migrations automatically"""
    print("=" * 60)
    print("Running Database Migrations...")
    print("=" * 60)
    
    connection = get_db_connection()
    if not connection:
        print("✗ Failed to connect to database")
        return False
    
    try:
        # Create migrations table if it doesn't exist
        if not create_migrations_table(connection):
            print("✗ Failed to create migrations table")
            return False
        
        # Get already applied migrations
        applied_migrations = get_applied_migrations(connection)
        print(f"Found {len(applied_migrations)} already applied migrations")
        
        # Load all migration files
        migration_files = load_migration_files()
        print(f"Found {len(migration_files)} migration files")
        
        if not migration_files:
            print("No migrations to run")
            return True
        
        # Run pending migrations
        pending_count = 0
        success_count = 0
        failed_count = 0
        
        for migration in migration_files:
            migration_name = migration['name']
            
            # Skip if already applied
            if migration_name in applied_migrations:
                print(f"⊘ Migration '{migration_name}' already applied, skipping")
                continue
            
            pending_count += 1
            print(f"\n→ Running migration: {migration_name}")
            
            # Import and run the migration
            try:
                # Import the migration module
                import importlib.util
                spec = importlib.util.spec_from_file_location(migration_name, migration['path'])
                migration_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(migration_module)
                
                # Check if it has a 'up' function (SQL migration) or 'migrate' function (Python migration)
                if hasattr(migration_module, 'up'):
                    # SQL migration
                    sql_statements = migration_module.up()
                    if isinstance(sql_statements, str):
                        sql_statements = [sql_statements]
                    if run_sql_migration(connection, migration_name, sql_statements):
                        success_count += 1
                    else:
                        failed_count += 1
                elif hasattr(migration_module, 'migrate'):
                    # Python migration
                    if run_python_migration(connection, migration_module.migrate):
                        success_count += 1
                    else:
                        failed_count += 1
                else:
                    print(f"✗ Migration '{migration_name}' has no 'up' or 'migrate' function")
                    failed_count += 1
                    
            except Exception as e:
                print(f"✗ Error loading migration '{migration_name}': {e}")
                failed_count += 1
        
        print("\n" + "=" * 60)
        print(f"Migration Summary:")
        print(f"  Pending: {pending_count}")
        print(f"  Success: {success_count}")
        print(f"  Failed: {failed_count}")
        print("=" * 60)
        
        return failed_count == 0
        
    except Exception as e:
        print(f"✗ Error running migrations: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if connection:
            try:
                connection.close()
            except:
                pass

if __name__ == '__main__':
    # Can be run standalone
    run_all_migrations()








