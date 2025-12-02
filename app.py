from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_session import Session
import pymysql
import pymysql.err
from pymysql.cursors import DictCursor
from functools import wraps
import os
from datetime import datetime
import secrets
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['SECRET_KEY'] = secrets.token_hex(16)
app.config['SESSION_TYPE'] = 'filesystem'
app.config['UPLOAD_FOLDER'] = 'static/images/students'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
Session(app)

# Create upload directory if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

# Database configuration
# Supports both local and hosted environments via environment variables
# Default values are set for hosted environment (groundle_school)
# Override with .env file for local development
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'user': os.getenv('DB_USER', 'groundle_school'),
    'password': os.getenv('DB_PASSWORD', 'Itskimathi007'),
    'database': os.getenv('DB_NAME', 'groundle_school'),
    'charset': 'utf8mb4',
    'cursorclass': DictCursor
}

def get_db_connection():
    """Create and return a database connection"""
    try:
        connection = pymysql.connect(**DB_CONFIG)
        return connection
    except pymysql.err.OperationalError as e:
        if e.args[0] == 1049:  # Unknown database
            # Try to create the database
            try:
                temp_config = DB_CONFIG.copy()
                temp_config.pop('database')
                temp_conn = pymysql.connect(**temp_config)
                with temp_conn.cursor() as cursor:
                    cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_CONFIG['database']} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
                    temp_conn.commit()
                temp_conn.close()
                # Now try connecting again
                connection = pymysql.connect(**DB_CONFIG)
                return connection
            except Exception as create_error:
                print(f"Error creating database: {create_error}")
                return None
        else:
            print(f"Database connection error: {e}")
            return None
    except Exception as e:
        print(f"Database connection error: {e}")
        return None

def init_db():
    """Initialize database with required tables"""
    connection = get_db_connection()
    if not connection:
        return False
    
    try:
        with connection.cursor() as cursor:
            # Users table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    username VARCHAR(100) UNIQUE NOT NULL,
                    email VARCHAR(255) UNIQUE NOT NULL,
                    password VARCHAR(255) NOT NULL,
                    full_name VARCHAR(255) NOT NULL,
                    role ENUM('student', 'parent', 'teacher', 'admin') NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT TRUE
                )
            """)
            
            # Students table for sponsorship intake
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS students (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT,
                    child_full_name VARCHAR(255) NOT NULL,
                    current_age INT,
                    birth_date DATE,
                    gender ENUM('Male', 'Female') NOT NULL,
                    physical_appearance TEXT,
                    case_history TEXT NOT NULL,
                    living_conditions TEXT,
                    household_chores TEXT,
                    sibling_information TEXT NOT NULL,
                    has_siblings_in_program ENUM('Yes', 'No') NOT NULL,
                    sibling_names TEXT,
                    interests_hobbies TEXT,
                    school_name VARCHAR(255),
                    current_class VARCHAR(100),
                    favorite_subjects TEXT,
                    future_aspirations TEXT,
                    additional_comments TEXT,
                    status ENUM('Pending Approval', 'Active', 'Suspended', 'Completed', 'Expelled') DEFAULT 'Pending Approval',
                    profile_image VARCHAR(500),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
                )
            """)
            
            # Student images table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS student_images (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    student_id INT NOT NULL,
                    image_url VARCHAR(500) NOT NULL,
                    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
                )
            """)
            
            # Posts/News table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS posts (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    title VARCHAR(255) NOT NULL,
                    content TEXT NOT NULL,
                    author_id INT,
                    category VARCHAR(100),
                    image_url VARCHAR(500),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (author_id) REFERENCES users(id) ON DELETE SET NULL
                )
            """)
            
            # Events table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    title VARCHAR(255) NOT NULL,
                    description TEXT,
                    event_date DATE NOT NULL,
                    event_time TIME,
                    location VARCHAR(255),
                    image_url VARCHAR(500),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Programs table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS programs (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    description TEXT,
                    grade_level VARCHAR(50),
                    category VARCHAR(100),
                    image_url VARCHAR(500)
                )
            """)
            
            # Gallery table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS gallery (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    title VARCHAR(255),
                    image_url VARCHAR(500) NOT NULL,
                    category VARCHAR(100),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Testimonials table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS testimonials (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    role VARCHAR(100),
                    content TEXT NOT NULL,
                    image_url VARCHAR(500),
                    rating INT DEFAULT 5,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Staff table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS staff (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    position VARCHAR(255),
                    qualifications TEXT,
                    bio TEXT,
                    image_url VARCHAR(500),
                    email VARCHAR(255),
                    subjects VARCHAR(255)
                )
            """)
            
            connection.commit()
            
            # Create default admin user if not exists
            cursor.execute("SELECT COUNT(*) as count FROM users WHERE role = 'admin'")
            if cursor.fetchone()['count'] == 0:
                cursor.execute("""
                    INSERT INTO users (username, email, password, full_name, role)
                    VALUES ('admin', 'admin@school.com', 'admin123', 'Administrator', 'admin')
                """)
                connection.commit()
            
        return True
    except Exception as e:
        print(f"Database initialization error: {e}")
        return False
    finally:
        connection.close()

# Decorator for role-based access
def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash('Please log in to access this page.', 'warning')
                return redirect(url_for('login'))
            user_role = session.get('user_role')
            if user_role not in roles:
                flash('You do not have permission to access this page.', 'danger')
                return redirect(url_for('dashboard'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Public routes
@app.route('/')
def index():
    connection = get_db_connection()
    testimonials = []
    events = []
    posts = []
    
    if connection:
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT * FROM testimonials ORDER BY created_at DESC LIMIT 6")
                testimonials = cursor.fetchall()
                
                cursor.execute("SELECT * FROM events WHERE event_date >= CURDATE() ORDER BY event_date ASC LIMIT 3")
                events = cursor.fetchall()
                
                cursor.execute("SELECT p.*, u.full_name as author_name FROM posts p LEFT JOIN users u ON p.author_id = u.id ORDER BY p.created_at DESC LIMIT 3")
                posts = cursor.fetchall()
        except Exception as e:
            print(f"Error fetching data: {e}")
        finally:
            connection.close()
    
    return render_template('index.html', testimonials=testimonials, events=events, posts=posts)

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/programs')
def programs():
    connection = get_db_connection()
    programs_list = []
    
    if connection:
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT * FROM programs ORDER BY grade_level, name")
                programs_list = cursor.fetchall()
        except Exception as e:
            print(f"Error fetching programs: {e}")
        finally:
            connection.close()
    
    return render_template('programs.html', programs=programs_list)

@app.route('/admissions', methods=['GET', 'POST'])
def admissions():
    if request.method == 'POST':
        # Handle form submission
        try:
            # Get form data
            child_full_name = request.form.get('child_full_name')
            current_age = request.form.get('current_age')
            birth_date = request.form.get('birth_date')
            gender = request.form.get('gender')
            physical_appearance = request.form.get('physical_appearance')
            case_history = request.form.get('case_history')
            living_conditions = request.form.get('living_conditions')
            household_chores = request.form.get('household_chores')
            sibling_information = request.form.get('sibling_information')
            has_siblings_in_program = request.form.get('has_siblings_in_program')
            sibling_names = request.form.get('sibling_names')
            interests_hobbies = request.form.get('interests_hobbies')
            school_name = request.form.get('school_name')
            current_class = request.form.get('current_class')
            favorite_subjects = request.form.get('favorite_subjects')
            future_aspirations = request.form.get('future_aspirations')
            additional_comments = request.form.get('additional_comments')
            
            # Handle file uploads
            profile_image = None
            image_urls = []
            
            def allowed_file(filename):
                ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
                return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
            
            if 'profile_image' in request.files:
                file = request.files['profile_image']
                if file and file.filename and allowed_file(file.filename):
                    filename = secure_filename(f"profile_{child_full_name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d%H%M%S')}.{file.filename.rsplit('.', 1)[1].lower()}")
                    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    file.save(filepath)
                    profile_image = f"static/images/students/{filename}"
            
            # Handle multiple image uploads (up to 5)
            if 'child_images' in request.files:
                files = request.files.getlist('child_images')
                for idx, file in enumerate(files[:5]):  # Limit to 5 files
                    if file and file.filename and allowed_file(file.filename):
                        filename = secure_filename(f"child_{child_full_name.replace(' ', '_')}_{idx}_{datetime.now().strftime('%Y%m%d%H%M%S')}.{file.filename.rsplit('.', 1)[1].lower()}")
                        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                        file.save(filepath)
                        image_urls.append(f"static/images/students/{filename}")
            
            connection = get_db_connection()
            if connection:
                try:
                    with connection.cursor() as cursor:
                        # Get or create user for the student
                        user_id = None
                        if session.get('user_id'):
                            user_id = session['user_id']
                        else:
                            # Create a temporary user account
                            email = request.form.get('email', f"{child_full_name.replace(' ', '.').lower()}@school.com")
                            username = child_full_name.replace(' ', '.').lower()
                            cursor.execute(
                                "INSERT INTO users (username, email, password, full_name, role) VALUES (%s, %s, %s, %s, 'student')",
                                (username, email, 'temp123', child_full_name)
                            )
                            connection.commit()
                            user_id = cursor.lastrowid
                        
                        # Insert student record
                        cursor.execute("""
                            INSERT INTO students (
                                user_id, child_full_name, current_age, birth_date, gender,
                                physical_appearance, case_history, living_conditions, household_chores,
                                sibling_information, has_siblings_in_program, sibling_names,
                                interests_hobbies, school_name, current_class, favorite_subjects,
                                future_aspirations, additional_comments, status, profile_image
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """, (
                            user_id, child_full_name, current_age, birth_date, gender,
                            physical_appearance, case_history, living_conditions, household_chores,
                            sibling_information, has_siblings_in_program, sibling_names,
                            interests_hobbies, school_name, current_class, favorite_subjects,
                            future_aspirations, additional_comments, 'Pending Approval', profile_image
                        ))
                        student_id = cursor.lastrowid
                        
                        # Insert student images
                        for image_url in image_urls:
                            cursor.execute(
                                "INSERT INTO student_images (student_id, image_url) VALUES (%s, %s)",
                                (student_id, image_url)
                            )
                        
                        connection.commit()
                        flash('Application submitted successfully! Your application is now pending approval.', 'success')
                        return redirect(url_for('admissions'))
                except Exception as e:
                    print(f"Error saving application: {e}")
                    flash('An error occurred while submitting your application. Please try again.', 'danger')
                finally:
                    connection.close()
        except Exception as e:
            print(f"Form processing error: {e}")
            flash('An error occurred. Please check all required fields and try again.', 'danger')
    
    return render_template('admissions.html')

@app.route('/news')
def news():
    connection = get_db_connection()
    posts_list = []
    
    if connection:
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT p.*, u.full_name as author_name FROM posts p LEFT JOIN users u ON p.author_id = u.id ORDER BY p.created_at DESC")
                posts_list = cursor.fetchall()
        except Exception as e:
            print(f"Error fetching posts: {e}")
        finally:
            connection.close()
    
    return render_template('news.html', posts=posts_list)

@app.route('/events')
def events():
    connection = get_db_connection()
    events_list = []
    
    if connection:
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT * FROM events ORDER BY event_date DESC")
                events_list = cursor.fetchall()
        except Exception as e:
            print(f"Error fetching events: {e}")
        finally:
            connection.close()
    
    return render_template('events.html', events=events_list)

@app.route('/gallery')
def gallery():
    connection = get_db_connection()
    gallery_items = []
    
    if connection:
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT * FROM gallery ORDER BY created_at DESC")
                gallery_items = cursor.fetchall()
        except Exception as e:
            print(f"Error fetching gallery: {e}")
        finally:
            connection.close()
    
    return render_template('gallery.html', gallery_items=gallery_items)

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        # Handle contact form submission
        name = request.form.get('name')
        email = request.form.get('email')
        message = request.form.get('message')
        purpose = request.form.get('purpose')
        
        # Here you would typically save to database or send email
        flash('Thank you for your message. We will get back to you soon!', 'success')
        return redirect(url_for('contact'))
    
    return render_template('contact.html')

@app.route('/ngo')
def ngo():
    return render_template('ngo.html')

@app.route('/donate', methods=['GET', 'POST'])
def donate():
    if request.method == 'POST':
        # Handle donation form
        flash('Thank you for your donation!', 'success')
        return redirect(url_for('donate'))
    
    return render_template('donate.html')

@app.route('/staff')
def staff():
    connection = get_db_connection()
    staff_list = []
    
    if connection:
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT * FROM staff ORDER BY position, name")
                staff_list = cursor.fetchall()
        except Exception as e:
            print(f"Error fetching staff: {e}")
        finally:
            connection.close()
    
    return render_template('staff.html', staff_list=staff_list)

# Authentication routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        connection = get_db_connection()
        if connection:
            try:
                with connection.cursor() as cursor:
                    cursor.execute(
                        "SELECT * FROM users WHERE username = %s AND password = %s AND is_active = TRUE",
                        (username, password)
                    )
                    user = cursor.fetchone()
                    
                    if user:
                        session['user_id'] = user['id']
                        session['username'] = user['username']
                        session['user_role'] = user['role']
                        session['full_name'] = user['full_name']
                        flash(f'Welcome back, {user["full_name"]}!', 'success')
                        return redirect(url_for('dashboard'))
                    else:
                        flash('Invalid username or password.', 'danger')
            except Exception as e:
                print(f"Login error: {e}")
                flash('An error occurred. Please try again.', 'danger')
            finally:
                connection.close()
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        full_name = request.form.get('full_name')
        role = request.form.get('role', 'student')
        
        connection = get_db_connection()
        if connection:
            try:
                with connection.cursor() as cursor:
                    cursor.execute(
                        "INSERT INTO users (username, email, password, full_name, role) VALUES (%s, %s, %s, %s, %s)",
                        (username, email, password, full_name, role)
                    )
                    connection.commit()
                    flash('Registration successful! Please log in.', 'success')
                    return redirect(url_for('login'))
            except Exception as e:
                print(f"Registration error: {e}")
                flash('Registration failed. Username or email may already exist.', 'danger')
            finally:
                connection.close()
    
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('index'))

# Dashboard routes
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        flash('Please log in to access the dashboard.', 'warning')
        return redirect(url_for('login'))
    
    user_role = session.get('user_role')
    
    if user_role == 'student':
        return redirect(url_for('student_dashboard'))
    elif user_role == 'parent':
        return redirect(url_for('parent_dashboard'))
    elif user_role == 'teacher':
        return redirect(url_for('teacher_dashboard'))
    elif user_role == 'admin':
        return redirect(url_for('admin_dashboard'))
    
    return redirect(url_for('index'))

@app.route('/dashboard/student')
@role_required('student')
def student_dashboard():
    connection = get_db_connection()
    student_data = None
    
    if connection:
        try:
            with connection.cursor(DictCursor) as cursor:
                cursor.execute("""
                    SELECT s.*, 
                           GROUP_CONCAT(si.image_url) as images
                    FROM students s
                    LEFT JOIN student_images si ON s.id = si.student_id
                    WHERE s.user_id = %s
                    GROUP BY s.id
                    ORDER BY s.created_at DESC
                    LIMIT 1
                """, (session['user_id'],))
                student_data = cursor.fetchone()
        except Exception as e:
            print(f"Error fetching student data: {e}")
        finally:
            connection.close()
    
    return render_template('dashboards/student.html', student_data=student_data)

@app.route('/dashboard/parent')
@role_required('parent')
def parent_dashboard():
    return render_template('dashboards/parent.html')

@app.route('/dashboard/teacher')
@role_required('teacher')
def teacher_dashboard():
    return render_template('dashboards/teacher.html')

@app.route('/dashboard/admin')
@role_required('admin')
def admin_dashboard():
    connection = get_db_connection()
    stats = {}
    
    if connection:
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) as count FROM users WHERE role = 'student'")
                stats['students'] = cursor.fetchone()['count']
                
                cursor.execute("SELECT COUNT(*) as count FROM users WHERE role = 'teacher'")
                stats['teachers'] = cursor.fetchone()['count']
                
                cursor.execute("SELECT COUNT(*) as count FROM posts")
                stats['posts'] = cursor.fetchone()['count']
                
                cursor.execute("SELECT COUNT(*) as count FROM events")
                stats['events'] = cursor.fetchone()['count']
        except Exception as e:
            print(f"Error fetching stats: {e}")
        finally:
            connection.close()
    
    return render_template('dashboards/admin.html', stats=stats)

# API route for dark mode toggle
@app.route('/api/toggle-theme', methods=['POST'])
def toggle_theme():
    theme = request.json.get('theme', 'light')
    session['theme'] = theme
    return jsonify({'success': True, 'theme': theme})

if __name__ == '__main__':
    # Initialize database on first run
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)

