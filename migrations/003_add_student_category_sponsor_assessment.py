"""
Migration: Add student_category, sponsor columns, and assessment_number to students table
Consolidated from migrate_student_columns.py
"""

def check_column_exists(cursor, table_name, column_name):
    """Check if a column exists in a table"""
    try:
        cursor.execute("""
            SELECT COUNT(*) as count 
            FROM information_schema.COLUMNS 
            WHERE TABLE_SCHEMA = DATABASE() 
            AND TABLE_NAME = %s
            AND COLUMN_NAME = %s
        """, (table_name, column_name))
        result = cursor.fetchone()
        return result and (result.get('count', 0) if isinstance(result, dict) else result[0]) > 0
    except Exception:
        return False

def add_column_if_not_exists(cursor, table_name, column_name, definition, after_column=None):
    """Add column to table if it doesn't exist"""
    if check_column_exists(cursor, table_name, column_name):
        return True
    try:
        if after_column:
            cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition} AFTER {after_column}")
        else:
            cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}")
        return True
    except Exception:
        return False

def migrate(connection):
    """Add student category, sponsor, and assessment_number columns"""
    with connection.cursor() as cursor:
        add_column_if_not_exists(cursor, 'students', 'student_category', 'VARCHAR(50) NULL', 'special_needs')
        add_column_if_not_exists(cursor, 'students', 'sponsor_name', 'VARCHAR(255) NULL', 'student_category')
        add_column_if_not_exists(cursor, 'students', 'sponsor_phone', 'VARCHAR(50) NULL', 'sponsor_name')
        add_column_if_not_exists(cursor, 'students', 'sponsor_email', 'VARCHAR(255) NULL', 'sponsor_phone')
        add_column_if_not_exists(cursor, 'students', 'assessment_number', 'VARCHAR(100) NULL', 'previous_school')
    connection.commit()
    return True
