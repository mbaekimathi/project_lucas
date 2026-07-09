"""
Migration: active/suspended status for hostels.
"""


def migrate(connection):
    with connection.cursor() as cursor:
        cursor.execute("SHOW COLUMNS FROM hostels LIKE 'status'")
        if not cursor.fetchone():
            cursor.execute("""
                ALTER TABLE hostels
                ADD COLUMN status ENUM('active', 'suspended') NOT NULL DEFAULT 'active'
                AFTER occupant_count
            """)
    connection.commit()
    return True
