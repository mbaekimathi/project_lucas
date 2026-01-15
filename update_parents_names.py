"""
Script to update parent names in the parents table to "PARENT TO [STUDENT NAME]"
"""
import pymysql
from dotenv import load_dotenv
import os

load_dotenv()

def is_hosted():
    """Check if running on hosted server"""
    hostname = os.environ.get('HOSTNAME', '')
    server_name = os.environ.get('SERVER_NAME', '')
    
    if 'cpanel' in hostname.lower() or 'cpanel' in server_name.lower():
        return True
    if 'shared' in hostname.lower() or 'shared' in server_name.lower():
        return True
    
    if any(indicator in hostname.lower() for indicator in ['hostinger', 'bluehost', 'godaddy', 'siteground']):
        return True
    
    return False

# Database configuration - automatically detect hosted vs local
if is_hosted():
    DB_CONFIG = {
        'host': os.environ.get('DB_HOST', 'localhost'),
        'user': os.environ.get('DB_USER', 'projectl_school'),
        'password': os.environ.get('DB_PASSWORD', 'Itskimathi007'),
        'database': os.environ.get('DB_NAME', 'projectl_school'),
        'charset': 'utf8mb4',
        'cursorclass': pymysql.cursors.DictCursor
    }
else:
    DB_CONFIG = {
        'host': os.environ.get('DB_HOST', 'localhost'),
        'user': os.environ.get('DB_USER', 'root'),
        'password': os.environ.get('DB_PASSWORD', ''),
        'database': os.environ.get('DB_NAME', 'modern_school'),
        'charset': 'utf8mb4',
        'cursorclass': pymysql.cursors.DictCursor
    }

def update_parents_names():
    """Update all parent names to 'PARENT TO [STUDENT NAME]' format"""
    try:
        connection = pymysql.connect(**DB_CONFIG)
        print(f"Connected to database: {DB_CONFIG['database']}")
        print("=" * 60)
        
        updated_count = 0
        
        with connection.cursor() as cursor:
            # Get all parent records with their associated student names
            cursor.execute("""
                SELECT p.id, p.student_id, s.full_name as student_name, p.full_name as current_parent_name
                FROM parents p
                INNER JOIN students s ON p.student_id = s.student_id
                ORDER BY p.id
            """)
            
            parents = cursor.fetchall()
            total_parents = len(parents)
            
            print(f"Found {total_parents} parent records to update")
            print("=" * 60)
            
            for parent in parents:
                parent_id = parent['id']
                student_id = parent['student_id']
                student_name = parent['student_name']
                current_parent_name = parent['current_parent_name']
                
                # Generate new parent name
                new_parent_name = f"PARENT TO {student_name}"
                
                # Update parent name
                cursor.execute("""
                    UPDATE parents 
                    SET full_name = %s 
                    WHERE id = %s
                """, (new_parent_name, parent_id))
                
                updated_count += 1
                
                if updated_count % 20 == 0:
                    print(f"  [OK] Updated {updated_count} parent records...")
            
            # Commit all changes
            connection.commit()
            
        print("\n" + "=" * 60)
        print(f"Update complete!")
        print(f"  [OK] Successfully updated: {updated_count} parent records")
        print(f"  Total processed: {updated_count} parents")
        
        connection.close()
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    print("Parent Names Update Script")
    print("=" * 60)
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == '--yes':
        update_parents_names()
    else:
        try:
            confirm = input("This will update all parent names to 'PARENT TO [STUDENT NAME]' format. Continue? (yes/no): ")
            if confirm.lower() == 'yes':
                update_parents_names()
            else:
                print("Cancelled.")
        except EOFError:
            print("Running in non-interactive mode...")
            update_parents_names()



