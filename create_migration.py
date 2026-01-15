#!/usr/bin/env python3
"""
Helper script to create a new migration file
Usage: python create_migration.py "description_of_migration"
"""

import sys
import os
from datetime import datetime

def get_next_migration_number():
    """Get the next migration number"""
    migrations_dir = 'migrations'
    if not os.path.exists(migrations_dir):
        return 1
    
    existing = []
    for filename in os.listdir(migrations_dir):
        if filename.endswith('.py') and filename != '__init__.py' and filename != 'migration_manager.py':
            try:
                num = int(filename.split('_')[0])
                existing.append(num)
            except:
                pass
    
    return max(existing) + 1 if existing else 1

def create_migration(description):
    """Create a new migration file"""
    migration_num = get_next_migration_number()
    safe_name = description.lower().replace(' ', '_').replace('-', '_')
    safe_name = ''.join(c for c in safe_name if c.isalnum() or c == '_')
    
    filename = f"{migration_num:03d}_{safe_name}.py"
    filepath = os.path.join('migrations', filename)
    
    template = f'''"""
Migration: {description}
Date: {datetime.now().strftime('%Y-%m-%d')}
"""

def up():
    """SQL statements to run"""
    return [
        # Add your SQL statements here
        # Example:
        # "ALTER TABLE students ADD COLUMN new_field VARCHAR(255)",
        # "CREATE INDEX idx_new_field ON students(new_field)"
    ]

# Alternative: Use Python migration for complex logic
# def migrate(connection):
#     """Python function to run migration"""
#     try:
#         with connection.cursor() as cursor:
#             # Your migration logic here
#             cursor.execute("ALTER TABLE students ADD COLUMN new_field VARCHAR(255)")
#             connection.commit()
#             return True
#     except Exception as e:
#         print(f"Migration error: {{e}}")
#         return False
'''
    
    if not os.path.exists('migrations'):
        os.makedirs('migrations')
    
    with open(filepath, 'w') as f:
        f.write(template)
    
    print(f"✓ Created migration: {filepath}")
    print(f"  Edit the file to add your migration SQL or Python code")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python create_migration.py 'description of migration'")
        print("Example: python create_migration.py 'add email to students'")
        sys.exit(1)
    
    description = ' '.join(sys.argv[1:])
    create_migration(description)






