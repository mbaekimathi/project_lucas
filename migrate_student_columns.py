#!/usr/bin/env python3
"""
Migration script to add student category and sponsor columns to the students table.
Run this script to update your database with the new columns.
"""

import pymysql
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Function to detect if running on hosted server
def is_hosted():
    """Check if the application is running on the hosted server"""
    # Check if we're in the production path
    current_path = os.path.abspath(os.getcwd())
    if '/home1/projectl/project_lucas' in current_path or '\\home1\\projectl\\project_lucas' in current_path:
        return True
    
    # Check for environment variable that indicates hosting
    if os.environ.get('IS_HOSTED', '').lower() in ['true', '1', 'yes']:
        return True
    
    # Check if DB_HOST is set to something other than localhost (indicates hosted)
    db_host = os.environ.get('DB_HOST', 'localhost')
    if db_host != 'localhost' and db_host != '127.0.0.1':
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

def check_column_exists(cursor, table_name, column_name):
    """Check if a column exists in a table"""
    try:
        cursor.execute("""
            SELECT COUNT(*) as count 
            FROM information_schema.COLUMNS 
            WHERE TABLE_SCHEMA = DATABASE() 
            AND TABLE_NAME = %s
            AND COLUMN_NAME = %s
        """, (table_name, column_name))
        result = cursor.fetchone()
        return result and result.get('count', 0) > 0
    except Exception as e:
        print(f"Error checking column {column_name}: {e}")
        return False

def add_column_if_not_exists(cursor, table_name, column_name, column_definition, after_column=None):
    """Add a column to a table if it doesn't exist"""
    if check_column_exists(cursor, table_name, column_name):
        print(f"[OK] Column '{column_name}' already exists in '{table_name}' table")
        return True
    
    try:
        if after_column:
            sql = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_definition} AFTER {after_column}"
        else:
            sql = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_definition}"
        
        cursor.execute(sql)
        print(f"[OK] Added column '{column_name}' to '{table_name}' table")
        return True
    except Exception as e:
        print(f"[ERROR] Error adding column '{column_name}': {e}")
        return False

def migrate_student_columns():
    """Add student category and sponsor columns to students table"""
    print("=" * 60)
    print("Student Table Migration Script")
    print("Adding student_category, sponsor_name, sponsor_phone, sponsor_email columns")
    print("=" * 60)
    
    try:
        # Connect to database
        connection = pymysql.connect(**DB_CONFIG)
        print(f"[OK] Connected to database: {DB_CONFIG['database']}")
        
        with connection.cursor() as cursor:
            # Check if students table exists
            cursor.execute("""
                SELECT COUNT(*) as count 
                FROM information_schema.TABLES 
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_NAME = 'students'
            """)
            result = cursor.fetchone()
            
            if not result or result.get('count', 0) == 0:
                print("[ERROR] 'students' table does not exist!")
                print("Please run the database initialization first.")
                return False
            
            print("[OK] 'students' table found")
            print()
            
            # Add student_category column
            print("1. Adding 'student_category' column...")
            add_column_if_not_exists(
                cursor, 
                'students', 
                'student_category', 
                'VARCHAR(50) NULL',
                'special_needs'
            )
            
            # Add sponsor_name column
            print("2. Adding 'sponsor_name' column...")
            add_column_if_not_exists(
                cursor, 
                'students', 
                'sponsor_name', 
                'VARCHAR(255) NULL',
                'student_category'
            )
            
            # Add sponsor_phone column
            print("3. Adding 'sponsor_phone' column...")
            add_column_if_not_exists(
                cursor, 
                'students', 
                'sponsor_phone', 
                'VARCHAR(50) NULL',
                'sponsor_name'
            )
            
            # Add sponsor_email column
            print("4. Adding 'sponsor_email' column...")
            add_column_if_not_exists(
                cursor, 
                'students', 
                'sponsor_email', 
                'VARCHAR(255) NULL',
                'sponsor_phone'
            )
            
            # Commit changes
            connection.commit()
            print()
            print("=" * 60)
            print("[OK] Migration completed successfully!")
            print("=" * 60)
            return True
            
    except pymysql.err.OperationalError as e:
        if e.args[0] == 1049:  # Unknown database
            print(f"[ERROR] Database '{DB_CONFIG['database']}' does not exist!")
            print("Please create the database first or check your .env file.")
        else:
            print(f"[ERROR] Database connection error: {e}")
        return False
    except Exception as e:
        print(f"[ERROR] Migration error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if 'connection' in locals() and connection:
            connection.close()
            print("[OK] Database connection closed")

if __name__ == '__main__':
    print()
    success = migrate_student_columns()
    print()
    if success:
        print("You can now use the admission form with student category and sponsor fields.")
    else:
        print("Migration failed. Please check the errors above and try again.")
    print()

