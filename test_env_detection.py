#!/usr/bin/env python3
"""
Test script to verify environment detection is working correctly
Run this to see which environment is detected
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

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
    config = {
        'host': os.environ.get('DB_HOST', defaults['host']),
        'user': os.environ.get('DB_USER', defaults['user']),
        'password': os.environ.get('DB_PASSWORD', defaults['password']),
        'database': os.environ.get('DB_NAME', defaults['database']),
    }
    
    return config, is_local

if __name__ == '__main__':
    print("=" * 60)
    print("Environment Detection Test")
    print("=" * 60)
    print()
    
    print("Current environment variables:")
    print(f"  DEPLOYMENT_ENV: {os.environ.get('DEPLOYMENT_ENV', '(not set)')}")
    print(f"  DB_HOST: {os.environ.get('DB_HOST', '(not set)')}")
    print(f"  DB_USER: {os.environ.get('DB_USER', '(not set)')}")
    print(f"  DB_NAME: {os.environ.get('DB_NAME', '(not set)')}")
    print(f"  DB_PASSWORD: {'(set)' if os.environ.get('DB_PASSWORD') else '(not set)'}")
    print(f"  FLASK_ENV: {os.environ.get('FLASK_ENV', '(not set)')}")
    print()
    
    print("Detection process:")
    print("-" * 60)
    config, is_local = get_db_config()
    print("-" * 60)
    print()
    
    env_type = "LOCALHOST/DEVELOPMENT" if is_local else "CPANEL/HOSTED"
    print(f"Result: Detected as {env_type}")
    print()
    print("Database configuration that will be used:")
    print(f"  Host: {config['host']}")
    print(f"  User: {config['user']}")
    print(f"  Database: {config['database']}")
    print(f"  Password: {'(set)' if config['password'] else '(empty)'}")
    print()
    print("=" * 60)
    print()
    print("To force a specific environment, set DEPLOYMENT_ENV in your .env file:")
    print("  DEPLOYMENT_ENV=development  (forces localhost)")
    print("  DEPLOYMENT_ENV=production   (forces cPanel/hosted)")

