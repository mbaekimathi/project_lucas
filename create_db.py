"""
Database initialization script for Modern School
Run this script to create the database and tables
"""
import pymysql
import os
from werkzeug.security import generate_password_hash

try:
    from env_loader import load_project_env
    load_project_env(os.path.dirname(os.path.abspath(__file__)))
except ImportError:
    pass

# Function to detect if running on hosted server
def is_hosted():
    """Check if the application is running on the hosted server"""
    # Check if we're in the production path
    current_path = os.path.abspath(os.getcwd())
    if any(p in current_path.replace('\\', '/') for p in ['/home1/projectl/elimu_centric', '/home1/projectl/project_lucas']):
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
        'user': os.environ.get('DB_USER', 'elimucentric_school'),
        'password': os.environ.get('DB_PASSWORD', ''),
        'charset': 'utf8mb4',
        'cursorclass': pymysql.cursors.DictCursor
    }
    DB_NAME = os.environ.get('DB_NAME', 'elimucentric_school')
else:
    # Local development credentials
    DB_CONFIG = {
        'host': os.environ.get('DB_HOST', 'localhost'),
        'user': os.environ.get('DB_USER', 'root'),
        'password': os.environ.get('DB_PASSWORD', ''),
        'charset': 'utf8mb4',
        'cursorclass': pymysql.cursors.DictCursor
    }
    DB_NAME = os.environ.get('DB_NAME', 'modern_school')

def create_database():
    """Create the database if it doesn't exist"""
    try:
        connection = pymysql.connect(**DB_CONFIG)
        with connection.cursor() as cursor:
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME}")
            print(f"Database '{DB_NAME}' created or already exists.")
        connection.close()
        return True
    except Exception as e:
        print(f"Error creating database: {e}")
        return False

def create_tables():
    """Create all required tables"""
    config = DB_CONFIG.copy()
    config['database'] = DB_NAME
    
    try:
        connection = pymysql.connect(**config)
        with connection.cursor() as cursor:
            # Create users table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    full_name VARCHAR(255) NOT NULL,
                    email VARCHAR(255) UNIQUE NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    login_code VARCHAR(6) NULL COMMENT 'Six-digit portal sign-in',
                    student_id VARCHAR(20) NULL COMMENT 'Links student users to students.student_id',
                    role ENUM('parent', 'student', 'employee') NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE KEY uk_users_login_code (login_code)
                )
            """)
            print("Users table created.")
            
            # Create students table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS students (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    student_id VARCHAR(20) UNIQUE NOT NULL,
                    full_name VARCHAR(255) NOT NULL,
                    date_of_birth DATE,
                    gender VARCHAR(50),
                    current_grade VARCHAR(50),
                    previous_school VARCHAR(255),
                    address TEXT,
                    medical_info TEXT,
                    special_needs TEXT,
                    status ENUM('pending approval', 'in session', 'suspended', 'expelled', 'alumni') DEFAULT 'pending approval',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                )
            """)
            print("Students table created.")
            
            # Create parents table (linked to students via student_id)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS parents (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    student_id VARCHAR(20) NOT NULL,
                    full_name VARCHAR(255) NOT NULL,
                    phone VARCHAR(50) NOT NULL,
                    email VARCHAR(255),
                    relationship VARCHAR(50),
                    emergency_contact VARCHAR(255),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE,
                    INDEX idx_student_id (student_id)
                )
            """)
            print("Parents table created.")
            
            # Migrate existing parents table to allow NULL email (if table exists)
            try:
                cursor.execute("ALTER TABLE parents MODIFY COLUMN email VARCHAR(255) NULL")
                print("Parents table email column updated to allow NULL.")
            except Exception as e:
                # Column might already be nullable or table might not exist yet
                pass
            
            # Keep admissions table for backward compatibility (optional - can be removed later)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS admissions (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    student_full_name VARCHAR(255) NOT NULL,
                    date_of_birth DATE,
                    gender VARCHAR(50),
                    current_grade VARCHAR(50),
                    previous_school VARCHAR(255),
                    parent_name VARCHAR(255) NOT NULL,
                    parent_phone VARCHAR(50) NOT NULL,
                    parent_email VARCHAR(255) NOT NULL,
                    address TEXT,
                    emergency_contact VARCHAR(255),
                    medical_info TEXT,
                    special_needs TEXT,
                    status ENUM('pending approval', 'in session', 'suspended', 'expelled', 'alumni') DEFAULT 'pending approval',
                    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            print("Admissions table created (for backward compatibility).")
            
            # Create news table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS news (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    title VARCHAR(255) NOT NULL,
                    summary TEXT,
                    content TEXT,
                    image_url VARCHAR(500),
                    date DATE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            print("News table created.")
            
            # Create gallery table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS gallery (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    title VARCHAR(255) NOT NULL,
                    description TEXT,
                    image_url VARCHAR(500),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            print("Gallery table created.")
            
            # Create employees table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS employees (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    employee_id VARCHAR(20) UNIQUE NOT NULL,
                    full_name VARCHAR(255) NOT NULL,
                    email VARCHAR(255) UNIQUE NOT NULL,
                    phone VARCHAR(50) NOT NULL,
                    id_number VARCHAR(50) NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    profile_picture VARCHAR(500),
                    role ENUM('employee', 'super admin', 'head of institution', 'deputy head of institution', 'curriculum coordinator', 'teachers', 'accountant', 'secretary', 'librarian', 'warden', 'transport manager', 'store manager', 'technician') DEFAULT 'employee',
                    status ENUM('pending approval', 'active', 'suspended', 'fired', 'retired') DEFAULT 'pending approval',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX idx_email (email),
                    INDEX idx_employee_id (employee_id)
                )
            """)
            print("Employees table created.")

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS employee_number (
                    employee_id INT NOT NULL PRIMARY KEY,
                    staff_number VARCHAR(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE,
                    UNIQUE KEY uq_employee_number_staff_number (staff_number)
                )
            """)
            print("employee_number table created.")
            
            connection.commit()
            return True
    except Exception as e:
        print(f"Error creating tables: {e}")
        return False
    finally:
        connection.close()

def create_sample_users():
    """Create sample users for testing"""
    config = DB_CONFIG.copy()
    config['database'] = DB_NAME
    
    try:
        connection = pymysql.connect(**config)
        with connection.cursor() as cursor:
            # Check if users already exist
            cursor.execute("SELECT COUNT(*) as count FROM users")
            result = cursor.fetchone()
            if result['count'] > 0:
                print("Sample users already exist. Skipping creation.")
                return True
            
            # Create sample users
            users = [
                {
                    'full_name': 'John Parent',
                    'email': 'parent@example.com',
                    'password': 'password123',
                    'role': 'parent',
                    'login_code': '100001',
                    'student_id': None,
                },
                {
                    'full_name': 'Sarah Student',
                    'email': 'student@example.com',
                    'password': 'password123',
                    'role': 'student',
                    'login_code': '200002',
                    'student_id': None,
                },
                {
                    'full_name': 'Admin Employee',
                    'email': 'employee@example.com',
                    'password': 'password123',
                    'role': 'employee',
                    'login_code': None,
                    'student_id': None,
                },
            ]
            
            for user in users:
                password_hash = generate_password_hash(user['password'])
                cursor.execute("""
                    INSERT INTO users (full_name, email, password_hash, login_code, student_id, role)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (
                    user['full_name'],
                    user['email'],
                    password_hash,
                    user.get('login_code'),
                    user.get('student_id'),
                    user['role'],
                ))
            
            connection.commit()
            print("Sample users created successfully!")
            print("\nLogin credentials (portal uses six-digit code + password):")
            print("Parent: code 100001 / password123 (email parent@example.com for password reset)")
            print("Student: code 200002 / password123")
            print("Employee row in users is sample only; staff use employees table + six-digit employee ID.")
            return True
    except Exception as e:
        print(f"Error creating sample users: {e}")
        return False
    finally:
        connection.close()

def main():
    """Main function to initialize database"""
    print("=" * 50)
    print("Modern School Database Initialization")
    print("=" * 50)
    
    if not create_database():
        print("Failed to create database. Exiting.")
        return
    
    if not create_tables():
        print("Failed to create tables. Exiting.")
        return
    
    # Ask user if they want to create sample users
    response = input("\nDo you want to create sample users? (y/n): ").strip().lower()
    if response == 'y':
        create_sample_users()
    
    print("\n" + "=" * 50)
    print("Database initialization completed!")
    print("=" * 50)

if __name__ == '__main__':
    main()


