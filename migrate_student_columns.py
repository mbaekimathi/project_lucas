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

# Detect if running on localhost or hosted (cPanel)
def is_localhost():
    """Detect if application is running on localhost or hosted environment"""
    # Method 1: Check DEPLOYMENT_ENV environment variable (most reliable - user can force it)
    deployment_env = os.environ.get('DEPLOYMENT_ENV', '').lower()
    if deployment_env in ['production', 'hosted', 'cpanel']:
        print("Environment detection: DEPLOYMENT_ENV set to hosted/cPanel")
        return False
    if deployment_env in ['development', 'local', 'localhost']:
        print("Environment detection: DEPLOYMENT_ENV set to localhost")
        return True
    
    # Method 2: Check if DB_USER is explicitly set in environment
    db_user = os.environ.get('DB_USER', '')
    if db_user and 'projectl' in db_user.lower():
        print(f"Environment detection: DB_USER '{db_user}' indicates hosted/cPanel")
        return False
    if db_user == 'root':
        print(f"Environment detection: DB_USER 'root' indicates localhost")
        return True
    
    # Method 3: Check if DB_NAME is explicitly set in environment
    db_name = os.environ.get('DB_NAME', '')
    if db_name and 'projectl' in db_name.lower():
        print(f"Environment detection: DB_NAME '{db_name}' indicates hosted/cPanel")
        return False
    if db_name == 'modern_school':
        print(f"Environment detection: DB_NAME 'modern_school' indicates localhost")
        return True
    
    # Method 4: Check if DB_PASSWORD is set and matches cPanel password
    db_password = os.environ.get('DB_PASSWORD', '')
    if db_password == 'Itskimathi007':
        print("Environment detection: DB_PASSWORD matches cPanel credentials")
        return False
    
    # Method 5: Check actual network interface IP address
    try:
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(('8.8.8.8', 80))
            local_ip = s.getsockname()[0]
            s.close()
            if local_ip == '127.0.0.1':
                print(f"Environment detection: Local IP {local_ip} indicates localhost")
                return True
        except Exception as e:
            s.close()
    except:
        pass
    
    # Method 6: Check hostname patterns
    try:
        import socket
        hostname = socket.gethostname().lower()
        localhost_indicators = ['localhost', '127.0.0.1', 'desktop', 'laptop', 'pc-', 'computer']
        if any(indicator in hostname for indicator in localhost_indicators):
            print(f"Environment detection: Hostname '{hostname}' indicates localhost")
            return True
        if '.' in hostname and len(hostname.split('.')) > 1:
            print(f"Environment detection: Hostname '{hostname}' looks like a server (hosted)")
            return False
    except:
        pass
    
    # Method 7: Check FLASK_ENV
    flask_env = os.environ.get('FLASK_ENV', '').lower()
    if flask_env == 'development':
        print("Environment detection: FLASK_ENV=development indicates localhost")
        return True
    if flask_env == 'production':
        print("Environment detection: FLASK_ENV=production indicates hosted")
        return False
    
    # Method 8: Default fallback
    import platform
    if platform.system() == 'Windows':
        print("Environment detection: Windows system, defaulting to localhost")
        return True
    
    print("Environment detection: No clear indicators, defaulting to localhost")
    print("  Tip: Set DEPLOYMENT_ENV=production or DEPLOYMENT_ENV=development to override")
    return True

# Database configuration with automatic environment detection
def get_db_config():
    """Get database configuration based on environment (localhost vs hosted)"""
    is_local = is_localhost()
    
    if is_local:
        # Localhost/Development defaults
        defaults = {
            'host': 'localhost',
            'user': 'root',
            'password': '',
            'database': 'modern_school'
        }
    else:
        # cPanel/Hosted defaults
        defaults = {
            'host': 'localhost',  # cPanel usually uses localhost for MySQL
            'user': 'projectl_school',
            'password': 'Itskimathi007',
            'database': 'projectl_school'
        }
    
    # Environment variables always override defaults
    return {
        'host': os.environ.get('DB_HOST', defaults['host']),
        'user': os.environ.get('DB_USER', defaults['user']),
        'password': os.environ.get('DB_PASSWORD', defaults['password']),
        'database': os.environ.get('DB_NAME', defaults['database']),
        'charset': 'utf8mb4',
        'cursorclass': pymysql.cursors.DictCursor
    }

# Initialize database configuration
DB_CONFIG = get_db_config()

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

