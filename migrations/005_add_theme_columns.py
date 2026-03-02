"""
Migration: Add theme/color columns to school_settings
"""

def migrate(connection):
    """Add primary_color, secondary_color, accent_color, font_family to school_settings"""
    columns = [
        ('primary_color', "VARCHAR(20) DEFAULT '#800020'", 'project_name'),
        ('secondary_color', "VARCHAR(20) DEFAULT '#A00030'", 'primary_color'),
        ('accent_color', "VARCHAR(20) DEFAULT '#5C0014'", 'secondary_color'),
        ('font_family', "VARCHAR(50) DEFAULT 'Inter'", 'accent_color'),
    ]
    with connection.cursor() as cursor:
        for col_name, col_def, after_col in columns:
            cursor.execute("""
                SELECT COUNT(*) as c FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'school_settings' AND COLUMN_NAME = %s
            """, (col_name,))
            if (cursor.fetchone() or {}).get('c', 0) == 0:
                cursor.execute(f"ALTER TABLE school_settings ADD COLUMN {col_name} {col_def} AFTER {after_col}")
    connection.commit()
    return True
