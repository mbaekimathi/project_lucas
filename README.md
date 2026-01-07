# Modern School - Flask Web Application

A comprehensive Flask-based school management system with role-based dashboards, admission forms, and a modern responsive UI built with Tailwind CSS.

## Features

- **Public Pages**: Home, About, Programs, News/Events, Gallery, Contact
- **Admission System**: Complete online admission form with validation
- **User Authentication**: Role-based login (Parent, Student, Employee)
- **Role Dashboards**: Customized dashboards for each user role
- **Responsive Design**: Mobile-first design with Tailwind CSS
- **Database Integration**: MySQL database with PyMySQL

## Requirements

- Python 3.8+
- MySQL 5.7+ or MariaDB 10.3+
- pip (Python package manager)

## Installation

1. **Clone the repository** (or navigate to the project directory)

2. **Create a virtual environment** (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**:
```bash
pip install -r requirements.txt
```

4. **Set up MySQL database**:
   - Create a MySQL database
   - Update database credentials in `env.example` and rename it to `.env`
   - Or set environment variables:
     ```bash
     export DB_HOST=localhost
     export DB_USER=root
     export DB_PASSWORD=your_password
     export DB_NAME=modern_school
     export SECRET_KEY=your-secret-key
     ```

5. **Initialize the database**:
```bash
python create_db.py
```

This will:
- Create the database if it doesn't exist
- Create all required tables
- Optionally create sample users for testing

## Running the Application

1. **Start the Flask development server**:
```bash
python app.py
```

2. **Access the application**:
   - Open your browser and navigate to `http://localhost:5000`

## Default Login Credentials

If you created sample users during database initialization:

- **Parent**: parent@example.com / password123
- **Student**: student@example.com / password123
- **Employee**: employee@example.com / password123

## Project Structure

```
project_lucas_school/
│
├── app.py                 # Main Flask application
├── create_db.py           # Database initialization script
├── requirements.txt       # Python dependencies
├── env.example            # Environment variables template
├── README.md              # This file
│
├── templates/             # Jinja2 templates
│   ├── base.html          # Base template with header/sidebar/footer
│   ├── home.html          # Home page
│   ├── about.html         # About page
│   ├── programs.html      # Programs page
│   ├── news.html          # News & Events page
│   ├── gallery.html       # Gallery page
│   ├── contact.html       # Contact page
│   ├── admission_form.html # Admission form
│   ├── login.html         # Login page
│   └── dashboards/        # Dashboard templates
│       ├── dashboard_parent.html
│       ├── dashboard_student.html
│       └── dashboard_employee.html
│
└── static/                # Static files
    ├── css/               # Custom CSS (if any)
    ├── js/                # JavaScript files
    │   └── main.js        # Main JavaScript file
    └── img/               # Images
```

## Database Schema

### Users Table
- `id`: Primary key
- `full_name`: User's full name
- `email`: Unique email address
- `password_hash`: Hashed password
- `role`: User role (parent/student/employee)
- `created_at`: Account creation timestamp

### Admissions Table
- `id`: Primary key
- `student_full_name`: Student's name
- `date_of_birth`: Student's date of birth
- `gender`: Student's gender
- `current_grade`: Grade applying for
- `previous_school`: Previous school name
- `parent_name`: Parent/guardian name
- `parent_phone`: Parent phone number
- `parent_email`: Parent email
- `address`: Home address
- `emergency_contact`: Emergency contact info
- `medical_info`: Medical conditions
- `special_needs`: Special needs information
- `status`: Application status (default: pending)
- `submitted_at`: Submission timestamp

### News Table
- `id`: Primary key
- `title`: News title
- `summary`: News summary
- `content`: Full news content
- `image_url`: News image URL
- `date`: News date
- `created_at`: Creation timestamp

### Gallery Table
- `id`: Primary key
- `title`: Image title
- `description`: Image description
- `image_url`: Image URL
- `created_at`: Creation timestamp

## Routes

### Public Routes
- `/` - Home page
- `/about` - About page
- `/programs` - Programs page
- `/news` - News & Events page
- `/gallery` - Gallery page
- `/contact` - Contact page (GET/POST)
- `/admission` - Admission form (GET/POST)
- `/login` - Login page (GET/POST)
- `/logout` - Logout

### Protected Routes (Require Login)
- `/dashboard/parent` - Parent dashboard
- `/dashboard/student` - Student dashboard
- `/dashboard/employee` - Employee dashboard

## Features in Detail

### Forward-Only Navigation
Each page includes a "Next" button that navigates to the next page in sequence:
- Home → About
- About → Programs
- Programs → News
- News → Gallery
- Gallery → Contact
- Contact → Admission
- Admission → (no next button)

### Responsive Design
- Mobile-first approach
- Collapsible sidebar on mobile devices
- Responsive grid layouts
- Touch-friendly interface

### Security Features
- Password hashing with Werkzeug
- Session-based authentication
- Role-based access control
- SQL injection prevention with parameterized queries

## Development

### Adding New Features

1. **New Page**: Create a new template in `templates/` and add a route in `app.py`
2. **New Database Table**: Add table creation SQL in `create_db.py` and `app.py`'s `init_db()` function
3. **New Dashboard**: Create template in `templates/dashboards/` and add protected route in `app.py`

### Customization

- **Styling**: Modify Tailwind classes in templates or add custom CSS in `static/css/`
- **JavaScript**: Add functionality in `static/js/main.js`
- **Database**: Modify schema in `create_db.py` and `app.py`

## Troubleshooting

### Database Connection Issues
- Verify MySQL is running
- Check database credentials in environment variables
- Ensure database exists: `CREATE DATABASE modern_school;`

### Import Errors
- Ensure virtual environment is activated
- Run `pip install -r requirements.txt` again

### Template Not Found
- Verify template files are in `templates/` directory
- Check template names match route return values

## License

This project is for educational purposes.

## Support

For issues or questions, please check the code comments or create an issue in the repository.


