"""
Migration: Student fingerprint templates for biometric attendance and other modules.
"""


def migrate(connection):
    with connection.cursor() as cursor:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS student_fingerprints (
                id INT AUTO_INCREMENT PRIMARY KEY,
                student_id VARCHAR(20) CHARACTER SET latin1 COLLATE latin1_swedish_ci NOT NULL,
                finger_code VARCHAR(32) NOT NULL,
                template_base64 LONGTEXT NOT NULL,
                template_format VARCHAR(50) NOT NULL DEFAULT 'binary_v1',
                template_hash CHAR(64) NULL COMMENT 'SHA-256 hex of decoded template for quick lookup',
                quality_score TINYINT UNSIGNED NULL,
                device_id VARCHAR(120) NULL,
                enrolled_by_employee_id INT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                UNIQUE KEY uk_student_finger (student_id, finger_code),
                INDEX idx_template_hash (template_hash),
                INDEX idx_student_id (student_id),
                FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
    connection.commit()
    return True
