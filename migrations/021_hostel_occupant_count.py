"""
Migration: number of occupants per registered hostel.
"""


def migrate(connection):
    with connection.cursor() as cursor:
        cursor.execute("SHOW COLUMNS FROM hostels LIKE 'occupant_count'")
        if not cursor.fetchone():
            cursor.execute("""
                ALTER TABLE hostels
                ADD COLUMN occupant_count INT NOT NULL DEFAULT 0
                AFTER room_count
            """)
    connection.commit()
    return True
