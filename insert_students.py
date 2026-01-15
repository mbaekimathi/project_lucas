"""
Script to insert students into the database with generated details
"""
import pymysql
from datetime import datetime, timedelta
import random
import re
from dotenv import load_dotenv
import os

load_dotenv()

def is_hosted():
    """Check if running on hosted server"""
    # Check for common hosted server indicators
    hostname = os.environ.get('HOSTNAME', '')
    server_name = os.environ.get('SERVER_NAME', '')
    
    # Check if running on cPanel/shared hosting
    if 'cpanel' in hostname.lower() or 'cpanel' in server_name.lower():
        return True
    if 'shared' in hostname.lower() or 'shared' in server_name.lower():
        return True
    
    # Check for specific hosting providers
    if any(indicator in hostname.lower() for indicator in ['hostinger', 'bluehost', 'godaddy', 'siteground']):
        return True
    
    return False

# Database configuration - automatically detect hosted vs local
if is_hosted():
    # Hosted server credentials
    DB_CONFIG = {
        'host': os.environ.get('DB_HOST', 'localhost'),
        'user': os.environ.get('DB_USER', 'projectl_school'),
        'password': os.environ.get('DB_PASSWORD', 'Itskimathi007'),
        'database': os.environ.get('DB_NAME', 'projectl_school'),
        'charset': 'utf8mb4',
        'cursorclass': pymysql.cursors.DictCursor
    }
else:
    # Local development credentials
    DB_CONFIG = {
        'host': os.environ.get('DB_HOST', 'localhost'),
        'user': os.environ.get('DB_USER', 'root'),
        'password': os.environ.get('DB_PASSWORD', ''),
        'database': os.environ.get('DB_NAME', 'modern_school'),
        'charset': 'utf8mb4',
        'cursorclass': pymysql.cursors.DictCursor
    }

# Student data organized by grade
STUDENTS_BY_GRADE = {
    'PP1': [
        'ABIGAEL MUTANU', 'ADASHA KAWAI', 'ANGEL WANGARI', 'ARIEL MULONGO', 'AZIEL MAINA',
        'BICKS WANDABWA', 'BRIGHTON MUSILI', 'CLIVE ANDREW', 'CRESCENCIA NJERI', 'ELLA FLORA WEKESA',
        'EVANS WANJAU', 'FAVOUR WAIRIMU', 'GIANNA ADIA', 'GIDEON MWAMBA', 'HADRIEL MUKHWANA',
        'JASMINE MORAA', 'JOAN WANGUI', 'JOHN AMANI', 'JOY NYAMBURA', 'JULIA MWAMU',
        'KELSY WANJIRU', 'LIAM AMONDE', 'LOWELL OLUOCH', 'LUCKY OGEMBO', 'MALKIA VICTORIA',
        'MEGHAN GOVOGO', 'MELVIN NJOROGE', 'OLA KEYSHIA', 'PEACE JOY', 'QUINTER LESLY',
        'SHANICE CHEROP', 'SHANTEL WANJIKU', 'SHENAZ WANGUI', 'TASHA MIRIMO', 'TREVOR MWIRIGI',
        'VALENCIA MARIA', 'VICTOR OMUNDI', 'VIONAH BOCHERE', 'ZARA GIKANDI'
    ],
    'PP2': [
        'AIDEN SULA', 'ALVIN WEZIZI', 'AMANI JOY GATHONI', 'AMOS OMOSA', 'ANGEL CHEPKOECH',
        'BENSON KARUNGU', 'BRAVIN MUTWIRI', 'CHARLOTTE NAKHUMICHA', 'CHRISTOPHER ABUGA', 'CLAIRE NJOKI',
        'DANIEL MUSYOKI', 'ESTHER WANGUI', 'EZEKIEL LITEMBO', 'GEOFFREY MUTHAMI', 'JAYDEN GIKUNGU',
        'JAYDEN NYAKUNDI', 'JAYDEN OMONDI', 'JEREMIAH MWANGANGI', 'JOSEPH NJOROGE', 'JOSEPH RIE',
        'JOY BLESSING', 'KAYDEN WAKIARA', 'KINSLEY KIGEN', 'KYLA AMANI', 'MARGARET NDUTA',
        'MELISA PENDO', 'NAFTALI NJERU', 'NESHIE WANDABWA', 'NYADIT KIR DENG', 'PRINCESS WEKESA',
        'RAMSEY MAINGI', 'SARAH AKINYI', 'SHANNEL AMANDA', 'SHERIETAH NEIMAH', 'SHIRLEEN AWINO',
        'TYRON DERWIN', 'VELMAH NJERI', 'VICTOR MUNGAI'
    ],
    'GRADE 1': [
        'ADRIAN OMANGI', 'AMOR WACHUKA', 'ANGEL MUTHONI', 'ANLON MUNDIA', 'ANNAH PENDO',
        'BEN CARSON', 'BLESSING OMONDI', 'CHARLOTTE HETA', 'EVE NYIVA', 'GADDIEL KERINA',
        'GEORGE MWIMA', 'JAMES ODEMBA', 'JAYDEN GATHIRE', 'JAYSON NJUGUNA', 'JOHN WACHIRA',
        'JOSHUA OTIENO', 'LYDIA NEEMA', 'NADIA NASIMIYU', 'PATIENCE WAYUA', 'PETER BORO',
        'PHILLIP MUJENYI', 'REEGAN RITHO', 'RISPER WANGU', 'RYTON MACHISU', 'SAMSON OGONYO',
        'SHANTEL MITO', 'SHARON WAMBUI', 'SHAWN KYLE', 'SHEILA ANGEL WAMAITHA', 'TRAVIS BERUR',
        'VICTOR KIMANI'
    ],
    'GRADE 2': [
        'ALVIN WANJAU', 'ANDREW MWANGI', 'BRAVIAN RYAN', 'BRIAR WAITHERA', 'DAISY NEKESA',
        'DEBORAH NANJALA', 'EDRIAN MOGIRE', 'ESTHER AMARYSS', 'GIFTON WANJAU', 'JACOB MAHANAIM',
        'JANE WANGARI', 'JEMIMAH BLESSING', 'MARION MOETI', 'MARY MUENI', 'MAXWELL KHISA',
        'MAXWELL MURIGI', 'MESHACK SHIVAIVO', 'MORGAN MUCHOKI', 'OWEN KISANYA', 'PATRICE OSORO',
        'SALIMINE MUMO', 'SHANTEL WAIRIMU', 'SHARON NDINDA', 'TATIANA WANJIKU'
    ],
    'GRADE 3': [
        'ANN ALOO', 'BILHA WAIRIMU', 'CELESTINE NDUNGWA', 'DAISY KAVUTHA', 'DANIEL WAWERU',
        'DERRICK MARAGA', 'DYLAN NJUGUNA', 'ELIZABETH AYUMA', 'EMMANUEL MWENDWA', 'FADRAHLHAN NAALIA',
        'GRAVINS OYARO', 'GWENDOLINE OMBURO', 'IBURA BOTOTO', 'JAYDEN WEKESA', 'KAYLAN WAMBUI',
        'KETHY AWUOR', 'KEZIA NALIAKA', 'LAMECK BAHATI', 'MARTHA MUTHONI', 'NADIA AMBUNYA',
        'NELLY EVERLYNE', 'NIVAH MIRIMO', 'ROBERT MUSUNDI', 'RYAN ROTICH', 'SYLVIA ACHIENG',
        'VALENCIA NELIMA', 'WAYNE MBURU'
    ],
    'GRADE 4': [
        'BRAMWEL CHEGE', 'BRAMWEL OCHIENG', 'CHRISTINE MUMBI', 'DAVID NDERITU', 'DOROTHY OTIENO',
        'FAVOUR MAKENA', 'KELYNE NJERI', 'KYLE KARIUKI', 'LAVIN ACHIENG', 'MARY WANJIRU',
        'NATASHA KEMUNTO', 'NYIBOL KIR DENG', 'PHRAEL ODHIAMBO', 'PRAISE NJERI', 'PURITY ORONI',
        'RACHEL NJERI', 'TIFFANY WANJIKU', 'VENUS KYENI'
    ],
    'GRADE 5': [
        'ARON OMONDI', 'ASHLEY WAIRIMU', 'BLESSING MUENI', 'CRIGON MARUBE', 'EMMANUEL GITONGA',
        'ESTHER NYAKIO', 'GIFTON KERINA', 'GLEN ONYANGO', 'HOPE WANGARI', 'JOAN WAITHERA',
        'JOHNSON KARANI', 'LENAH KEMUNTO', 'MOSES WAMBUA', 'PRAXEDES NADDIN', 'PRECIOUS KYLA NDUTA',
        'PRISCAH WANJA', 'REBECCA ATIENO', 'ROBINSON MUSUNDI', 'SAVON KEMUNTO', 'SHANTEL WANJIRU',
        'TERESIA WANJIRU', 'WALTER HENRY'
    ],
    'GRADE 6': [
        'ALBERT MWEU', 'BLESSING MBURU', 'BRIAN MURUMURI', 'DANIEL CLINTON', 'EMMANUEL ASIKOYE',
        'GLORIA NYANCHAMA', 'JAYDEN NGANGA', 'JOYCE INZAI', 'KELVIN MBUTHIA', 'MAXWELL CHARAI',
        'MITCHEL NELIMA', 'NICHOLAS MUTUA', 'RUTH NJOKI', 'SHALINE WAMBUI', 'SHARON WAIRIMU',
        'WINNIE WAMAITHA', 'ZADDOCK BARAZA'
    ]
}

# Age ranges by grade (for generating date of birth)
AGE_RANGES = {
    'PP1': (3, 4),   # 3-4 years old
    'PP2': (4, 5),   # 4-5 years old
    'GRADE 1': (5, 6),
    'GRADE 2': (6, 7),
    'GRADE 3': (7, 8),
    'GRADE 4': (8, 9),
    'GRADE 5': (9, 10),
    'GRADE 6': (10, 11)
}

def generate_student_id(connection):
    """Generate a unique student ID in format STU001, STU002, etc."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT student_id FROM students 
                WHERE student_id LIKE 'STU%' 
                ORDER BY CAST(SUBSTRING(student_id, 4) AS UNSIGNED) DESC 
                LIMIT 1
            """)
            result = cursor.fetchone()
            
            if result:
                last_number = int(result['student_id'][3:])
                new_number = last_number + 1
            else:
                new_number = 1
            
            return f"STU{new_number:03d}"
    except Exception as e:
        print(f"Error generating student ID: {e}")
        return f"STU{int(datetime.now().timestamp()) % 100000:05d}"

def guess_gender(name):
    """Guess gender based on name (simple heuristic)"""
    name_upper = name.upper()
    # Common female names in Kenya
    female_indicators = ['ANGEL', 'JOY', 'JASMINE', 'JOAN', 'JULIA', 'SHANICE', 'SHANTEL', 
                        'SHENAZ', 'VALENCIA', 'VIONAH', 'ZARA', 'ADASHA', 'CRESCENCIA', 
                        'ELLA', 'FAVOUR', 'GIANNA', 'KELSY', 'MALKIA', 'MEGHAN', 'OLA', 
                        'PEACE', 'QUINTER', 'TASHA', 'CHARLOTTE', 'CLAIRE', 'ESTHER', 
                        'KYLA', 'MARGARET', 'MELISA', 'PRINCESS', 'SARAH', 'SHANNEL', 
                        'SHERIETAH', 'SHIRLEEN', 'VELMAH', 'AMOR', 'ANNAH', 'BLESSING', 
                        'EVE', 'LYDIA', 'NADIA', 'PATIENCE', 'RISPER', 'SHARON', 'SHEILA', 
                        'DAISY', 'DEBORAH', 'JANE', 'JEMIMAH', 'MARION', 'MARY', 'TATIANA', 
                        'ANN', 'BILHA', 'CELESTINE', 'ELIZABETH', 'GWENDOLINE', 'KAYLAN', 
                        'KEZIA', 'MARTHA', 'NELLY', 'NIVAH', 'SYLVIA', 'VALENCIA', 
                        'CHRISTINE', 'DOROTHY', 'KELYNE', 'PRAISE', 'PURITY', 'RACHEL', 
                        'TIFFANY', 'VENUS', 'ASHLEY', 'ESTHER', 'HOPE', 'JOAN', 'LENAH', 
                        'PRECIOUS', 'PRISCAH', 'REBECCA', 'SHANTEL', 'TERESIA', 'GLORIA', 
                        'JOYCE', 'RUTH', 'SHALINE', 'SHARON', 'WINNIE']
    
    # Common male names
    male_indicators = ['JOHN', 'VICTOR', 'TREVOR', 'LIAM', 'LOWELL', 'LUCKY', 'MELVIN', 
                       'EVANS', 'GIDEON', 'HADRIEL', 'BRIGHTON', 'CLIVE', 'AZIEL', 'ARIEL', 
                       'BICKS', 'AIDEN', 'ALVIN', 'AMOS', 'BENSON', 'BRAVIN', 'CHRISTOPHER', 
                       'DANIEL', 'EZEKIEL', 'GEOFFREY', 'JAYDEN', 'JEREMIAH', 'JOSEPH', 
                       'KAYDEN', 'KINSLEY', 'NAFTALI', 'RAMSEY', 'TYRON', 'VICTOR', 
                       'ADRIAN', 'ANLON', 'BEN', 'GADDIEL', 'GEORGE', 'JAMES', 'JAYSON', 
                       'JOSHUA', 'PETER', 'PHILLIP', 'SAMSON', 'SHAWN', 'TRAVIS', 
                       'ALVIN', 'ANDREW', 'BRAVIAN', 'EDRIAN', 'GIFTON', 'JACOB', 
                       'MAXWELL', 'MESHACK', 'MORGAN', 'OWEN', 'DANIEL', 'DERRICK', 'DYLAN', 
                       'EMMANUEL', 'GRAVINS', 'IBURA', 'JAYDEN', 'LAMECK', 'ROBERT', 'RYAN', 
                       'WAYNE', 'BRAMWEL', 'DAVID', 'KYLE', 'PHRAEL', 'ARON', 'EMMANUEL', 
                       'GIFTON', 'GLEN', 'JOHNSON', 'MOSES', 'ROBINSON', 'WALTER', 
                       'ALBERT', 'BRIAN', 'DANIEL', 'EMMANUEL', 'JAYDEN', 'KELVIN', 
                       'MAXWELL', 'MITCHEL', 'NICHOLAS', 'ZADDOCK']
    
    for indicator in female_indicators:
        if indicator in name_upper:
            return 'Female'
    
    for indicator in male_indicators:
        if indicator in name_upper:
            return 'Male'
    
    # Default: random if can't determine
    return random.choice(['Male', 'Female'])

def generate_date_of_birth(grade):
    """Generate a date of birth based on grade"""
    age_min, age_max = AGE_RANGES.get(grade, (5, 6))
    age = random.randint(age_min, age_max)
    birth_date = datetime.now() - timedelta(days=age * 365 + random.randint(0, 364))
    return birth_date.date()

def generate_parent_name(student_name):
    """Generate a parent name based on student name"""
    return f"PARENT TO {student_name}"

def generate_phone():
    """Generate a Kenyan phone number"""
    prefixes = ['070', '071', '072', '073', '074', '075', '076', '077', '078', '079']
    return f"{random.choice(prefixes)}{random.randint(1000000, 9999999)}"

def generate_email(name):
    """Generate an email from name"""
    # Clean name for email
    email_name = re.sub(r'[^A-Z0-9]', '', name.upper().replace(' ', ''))
    return f"{email_name.lower()}@example.com"

def insert_students():
    """Insert all students into the database"""
    try:
        connection = pymysql.connect(**DB_CONFIG)
        print(f"Connected to database: {DB_CONFIG['database']}")
        
        total_students = sum(len(students) for students in STUDENTS_BY_GRADE.values())
        print(f"Total students to insert: {total_students}")
        print("=" * 60)
        
        inserted_count = 0
        skipped_count = 0
        
        with connection.cursor() as cursor:
            for grade, students in STUDENTS_BY_GRADE.items():
                print(f"\nProcessing {grade}: {len(students)} students")
                
                for student_name in students:
                    try:
                        # Check if student already exists
                        cursor.execute("SELECT student_id FROM students WHERE full_name = %s", (student_name,))
                        student_result = cursor.fetchone()
                        
                        if student_result:
                            # Student exists, get their student_id
                            student_id = student_result['student_id']
                            skipped_count += 1
                        else:
                            # Generate student ID for new student
                            student_id = generate_student_id(connection)
                            
                            # Generate student data
                            gender = guess_gender(student_name)
                            date_of_birth = generate_date_of_birth(grade)
                            current_grade = grade
                            
                            # Insert student
                            student_sql = """
                                INSERT INTO students 
                                (student_id, full_name, date_of_birth, gender, current_grade, 
                                 status, student_category)
                                VALUES (%s, %s, %s, %s, %s, 'in session', 'self sponsored')
                            """
                            cursor.execute(student_sql, (
                                student_id, student_name, date_of_birth, gender, current_grade
                            ))
                            inserted_count += 1
                        
                        # Always insert/update parent for the student
                        parent_name = generate_parent_name(student_name)
                        parent_phone = generate_phone()
                        parent_email = generate_email(parent_name)
                        relationship = random.choice(['Mother', 'Father', 'Guardian'])
                        emergency_contact = generate_phone()
                        
                        # Check if parent exists
                        cursor.execute("SELECT id FROM parents WHERE student_id = %s", (student_id,))
                        if not cursor.fetchone():
                            # Insert new parent
                            parent_sql = """
                                INSERT INTO parents 
                                (student_id, full_name, phone, email, relationship, emergency_contact)
                                VALUES (%s, %s, %s, %s, %s, %s)
                            """
                            cursor.execute(parent_sql, (
                                student_id, parent_name, parent_phone, parent_email, 
                                relationship, emergency_contact
                            ))
                        else:
                            # Update existing parent
                            update_parent_sql = """
                                UPDATE parents 
                                SET full_name = %s, phone = %s, email = %s, 
                                    relationship = %s, emergency_contact = %s
                                WHERE student_id = %s
                            """
                            cursor.execute(update_parent_sql, (
                                parent_name, parent_phone, parent_email, 
                                relationship, emergency_contact, student_id
                            ))
                        
                        if inserted_count > 0 and inserted_count % 10 == 0:
                            print(f"  [OK] Processed {inserted_count + skipped_count} students so far...")
                        
                    except Exception as e:
                        print(f"  [ERROR] Error processing {student_name}: {e}")
                        connection.rollback()
                        continue
                
                # Commit after each grade
                connection.commit()
                print(f"  [OK] Completed {grade}")
        
        print("\n" + "=" * 60)
        print(f"Insertion complete!")
        print(f"  [OK] Successfully inserted: {inserted_count} students")
        print(f"  [SKIP] Skipped (already exists): {skipped_count} students")
        print(f"  Total processed: {inserted_count + skipped_count} students")
        
        connection.close()
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    print("Student Insertion Script")
    print("=" * 60)
    import sys
    # Check if running in non-interactive mode or if '--yes' flag is provided
    if len(sys.argv) > 1 and sys.argv[1] == '--yes':
        insert_students()
    else:
        try:
            confirm = input("This will insert students into the database. Continue? (yes/no): ")
            if confirm.lower() == 'yes':
                insert_students()
            else:
                print("Cancelled.")
        except EOFError:
            # Non-interactive mode - proceed automatically
            print("Running in non-interactive mode...")
            insert_students()

