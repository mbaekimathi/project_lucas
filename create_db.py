"""
Database initialization script for Modern School
Run this script to create the database and tables
"""
import pymysql
import os
from werkzeug.security import generate_password_hash
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
        'charset': 'utf8mb4',
        'cursorclass': pymysql.cursors.DictCursor
    }

# Initialize database configuration
DB_CONFIG = get_db_config()

# Get database name based on environment
def get_db_name():
    """Get database name based on environment"""
    is_local = is_localhost()
    default_db = 'modern_school' if is_local else 'projectl_school'
    return os.environ.get('DB_NAME', default_db)

DB_NAME = get_db_name()

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
                    role ENUM('parent', 'student', 'employee') NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
                    email VARCHAR(255) NOT NULL,
                    relationship VARCHAR(50),
                    emergency_contact VARCHAR(255),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE,
                    INDEX idx_student_id (student_id)
                )
            """)
            print("Parents table created.")
            
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
                    role ENUM('employee', 'super admin', 'principal', 'deputy principal', 'academic coordinator', 'teachers', 'accountant', 'librarian', 'warden', 'transport manager', 'technician') DEFAULT 'employee',
                    status ENUM('pending approval', 'active', 'suspended', 'fired', 'retired') DEFAULT 'pending approval',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX idx_email (email),
                    INDEX idx_employee_id (employee_id)
                )
            """)
            print("Employees table created.")
            
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
                    'role': 'parent'
                },
                {
                    'full_name': 'Sarah Student',
                    'email': 'student@example.com',
                    'password': 'password123',
                    'role': 'student'
                },
                {
                    'full_name': 'Admin Employee',
                    'email': 'employee@example.com',
                    'password': 'password123',
                    'role': 'employee'
                }
            ]
            
            for user in users:
                password_hash = generate_password_hash(user['password'])
                cursor.execute("""
                    INSERT INTO users (full_name, email, password_hash, role)
                    VALUES (%s, %s, %s, %s)
                """, (user['full_name'], user['email'], password_hash, user['role']))
            
            connection.commit()
            print("Sample users created successfully!")
            print("\nLogin credentials:")
            print("Parent: parent@example.com / password123")
            print("Student: student@example.com / password123")
            print("Employee: employee@example.com / password123")
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


