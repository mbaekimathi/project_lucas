"""
Migration: session_slot on student_attendance_records (morning / afternoon / evening).
"""


def migrate(connection):
    with connection.cursor() as cursor:
        try:
            cursor.execute("""
                ALTER TABLE student_attendance_records
                ADD COLUMN session_slot VARCHAR(20) NOT NULL DEFAULT ''
            """)
        except Exception:
            pass
        try:
            cursor.execute("""
                ALTER TABLE student_attendance_records
                DROP INDEX unique_student_date_level_term_subject
            """)
        except Exception:
            pass
        try:
            cursor.execute("""
                ALTER TABLE student_attendance_records
                ADD UNIQUE KEY unique_student_date_level_term_subject_slot (
                    student_id, attendance_date, academic_level_id, term_id, subject_id, session_slot
                )
            """)
        except Exception:
            pass
    connection.commit()
    return True
