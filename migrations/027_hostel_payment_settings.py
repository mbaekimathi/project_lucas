"""
Migration: hostel payment settings (accounts per payment type and allowed methods).
"""


def migrate(connection):
    with connection.cursor() as cursor:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS hostel_payment_settings (
                id INT NOT NULL PRIMARY KEY DEFAULT 1,
                deposit_finance_account_id INT NULL,
                balance_finance_account_id INT NULL,
                full_finance_account_id INT NULL,
                allow_mpesa TINYINT(1) NOT NULL DEFAULT 0,
                allow_cash TINYINT(1) NOT NULL DEFAULT 0,
                allow_cheque TINYINT(1) NOT NULL DEFAULT 0,
                allow_bank TINYINT(1) NOT NULL DEFAULT 0,
                updated_by INT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                CONSTRAINT chk_hostel_payment_settings_singleton CHECK (id = 1)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        cursor.execute(
            "INSERT IGNORE INTO hostel_payment_settings (id) VALUES (1)"
        )
    connection.commit()
    return True
