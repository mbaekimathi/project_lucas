"""
Migration: Create student_attendance_records table
"""

def migrate(connection):
    """Create student_attendance_records table for tracking daily attendance"""
    with connection.cursor() as cursor:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS student_attendance_records (
                id INT AUTO_INCREMENT PRIMARY KEY,
                student_id VARCHAR(20) NOT NULL,
                attendance_date DATE NOT NULL,
                academic_level_id INT NOT NULL,
                term_id INT NOT NULL,
                present TINYINT(1) NOT NULL DEFAULT 1,
                recorded_by_employee_id INT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE KEY unique_student_date_level_term (student_id, attendance_date, academic_level_id, term_id),
                INDEX idx_student_date (student_id, attendance_date),
                INDEX idx_level_term_date (academic_level_id, term_id, attendance_date),
                FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE,
                FOREIGN KEY (academic_level_id) REFERENCES academic_levels(id) ON DELETE CASCADE,
                FOREIGN KEY (term_id) REFERENCES terms(id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
    connection.commit()
    return True
