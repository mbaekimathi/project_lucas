"""
Script to create the school database if it doesn't exist.
Run this script if you encounter database connection errors.
"""
import pymysql
import os

# Database configuration
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_USER = os.getenv('DB_USER', 'root')
DB_PASSWORD = os.getenv('DB_PASSWORD', '')
DB_NAME = os.getenv('DB_NAME', 'school_db')

try:
    # Connect without specifying database
    connection = pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        charset='utf8mb4'
    )
    
    with connection.cursor() as cursor:
        # Create database
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        print(f"✅ Database '{DB_NAME}' created successfully!")
    
    connection.close()
    
    # Now connect to the new database
    connection = pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        charset='utf8mb4'
    )
    
    print(f"✅ Successfully connected to database '{DB_NAME}'!")
    print("🚀 You can now run the Flask application: python app.py")
    connection.close()
    
except pymysql.err.OperationalError as e:
    print(f"❌ Error: {e}")
    print("\nPlease check:")
    print("1. MySQL server is running")
    print("2. Database credentials are correct")
    print("3. User has CREATE DATABASE privileges")
except Exception as e:
    print(f"❌ Unexpected error: {e}")

