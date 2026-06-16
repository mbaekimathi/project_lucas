"""
Migration: class_teacher_assignments — curriculum coordinator assigns class teachers per level/year.
"""


def migrate(connection):
    with connection.cursor() as cursor:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS class_teacher_assignments (
                id INT AUTO_INCREMENT PRIMARY KEY,
                academic_level_id INT NOT NULL,
                academic_year_id INT NOT NULL,
                teacher_id INT NOT NULL,
                created_by INT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                UNIQUE KEY unique_class_teacher_level_year (academic_level_id, academic_year_id),
                INDEX idx_cta_teacher (teacher_id),
                INDEX idx_cta_year (academic_year_id),
                FOREIGN KEY (academic_level_id) REFERENCES academic_levels(id) ON DELETE CASCADE,
                FOREIGN KEY (academic_year_id) REFERENCES academic_years(id) ON DELETE CASCADE,
                FOREIGN KEY (teacher_id) REFERENCES employees(id) ON DELETE CASCADE,
                FOREIGN KEY (created_by) REFERENCES employees(id) ON DELETE SET NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
    connection.commit()
    return True
