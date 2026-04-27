#!/usr/bin/env python3
"""
Environment configuration checker for Elimu Centric.
Run this script to verify .env and see which mode (local vs hosted) will be used.
Usage: python check_env.py
"""
import os
from pathlib import Path

# Load .env and optional .env.local (see env.local.example, env.hosted.example)
env_root = Path(__file__).parent
try:
    from env_loader import load_project_env
    load_project_env(str(env_root))
    _env = env_root / ".env"
    _local = env_root / ".env.local"
    if _env.is_file() or _local.is_file():
        if _local.is_file():
            print(f"Loaded .env and .env.local from {env_root}")
        else:
            print(f"Loaded .env from {env_root}")
    else:
        print(f"WARNING: No .env or .env.local at {env_root}")
        print("  Production: copy env.hosted.example to .env")
        print("  Local dev:   copy env.local.example to .env.local\n")
except ImportError:
    print("Note: python-dotenv not installed. Using system environment only.")

def is_hosted():
    """Check if the application will use hosted (production) settings."""
    current_path = str(Path.cwd().resolve())
    if any(p in current_path.replace('\\', '/') for p in ['/home1/projectl/elimu_centric', '/home1/projectl/project_lucas']):
        return True
    if os.environ.get('IS_HOSTED', '').lower() in ['true', '1', 'yes']:
        return True
    db_host = os.environ.get('DB_HOST', 'localhost')
    if db_host not in ('localhost', '127.0.0.1', ''):
        return True
    return False

def main():
    print("=" * 60)
    print("Elimu Centric - Environment Check")
    print("=" * 60)

    hosted = is_hosted()
    mode = "HOSTED (production)" if hosted else "LOCAL (development)"
    print(f"\nMode: {mode}")
    print("-" * 60)

    # Database
    db_host = os.environ.get('DB_HOST', 'localhost')
    db_user = os.environ.get('DB_USER', 'elimucentric_school' if hosted else 'root')
    db_name = os.environ.get('DB_NAME', 'elimucentric_school' if hosted else 'modern_school')
    db_pass = os.environ.get('DB_PASSWORD', '')

    print("Database:")
    print(f"  Host:     {db_host}")
    print(f"  User:     {db_user}")
    print(f"  Database: {db_name}")
    print(f"  Password: {'*' * 8 if db_pass else '(empty)'}")

    # Secret key
    sk = os.environ.get('SECRET_KEY', '')
    if not sk or sk == 'your-secret-key-change-in-production':
        print("\n  WARNING: SECRET_KEY not set or still default - change for production!")
    else:
        print("\n  SECRET_KEY: (set)")

    # Mail
    mail_user = os.environ.get('MAIL_USERNAME', '')
    print("\nEmail:")
    print(f"  Configured: {'Yes' if mail_user else 'No (optional)'}")

    print("\n" + "=" * 60)

if __name__ == '__main__':
    main()
