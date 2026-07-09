"""
Migration: cancel legacy unpaid hostel bookings (status only changes on payment).
"""


def migrate(connection):
    with connection.cursor() as cursor:
        cursor.execute(
            """
            UPDATE student_hostel_bookings
            SET status = 'cancelled'
            WHERE status = 'pending_deposit'
            """
        )
    connection.commit()
    return True
