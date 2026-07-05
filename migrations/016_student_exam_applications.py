"""
Migration: student exam applications (student portal).
"""


def migrate(connection):
    with connection.cursor() as cursor:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS student_exam_applications (
                id INT AUTO_INCREMENT PRIMARY KEY,
                student_id VARCHAR(64) NOT NULL,
                sitting_key VARCHAR(32) NOT NULL,
                exam_id INT NULL,
                exam_name VARCHAR(255) NOT NULL,
                exam_type VARCHAR(100) NULL,
                academic_year_id INT NULL,
                term_id INT NULL,
                academic_level_id INT NULL,
                year_name VARCHAR(120) NULL,
                term_name VARCHAR(120) NULL,
                exam_date_str VARCHAR(32) NULL,
                notes TEXT NULL,
                status ENUM('pending', 'approved', 'rejected', 'withdrawn') NOT NULL DEFAULT 'pending',
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                reviewed_at TIMESTAMP NULL,
                reviewed_by INT NULL,
                review_notes TEXT NULL,
                UNIQUE KEY uniq_student_exam_sitting (student_id, sitting_key),
                INDEX idx_sea_student (student_id),
                INDEX idx_sea_status (status),
                INDEX idx_sea_applied (applied_at)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
    connection.commit()
    return True
