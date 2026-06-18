"""
Migration: scope lesson plans per teacher (teacher_id + unique key).
"""


def migrate(connection):
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT COLUMN_NAME FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = 'subject_attendance_lesson_plans'
              AND COLUMN_NAME = 'teacher_id'
        """)
        if not cursor.fetchone():
            cursor.execute("""
                ALTER TABLE subject_attendance_lesson_plans
                ADD COLUMN teacher_id INT NULL AFTER subject_id
            """)
        cursor.execute("""
            UPDATE subject_attendance_lesson_plans
            SET teacher_id = recorded_by_employee_id
            WHERE teacher_id IS NULL AND recorded_by_employee_id IS NOT NULL
        """)
        try:
            cursor.execute("ALTER TABLE subject_attendance_lesson_plans DROP INDEX uniq_attendance_lesson_plan")
        except Exception:
            pass
        try:
            cursor.execute("""
                ALTER TABLE subject_attendance_lesson_plans
                ADD UNIQUE KEY uniq_attendance_lesson_plan_teacher (
                    academic_level_id, subject_id, term_id, session_date, teacher_id
                )
            """)
        except Exception:
            pass
    connection.commit()
    return True
