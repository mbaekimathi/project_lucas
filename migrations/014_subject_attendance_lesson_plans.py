"""
Migration: optional lesson plans linked to subject attendance sessions.
"""


def migrate(connection):
    with connection.cursor() as cursor:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS subject_attendance_lesson_plans (
                id INT AUTO_INCREMENT PRIMARY KEY,
                academic_level_id INT NOT NULL,
                subject_id INT NOT NULL,
                term_id INT NOT NULL,
                session_date DATE NOT NULL,
                strand TEXT NULL,
                substrand TEXT NULL,
                lesson_learning_outcomes TEXT NULL,
                key_inquiry_questions TEXT NULL,
                core_competencies TEXT NULL,
                lesson_values TEXT NULL,
                pcis TEXT NULL,
                learning_resources TEXT NULL,
                organization_of_learning TEXT NULL,
                introduction TEXT NULL,
                lesson_development TEXT NULL,
                recorded_by_employee_id INT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                UNIQUE KEY uniq_attendance_lesson_plan (
                    academic_level_id, subject_id, term_id, session_date
                ),
                INDEX idx_att_lesson_plan_date (session_date),
                INDEX idx_att_lesson_plan_term (term_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
    connection.commit()
    return True
