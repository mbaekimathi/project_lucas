#!/usr/bin/env python3
"""
Helper script to create a new migration file
Usage: python migrations/create_migration.py "description_of_migration"
"""
import sys
import os
from datetime import datetime

def get_next_migration_number():
    """Get the next migration number"""
    migrations_dir = os.path.dirname(os.path.abspath(__file__))
    existing = []
    for filename in os.listdir(migrations_dir):
        if filename.endswith('.py') and filename not in ('__init__.py', 'migration_manager.py', 'create_migration.py'):
            try:
                num = int(filename.split('_')[0])
                existing.append(num)
            except ValueError:
                pass
    return max(existing) + 1 if existing else 1

def create_migration(description):
    """Create a new migration file"""
    migration_num = get_next_migration_number()
    safe_name = description.lower().replace(' ', '_').replace('-', '_')
    safe_name = ''.join(c for c in safe_name if c.isalnum() or c == '_')
    migrations_dir = os.path.dirname(os.path.abspath(__file__))
    filename = f"{migration_num:03d}_{safe_name}.py"
    filepath = os.path.join(migrations_dir, filename)
    template = f'''"""
Migration: {description}
Date: {datetime.now().strftime('%Y-%m-%d')}
"""

def up():
    """SQL statements to run"""
    return [
        # "ALTER TABLE table_name ADD COLUMN col VARCHAR(255)",
    ]

# Or use Python migration for complex logic:
# def migrate(connection):
#     with connection.cursor() as cursor:
#         cursor.execute("ALTER TABLE ...")
#     connection.commit()
#     return True
'''
    with open(filepath, 'w') as f:
        f.write(template)
    print(f"Created: {filepath}")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python migrations/create_migration.py 'description'")
        sys.exit(1)
    create_migration(' '.join(sys.argv[1:]))
