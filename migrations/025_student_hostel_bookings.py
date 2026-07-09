"""
Migration: student hostel bookings (deposit → reserved, balance → occupied).
"""


def migrate(connection):
    with connection.cursor() as cursor:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS student_hostel_bookings (
                id INT AUTO_INCREMENT PRIMARY KEY,
                student_id VARCHAR(20) NOT NULL,
                hostel_id INT NOT NULL,
                hostel_room_id INT NOT NULL,
                status ENUM('pending_deposit', 'reserved', 'occupied', 'cancelled')
                    NOT NULL DEFAULT 'pending_deposit',
                total_amount DECIMAL(12,2) NOT NULL DEFAULT 0,
                deposit_amount DECIMAL(12,2) NOT NULL DEFAULT 0,
                balance_amount DECIMAL(12,2) NOT NULL DEFAULT 0,
                deposit_paid_at DATETIME NULL,
                balance_paid_at DATETIME NULL,
                deposit_receipt VARCHAR(64) NULL,
                balance_receipt VARCHAR(64) NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_shb_student (student_id),
                INDEX idx_shb_hostel (hostel_id),
                INDEX idx_shb_room (hostel_room_id),
                INDEX idx_shb_status (status)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
    connection.commit()
    return True
