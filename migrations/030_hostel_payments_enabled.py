"""
Migration: per-hostel payments on/off toggle and nullable finance account when payments off.
"""


def migrate(connection):
    with connection.cursor() as cursor:
        cursor.execute("SHOW TABLES LIKE 'hostel_payment_settings'")
        if not cursor.fetchone():
            return True

        cursor.execute("SHOW COLUMNS FROM hostel_payment_settings LIKE 'payments_enabled'")
        if not cursor.fetchone():
            cursor.execute(
                "ALTER TABLE hostel_payment_settings "
                "ADD COLUMN payments_enabled TINYINT(1) NOT NULL DEFAULT 1"
            )

        cursor.execute("SHOW COLUMNS FROM hostel_payment_settings LIKE 'finance_account_id'")
        col = cursor.fetchone()
        if col:
            cursor.execute("SHOW COLUMNS FROM hostel_payment_settings")
            rows = cursor.fetchall() or []
            nullable = True
            for r in rows:
                name = r.get('Field') if isinstance(r, dict) else r[0]
                if name == 'finance_account_id':
                    null_flag = r.get('Null') if isinstance(r, dict) else r[2]
                    nullable = (null_flag or '').upper() == 'YES'
                    break
            if not nullable:
                cursor.execute(
                    "ALTER TABLE hostel_payment_settings "
                    "MODIFY COLUMN finance_account_id INT NULL"
                )

    connection.commit()
    return True
