#!/usr/bin/env python3
"""
Migration script to allow NULL values in parents.email column
"""
import pymysql
import os

def is_hosted():
    """Check if running on hosted server"""
    # Check for common hosting indicators
    if os.path.exists('/home'):
        # Check for common hosting paths
        if os.path.exists('/home/projectl_school') or os.path.exists('/home/projectl'):
            return True
    return False

# Database configuration - automatically detect hosted vs local
if is_hosted():
    # Hosted server credentials
    DB_CONFIG = {
        'host': os.environ.get('DB_HOST', 'localhost'),
        'user': os.environ.get('DB_USER', 'projectl_school'),
        'password': os.environ.get('DB_PASSWORD', 'Itskimathi007'),
        'database': os.environ.get('DB_NAME', 'projectl_school'),
        'charset': 'utf8mb4',
        'cursorclass': pymysql.cursors.DictCursor
    }
else:
    # Local development credentials
    DB_CONFIG = {
        'host': os.environ.get('DB_HOST', 'localhost'),
        'user': os.environ.get('DB_USER', 'root'),
        'password': os.environ.get('DB_PASSWORD', ''),
        'database': os.environ.get('DB_NAME', 'modern_school'),
        'charset': 'utf8mb4',
        'cursorclass': pymysql.cursors.DictCursor
    }

def migrate_parents_email():
    """Migrate parents table to allow NULL email"""
    try:
        connection = pymysql.connect(**DB_CONFIG)
        with connection.cursor() as cursor:
            # Check if column exists and is NOT NULL
            cursor.execute("""
                SELECT IS_NULLABLE 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = %s 
                AND TABLE_NAME = 'parents' 
                AND COLUMN_NAME = 'email'
            """, (DB_CONFIG['database'],))
            
            result = cursor.fetchone()
            if result:
                is_nullable = result.get('IS_NULLABLE', 'NO')
                if is_nullable == 'NO':
                    # Column exists and is NOT NULL, modify it
                    cursor.execute("ALTER TABLE parents MODIFY COLUMN email VARCHAR(255) NULL")
                    connection.commit()
                    print("Successfully updated parents.email column to allow NULL values.")
                else:
                    print("parents.email column already allows NULL values.")
            else:
                print("Column 'email' not found in 'parents' table.")
        
        connection.close()
        return True
    except Exception as e:
        print(f"Error migrating parents.email column: {e}")
        return False

if __name__ == '__main__':
    print("Migrating parents.email column to allow NULL values...")
    migrate_parents_email()

