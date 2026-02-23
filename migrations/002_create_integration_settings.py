"""
Migration: Create integration_settings table (WhatsApp, Email, SMS)
Run on deploy so schema is applied after git pull.
"""

def up():
    """SQL statements to create integration_settings table and placeholder rows"""
    return [
        """
        CREATE TABLE IF NOT EXISTS integration_settings (
            id INT AUTO_INCREMENT PRIMARY KEY,
            integration_type VARCHAR(50) NOT NULL,
            settings_json TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            UNIQUE KEY unique_integration_type (integration_type)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """,
        "INSERT IGNORE INTO integration_settings (integration_type, settings_json) VALUES ('whatsapp', '{}')",
        "INSERT IGNORE INTO integration_settings (integration_type, settings_json) VALUES ('email', '{}')",
        "INSERT IGNORE INTO integration_settings (integration_type, settings_json) VALUES ('sms', '{}')",
    ]
