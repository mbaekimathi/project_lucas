"""
Migration: hostel payment plan — full vs installments, reservation %, installment schedule.
"""


def migrate(connection):
    with connection.cursor() as cursor:
        cursor.execute("SHOW TABLES LIKE 'hostel_payment_settings'")
        if not cursor.fetchone():
            return True

        cols = [
            ("allow_full_payment", "TINYINT(1) NOT NULL DEFAULT 1"),
            ("allow_installment_payment", "TINYINT(1) NOT NULL DEFAULT 0"),
            ("allow_reservation", "TINYINT(1) NOT NULL DEFAULT 1"),
            ("reservation_pct", "DECIMAL(5,2) NOT NULL DEFAULT 25.00"),
            ("installment_count", "INT NOT NULL DEFAULT 2"),
            ("installment_pcts_json", "TEXT NULL"),
        ]
        for col, definition in cols:
            cursor.execute(f"SHOW COLUMNS FROM hostel_payment_settings LIKE '{col}'")
            if not cursor.fetchone():
                cursor.execute(
                    f"ALTER TABLE hostel_payment_settings ADD COLUMN {col} {definition}"
                )

        cursor.execute("SHOW TABLES LIKE 'student_hostel_bookings'")
        if cursor.fetchone():
            booking_cols = [
                ("amount_paid", "DECIMAL(12,2) NOT NULL DEFAULT 0"),
                ("installments_paid", "INT NOT NULL DEFAULT 0"),
                ("installment_plan_json", "TEXT NULL"),
            ]
            for col, definition in booking_cols:
                cursor.execute(f"SHOW COLUMNS FROM student_hostel_bookings LIKE '{col}'")
                if not cursor.fetchone():
                    cursor.execute(
                        f"ALTER TABLE student_hostel_bookings ADD COLUMN {col} {definition}"
                    )

    connection.commit()
    return True
