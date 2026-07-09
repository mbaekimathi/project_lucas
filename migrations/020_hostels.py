"""
Migration: school hostels and hostel rooms (warden portal).
"""


def migrate(connection):
    with connection.cursor() as cursor:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS hostels (
                id INT AUTO_INCREMENT PRIMARY KEY,
                category VARCHAR(80) NOT NULL,
                name VARCHAR(200) NOT NULL,
                description TEXT NULL,
                location VARCHAR(255) NOT NULL,
                room_count INT NOT NULL DEFAULT 0,
                created_by INT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_hostels_category (category),
                INDEX idx_hostels_name (name)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS hostel_rooms (
                id INT AUTO_INCREMENT PRIMARY KEY,
                hostel_id INT NOT NULL,
                reference_number VARCHAR(80) NOT NULL,
                price DECIMAL(12,2) NOT NULL DEFAULT 0,
                sort_order INT NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE KEY uk_hostel_room_ref (hostel_id, reference_number),
                INDEX idx_hostel_rooms_hostel (hostel_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
    connection.commit()
    return True
