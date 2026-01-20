"""
Migration: Create backup_settings and backup_history tables
Date: 2025-01-XX
"""

def up():
    """SQL statements to create backup tables"""
    return [
        """
        CREATE TABLE IF NOT EXISTS backup_settings (
            id INT AUTO_INCREMENT PRIMARY KEY,
            auto_backup_enabled BOOLEAN DEFAULT FALSE,
            backup_frequency ENUM('daily', 'weekly', 'monthly') DEFAULT 'daily',
            last_backup DATETIME NULL,
            next_backup DATETIME NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            updated_by VARCHAR(255),
            INDEX idx_auto_backup (auto_backup_enabled)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """,
        """
        CREATE TABLE IF NOT EXISTS backup_history (
            id INT AUTO_INCREMENT PRIMARY KEY,
            filename VARCHAR(255) NOT NULL,
            file_path VARCHAR(500),
            file_size BIGINT,
            table_count INT,
            record_count INT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_by VARCHAR(255),
            INDEX idx_created_at (created_at),
            INDEX idx_filename (filename)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
    ]








