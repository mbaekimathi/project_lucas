"""Quick script to check and update parents"""
import pymysql
from dotenv import load_dotenv
import os

load_dotenv()

DB_CONFIG = {
    'host': os.environ.get('DB_HOST', 'localhost'),
    'user': os.environ.get('DB_USER', 'root'),
    'password': os.environ.get('DB_PASSWORD', ''),
    'database': os.environ.get('DB_NAME', 'modern_school'),
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}

conn = pymysql.connect(**DB_CONFIG)
cur = conn.cursor()

# Check counts
cur.execute('SELECT COUNT(*) as count FROM parents')
parent_count = cur.fetchone()['count']
print(f'Total parents: {parent_count}')

cur.execute('SELECT COUNT(*) as count FROM students')
student_count = cur.fetchone()['count']
print(f'Total students: {student_count}')

# Update parents
if parent_count > 0:
    cur.execute("""
        UPDATE parents p
        INNER JOIN students s ON p.student_id = s.student_id
        SET p.full_name = CONCAT('PARENT TO ', s.full_name)
    """)
    conn.commit()
    print(f'Updated {cur.rowcount} parent records')
else:
    print('No parents found to update')

conn.close()




