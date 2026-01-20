# Database Migration System

## Overview

This migration system automatically updates your database schema when code is deployed to cPanel. Migrations run automatically on:
- Application startup (via `passenger_wsgi.py`)
- Manual deployment (via `deploy.sh`)
- Local development (when running `app.py`)

## How It Works

1. **Migration Tracking**: A `migrations` table tracks which migrations have been applied
2. **Automatic Execution**: Migrations run automatically when the app starts
3. **Safe Execution**: Each migration is tracked and won't run twice
4. **Error Handling**: Failed migrations are logged and can be retried

## Creating a New Migration

### Step 1: Create Migration File

Create a new file in the `migrations/` folder with a numbered name:

```
migrations/002_add_new_column.py
migrations/003_create_new_table.py
```

### Step 2: Write Migration Code

#### Option A: SQL Migration (Recommended)

```python
"""
Migration: Add new column to students table
Date: 2025-01-XX
"""

def up():
    """SQL statements to run"""
    return [
        "ALTER TABLE students ADD COLUMN new_field VARCHAR(255) AFTER existing_field",
        "CREATE INDEX idx_new_field ON students(new_field)"
    ]
```

#### Option B: Python Migration (For Complex Logic)

```python
"""
Migration: Complex data migration
Date: 2025-01-XX
"""

def migrate(connection):
    """Python function to run migration"""
    try:
        with connection.cursor() as cursor:
            # Your migration logic here
            cursor.execute("ALTER TABLE students ADD COLUMN new_field VARCHAR(255)")
            connection.commit()
            return True
    except Exception as e:
        print(f"Migration error: {e}")
        return False
```

## Migration Naming Convention

- Use numbers: `001_`, `002_`, `003_`, etc.
- Use descriptive names: `001_create_backup_tables.py`
- Always increment the number for new migrations

## Example Migrations

### Example 1: Add a Column

```python
# migrations/002_add_email_to_students.py
def up():
    return [
        "ALTER TABLE students ADD COLUMN email VARCHAR(255) AFTER full_name",
        "CREATE INDEX idx_email ON students(email)"
    ]
```

### Example 2: Create a Table

```python
# migrations/003_create_notifications_table.py
def up():
    return [
        """
        CREATE TABLE IF NOT EXISTS notifications (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            message TEXT NOT NULL,
            read BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_user_id (user_id),
            INDEX idx_read (read)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """
    ]
```

### Example 3: Data Migration

```python
# migrations/004_update_student_status.py
def migrate(connection):
    try:
        with connection.cursor() as cursor:
            # Update all pending students to in_session
            cursor.execute("""
                UPDATE students 
                SET status = 'in session' 
                WHERE status = 'pending approval' 
                AND created_at < DATE_SUB(NOW(), INTERVAL 30 DAY)
            """)
            connection.commit()
            return True
    except Exception as e:
        print(f"Error: {e}")
        return False
```

## Checking Migration Status

### View Applied Migrations

The system automatically tracks migrations in the `migrations` table. You can check:

```sql
SELECT * FROM migrations ORDER BY applied_at DESC;
```

### Check Migration Status in Code

```python
from migrations.migration_manager import get_applied_migrations, get_db_connection

connection = get_db_connection()
applied = get_applied_migrations(connection)
print(f"Applied migrations: {applied}")
```

## Manual Migration Execution

### Run Migrations Manually

```bash
# Via Python
python3 -c "from migrations.migration_manager import run_all_migrations; run_all_migrations()"

# Or via deploy script
./deploy.sh
```

## Best Practices

1. **Always Test Locally**: Test migrations on a local copy first
2. **Backup First**: Always backup database before running migrations
3. **Idempotent**: Make migrations safe to run multiple times (use `IF NOT EXISTS`, etc.)
4. **One Change Per Migration**: Keep migrations focused on one change
5. **Document Changes**: Add comments explaining what the migration does
6. **Number Sequentially**: Never skip numbers or reuse them

## Troubleshooting

### Migration Failed

1. Check the `migrations` table for error details:
   ```sql
   SELECT * FROM migrations WHERE status = 'failed';
   ```

2. Fix the migration file
3. Delete the failed record:
   ```sql
   DELETE FROM migrations WHERE migration_name = 'failed_migration_name';
   ```
4. Re-run migrations

### Migration Not Running

1. Check that the file is in `migrations/` folder
2. Verify file naming: `001_name.py` (not `001_name.sql`)
3. Check that migration has `up()` or `migrate()` function
4. Check application logs for errors

### Rollback

The current system doesn't support automatic rollback. To rollback:

1. Create a new migration that reverses the changes
2. Or manually run SQL to undo changes
3. Remove the migration record from `migrations` table

## Integration Points

Migrations run automatically at:

1. **Application Startup** (`passenger_wsgi.py`):
   - Runs when Passenger loads the app
   - Runs on every app restart

2. **Deployment Script** (`deploy.sh`):
   - Runs after `git pull`
   - Runs before restarting Passenger

3. **Local Development** (`app.py`):
   - Runs when starting the Flask dev server

## Migration Files Included

- `001_create_backup_tables.py` - Creates backup_settings and backup_history tables

## Next Steps

When you need to add database changes:

1. Create a new migration file in `migrations/`
2. Write the SQL or Python code
3. Commit and push to GitHub
4. Deploy to cPanel (migrations run automatically)

The system will automatically detect and run the new migration!








