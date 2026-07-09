"""
Migration: occupants per hostel room.
"""


def migrate(connection):
    with connection.cursor() as cursor:
        cursor.execute("SHOW COLUMNS FROM hostel_rooms LIKE 'occupant_count'")
        if not cursor.fetchone():
            cursor.execute("""
                ALTER TABLE hostel_rooms
                ADD COLUMN occupant_count INT NOT NULL DEFAULT 0
                AFTER price
            """)
    connection.commit()
    return True
