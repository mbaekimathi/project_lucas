"""
Migration: Add profile_image column to students table for student photos.
"""


def check_column_exists(cursor, table_name, column_name):
    try:
        cursor.execute(
            """
            SELECT COUNT(*) as count
            FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = %s
              AND COLUMN_NAME = %s
            """,
            (table_name, column_name),
        )
        result = cursor.fetchone()
        return result and (result.get('count', 0) if isinstance(result, dict) else result[0]) > 0
    except Exception:
        return False


def migrate(connection):
    with connection.cursor() as cursor:
        if check_column_exists(cursor, 'students', 'profile_image'):
            return True
        try:
            cursor.execute(
                """
                ALTER TABLE students
                ADD COLUMN profile_image VARCHAR(500) NULL
                AFTER special_needs
                """
            )
            return True
        except Exception:
            return False
