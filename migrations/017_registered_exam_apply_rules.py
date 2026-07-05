"""
Migration: optional student application requirements per registered exam group.
"""


def migrate(connection):
    with connection.cursor() as cursor:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS registered_exam_apply_rules (
                id INT AUTO_INCREMENT PRIMARY KEY,
                exam_name VARCHAR(255) NOT NULL,
                exam_type VARCHAR(100) NOT NULL DEFAULT '',
                academic_year_id INT NOT NULL,
                term_id INT NOT NULL,
                class_attendance_min_pct DECIMAL(5, 2) NULL,
                subject_attendance_min_pct DECIMAL(5, 2) NULL,
                fee_payment_min_pct DECIMAL(5, 2) NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                UNIQUE KEY uniq_exam_apply_rules (exam_name, exam_type, academic_year_id, term_id),
                INDEX idx_rear_year_term (academic_year_id, term_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
    connection.commit()
    return True
