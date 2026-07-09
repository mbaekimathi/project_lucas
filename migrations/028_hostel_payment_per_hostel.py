"""
Migration: per-hostel payment settings (account + allowed modes per hostel).
"""


def migrate(connection):
    with connection.cursor() as cursor:
        cursor.execute("SHOW TABLES LIKE 'hostel_payment_settings'")
        has_table = cursor.fetchone()
        if has_table:
            cursor.execute("SHOW COLUMNS FROM hostel_payment_settings LIKE 'hostel_id'")
            if not cursor.fetchone():
                cursor.execute("DROP TABLE hostel_payment_settings")
                has_table = None
        if not has_table:
            cursor.execute("""
                CREATE TABLE hostel_payment_settings (
                    hostel_id INT NOT NULL PRIMARY KEY,
                    finance_account_id INT NOT NULL,
                    allow_mpesa TINYINT(1) NOT NULL DEFAULT 0,
                    allow_cash TINYINT(1) NOT NULL DEFAULT 0,
                    allow_cheque TINYINT(1) NOT NULL DEFAULT 0,
                    allow_bank TINYINT(1) NOT NULL DEFAULT 0,
                    updated_by INT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX idx_hps_account (finance_account_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
    connection.commit()
    return True
