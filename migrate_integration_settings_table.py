"""
One-off migration: create integration_settings table if it doesn't exist.
Run once: python migrate_integration_settings_table.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import get_db_connection

def migrate():
    conn = get_db_connection()
    if not conn:
        print("Could not connect to database.")
        return False
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS integration_settings (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    integration_type VARCHAR(50) NOT NULL,
                    settings_json TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    UNIQUE KEY unique_integration_type (integration_type)
                )
            """)
            for itype in ('whatsapp', 'email', 'sms'):
                try:
                    cursor.execute(
                        "INSERT IGNORE INTO integration_settings (integration_type, settings_json) VALUES (%s, %s)",
                        (itype, '{}')
                    )
                except Exception:
                    pass
        conn.commit()
        print("integration_settings table created/verified successfully.")
        return True
    except Exception as e:
        print(f"Migration failed: {e}")
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
