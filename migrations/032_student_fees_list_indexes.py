"""
Migration: indexes for student fees list / payment lookups.
Date: 2026-07-22
"""


def _ensure_index(cursor, table, index_name, ddl):
    cursor.execute(f"SHOW TABLES LIKE '{table}'")
    if not cursor.fetchone():
        return
    cursor.execute(f"SHOW INDEX FROM `{table}` WHERE Key_name = %s", (index_name,))
    if cursor.fetchone():
        return
    cursor.execute(ddl)


def migrate(connection):
    with connection.cursor() as cursor:
        _ensure_index(
            cursor,
            "students",
            "idx_students_status",
            "CREATE INDEX idx_students_status ON students (status)",
        )
        _ensure_index(
            cursor,
            "students",
            "idx_students_status_grade",
            "CREATE INDEX idx_students_status_grade ON students (status, current_grade)",
        )
        _ensure_index(
            cursor,
            "student_payments",
            "idx_student_payments_student_fs",
            "CREATE INDEX idx_student_payments_student_fs ON student_payments (student_id, fee_structure_id)",
        )
        _ensure_index(
            cursor,
            "fee_structures",
            "idx_fee_structures_level_status_yt",
            "CREATE INDEX idx_fee_structures_level_status_yt ON fee_structures "
            "(academic_level_id, status, academic_year_id, term_id)",
        )
        _ensure_index(
            cursor,
            "parents",
            "idx_parents_student_id",
            "CREATE INDEX idx_parents_student_id ON parents (student_id)",
        )
    connection.commit()
    return True
