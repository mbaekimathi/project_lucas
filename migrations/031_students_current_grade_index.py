"""
Migration: index students.current_grade for class lists / marks filters.
Date: 2026-07-22
"""


def migrate(connection):
    with connection.cursor() as cursor:
        cursor.execute("SHOW TABLES LIKE 'students'")
        if not cursor.fetchone():
            return True

        cursor.execute("SHOW COLUMNS FROM students LIKE 'current_grade'")
        if not cursor.fetchone():
            return True

        cursor.execute("SHOW INDEX FROM students WHERE Key_name = 'idx_students_current_grade'")
        if cursor.fetchone():
            return True

        cursor.execute(
            "CREATE INDEX idx_students_current_grade ON students (current_grade)"
        )

    connection.commit()
    return True
