"""
Migration: Add student ID generation settings to school_settings
"""

def migrate(connection):
    """Add student_id_prefix and student_id_digits to school_settings"""
    columns = [
        ('student_id_prefix', "VARCHAR(10) DEFAULT 'STU'", 'project_name'),
        ('student_id_digits', "INT DEFAULT 3", 'student_id_prefix'),
    ]
    with connection.cursor() as cursor:
        for col_name, col_def, after_col in columns:
            cursor.execute("""
                SELECT COUNT(*) as c FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'school_settings' AND COLUMN_NAME = %s
            """, (col_name,))
            result = cursor.fetchone()
            count = result.get('c', 0) if isinstance(result, dict) else (result[0] if result else 0)
            if count == 0:
                cursor.execute(f"ALTER TABLE school_settings ADD COLUMN {col_name} {col_def} AFTER {after_col}")
    connection.commit()
    return True
