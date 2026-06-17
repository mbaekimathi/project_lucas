"""
Migration: per-exam frozen settings (grades, totals, combinations) when global settings change.
"""


def migrate(connection):
    with connection.cursor() as cursor:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS exam_context_settings (
                id INT AUTO_INCREMENT PRIMARY KEY,
                exam_name VARCHAR(255) NOT NULL,
                academic_year_id INT NOT NULL,
                term_id INT NOT NULL,
                academic_level_id INT NOT NULL,
                settings_json LONGTEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                UNIQUE KEY uniq_exam_context (
                    exam_name, academic_year_id, term_id, academic_level_id
                ),
                INDEX idx_exam_ctx_level (academic_level_id),
                INDEX idx_exam_ctx_year_term (academic_year_id, term_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
    connection.commit()
    return True
