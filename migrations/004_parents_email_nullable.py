"""
Migration: Allow NULL values in parents.email column
Consolidated from migrate_parents_email.py
"""

def migrate(connection):
    """Make parents.email column nullable"""
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT IS_NULLABLE 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = DATABASE() 
            AND TABLE_NAME = 'parents' 
            AND COLUMN_NAME = 'email'
        """)
        result = cursor.fetchone()
        if result:
            is_nullable = result.get('IS_NULLABLE', 'NO') if isinstance(result, dict) else result[0]
            if is_nullable == 'NO':
                cursor.execute("ALTER TABLE parents MODIFY COLUMN email VARCHAR(255) NULL")
    connection.commit()
    return True
