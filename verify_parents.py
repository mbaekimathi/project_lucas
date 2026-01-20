"""Verify parent names format"""
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

# Check a few parent names
cur.execute("""
    SELECT p.full_name as parent_name, s.full_name as student_name
    FROM parents p
    INNER JOIN students s ON p.student_id = s.student_id
    LIMIT 10
""")

parents = cur.fetchall()
print("Sample parent names:")
print("=" * 60)
for p in parents:
    print(f"Parent: {p['parent_name']}")
    print(f"Student: {p['student_name']}")
    print()

# Check if all parents have correct format
cur.execute("""
    SELECT COUNT(*) as count
    FROM parents p
    INNER JOIN students s ON p.student_id = s.student_id
    WHERE p.full_name = CONCAT('PARENT TO ', s.full_name)
""")
correct_format = cur.fetchone()['count']

cur.execute("SELECT COUNT(*) as count FROM parents")
total = cur.fetchone()['count']

print("=" * 60)
print(f"Total parents: {total}")
print(f"Parents with correct format: {correct_format}")
print(f"Parents needing update: {total - correct_format}")

conn.close()




