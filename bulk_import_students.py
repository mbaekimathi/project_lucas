"""
Script to bulk import students into the database
Run this script to import the provided student data
"""

import pymysql
from datetime import datetime
import sys
import os

# Add the project directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import database config
from app import DB_CONFIG, get_db_connection, generate_student_id

# Student data organized by grade
student_data = {
    'PLAYGROUP': [
        'Abigael Mutanu', 'Adasha Kawai', 'Angel Wangari', 'Ariel Mulongo', 'Aziel Maina',
        'Bicks Wandabwa', 'Brighton Musili', 'Clive Andrew', 'Crescencia Njeri', 'Derrick Mutuku',
        'Divine Akinyi', 'Faith Wanjiru', 'Gift Muthoni', 'Ivy Muthoni', 'Jayden Mwangi',
        'Joy Chepkemoi', 'Junior Kiplagat', 'Keith Kimani', 'Liam Mwenda', 'Mercy Kavengi',
        'Mitchell Mutua', 'Naomi Wanjiku', 'Prince Otieno', 'Rayan Hassan', 'Ryan Muthee',
        'Samantha Njeri', 'Sheila Atieno', 'Tyler Mwiti', 'Victor Kiptoo'
    ],
    'PP1': [
        'Abigail Muthoni', 'Alex Kiprotich', 'Angel Mumo', 'Ann Wairimu', 'Brian Mutua',
        'Caleb Mwangi', 'Cathy Njeri', 'Clinton Otieno', 'Daisy Chebet', 'David Mutiso',
        'Derrick Mbugua', 'Faith Chepkirui', 'Felix Maina', 'Gift Akinyi', 'Grace Wambui',
        'Ian Mwenda', 'Ivy Atieno', 'James Kamau', 'Jeff Kibet', 'Joyline Wanjiru',
        'Kevin Mutuku', 'Leah Njeri', 'Leon Mwangi', 'Lydia Chepkemoi', 'Mark Otieno',
        'Mercy Wanjiku', 'Mitchell Kiplagat'
    ],
    'PP2': [
        'Allan Mutiso', 'Angel Jepchirchir', 'Brian Mwangi', 'Calvin Mutua', 'Dennis Kiptoo',
        'Diana Wanjiru', 'Emmanuel Otieno', 'Faith Kendi', 'Frank Kibet', 'Grace Chebet',
        'Ian Kimani', 'Ivy Wairimu', 'Jason Muthee', 'Jeff Maina', 'John Mwenda',
        'Joy Chepngeno', 'Kelvin Mutuku', 'Leah Atieno', 'Liam Kiprop', 'Mercy Njeri',
        'Mike Otieno', 'Moses Kamau', 'Nathan Kiplagat', 'Peter Mwangi', 'Ryan Mutiso'
    ],
    'GRADE 1': [
        'Allan Kiprotich', 'Angel Wambui', 'Brian Otieno', 'Caleb Mutua', 'Cynthia Wanjiru',
        'Daniel Kibet', 'Derrick Mwangi', 'Diana Chepkemoi', 'Emmanuel Mutiso', 'Faith Njeri',
        'Frank Mwenda', 'Grace Akinyi', 'Ian Kamau', 'Ivy Chebet', 'James Muthee',
        'Jeff Kiptoo', 'Joyline Wanjiku', 'Kelvin Maina', 'Leah Wairimu', 'Leon Otieno',
        'Mercy Chepngeno', 'Mike Mutua'
    ],
    'GRADE 2': [
        'Allan Mwangi', 'Angel Chebet', 'Brian Mutiso', 'Caleb Kiptoo', 'Daisy Wanjiru',
        'Daniel Kamau', 'Dennis Otieno', 'Diana Akinyi', 'Emmanuel Mwenda', 'Faith Chepkirui',
        'Felix Mutua', 'Grace Njeri', 'Ian Kiprotich', 'Ivy Wambui', 'James Maina',
        'Jeff Mutiso', 'Joy Chepngeno', 'Kelvin Mwangi', 'Leah Atieno', 'Leon Kibet',
        'Mercy Wairimu'
    ],
    'GRADE 3': [
        'Allan Mutua', 'Angel Wanjiru', 'Brian Kiptoo', 'Caleb Mwenda', 'Cynthia Njeri',
        'Daniel Otieno', 'Dennis Kamau', 'Diana Chebet', 'Emmanuel Mwangi', 'Faith Akinyi',
        'Frank Mutiso', 'Grace Wambui', 'Ian Kiplagat', 'Ivy Njeri', 'James Kiprotich',
        'Jeff Maina', 'Joyline Chepkemoi', 'Kelvin Muthee', 'Leah Wairimu'
    ],
    'GRADE 4': [
        'Allan Kamau', 'Angel Chepngeno', 'Brian Mwenda', 'Caleb Otieno', 'Daisy Njeri',
        'Daniel Mutiso', 'Dennis Mwangi', 'Diana Wairimu', 'Emmanuel Kiptoo', 'Faith Wanjiku',
        'Frank Maina', 'Grace Chebet', 'Ian Mutua', 'Ivy Atieno', 'James Kibet',
        'Jeff Mwangi', 'Joy Chepkirui', 'Kelvin Kamau'
    ],
    'GRADE 5': [
        'Allan Mwenda', 'Angel Njeri', 'Brian Kiprotich', 'Caleb Mutiso', 'Daisy Wambui',
        'Daniel Mwangi', 'Dennis Otieno', 'Diana Chepngeno', 'Emmanuel Kamau', 'Faith Chebet',
        'Frank Muthee', 'Grace Wairimu', 'Ian Maina', 'Ivy Njeri', 'James Kiptoo',
        'Jeff Otieno'
    ],
    'GRADE 6': [
        'Allan Otieno', 'Angel Wanjiku', 'Brian Mwangi', 'Caleb Kamau', 'Daisy Chepkirui',
        'Daniel Maina', 'Dennis Mutiso', 'Diana Wambui', 'Emmanuel Kiprotich', 'Faith Njeri',
        'Frank Otieno', 'Grace Mwenda', 'Ian Kibet', 'Ivy Wairimu', 'James Mwangi'
    ]
}

def import_students():
    """Import all students from the student_data dictionary"""
    connection = get_db_connection()
    if not connection:
        print("Error: Could not connect to database")
        return
    
    imported = []
    errors = []
    total_count = 0
    
    try:
        with connection.cursor() as cursor:
            for grade, students in student_data.items():
                print(f"\nProcessing {grade}: {len(students)} students")
                
                for student_name in students:
                    total_count += 1
                    try:
                        full_name = student_name.strip().upper()
                        
                        if not full_name:
                            errors.append({'name': student_name, 'grade': grade, 'error': 'Empty name'})
                            continue
                        
                        # Check if student already exists
                        cursor.execute("SELECT student_id FROM students WHERE full_name = %s", (full_name,))
                        existing = cursor.fetchone()
                        if existing:
                            print(f"  [SKIP] Skipping {full_name} - already exists")
                            continue
                        
                        # Generate unique student ID
                        student_id = generate_student_id(connection)
                        
                        # Insert student
                        cursor.execute("""
                            INSERT INTO students 
                            (student_id, full_name, current_grade, status, student_category)
                            VALUES (%s, %s, %s, 'in session', 'regular')
                        """, (student_id, full_name, grade))
                        
                        # Create placeholder parent record
                        placeholder_parent_name = f"PARENT OF {full_name}"
                        placeholder_email = f"parent.{student_id.lower()}@school.local"
                        
                        cursor.execute("""
                            INSERT INTO parents 
                            (student_id, full_name, phone, email, relationship)
                            VALUES (%s, %s, %s, %s, %s)
                        """, (student_id, placeholder_parent_name, '0000000000', placeholder_email, 'Guardian'))
                        
                        imported.append({
                            'student_id': student_id,
                            'full_name': full_name,
                            'grade': grade
                        })
                        
                        print(f"  [OK] {student_id}: {full_name} ({grade})")
                        
                    except Exception as e:
                        error_msg = str(e)
                        errors.append({'name': student_name, 'grade': grade, 'error': error_msg})
                        print(f"  [ERROR] Error importing {student_name}: {error_msg}")
            
            connection.commit()
            
            print("\n" + "="*60)
            print("IMPORT SUMMARY")
            print("="*60)
            print(f"Total students processed: {total_count}")
            print(f"Successfully imported: {len(imported)}")
            print(f"Errors: {len(errors)}")
            print(f"Skipped (duplicates): {total_count - len(imported) - len(errors)}")
            
            if errors:
                print("\nErrors:")
                for error in errors:
                    print(f"  - {error['name']} ({error['grade']}): {error['error']}")
            
            print("\n" + "="*60)
            print("Import completed successfully!")
            print("="*60)
            
    except Exception as e:
        connection.rollback()
        print(f"\nFatal error during import: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if connection:
            try:
                connection.close()
            except:
                pass

if __name__ == '__main__':
    print("Starting bulk student import...")
    print("="*60)
    import_students()

