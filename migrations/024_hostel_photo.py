"""
Migration: hostel photo for warden registration.
"""


def migrate(connection):
    with connection.cursor() as cursor:
        cursor.execute("SHOW COLUMNS FROM hostels LIKE 'photo_path'")
        if not cursor.fetchone():
            cursor.execute("""
                ALTER TABLE hostels
                ADD COLUMN photo_path VARCHAR(500) NULL
                AFTER status
            """)
    connection.commit()
    return True
