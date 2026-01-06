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

4. **Configure environment variables**:
   - Copy `env.example` to `.env`:
     ```bash
     cp env.example .env
     ```
   - **IMPORTANT**: Edit `.env` and set all required values:
     - **SECRET_KEY**: Generate a secure random key:
       ```bash
       python -c "import secrets; print(secrets.token_hex(32))"
       ```
     - **Database credentials**: The app automatically detects if running on localhost or cPanel/hosted:
       - **Localhost**: Uses defaults (localhost, root, modern_school)
       - **cPanel/Hosted**: Uses cPanel defaults (projectl_school credentials)
       - You can override by setting `DB_HOST`, `DB_USER`, `DB_PASSWORD`, and `DB_NAME`
       - To force detection, set `DEPLOYMENT_ENV=development` (localhost) or `DEPLOYMENT_ENV=production` (hosted)
     - **Email settings** (optional): Configure if using email features
   
   - **Security Note**: Never commit `.env` to version control! It's already in `.gitignore`.

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
- Environment variable configuration (no hardcoded credentials)
- Automatic validation of critical environment variables
- Secure file upload handling

## Development

### Adding New Features

1. **New Page**: Create a new template in `templates/` and add a route in `app.py`
2. **New Database Table**: Add table creation SQL in `create_db.py` and `app.py`'s `init_db()` function
3. **New Dashboard**: Create template in `templates/dashboards/` and add protected route in `app.py`

### Customization

- **Styling**: Modify Tailwind classes in templates or add custom CSS in `static/css/`
- **JavaScript**: Add functionality in `static/js/main.js`
- **Database**: Modify schema in `create_db.py` and `app.py`

## Environment Variables

### Automatic Environment Detection
The application automatically detects whether it's running on **localhost** (development) or **cPanel/hosted** (production) and uses appropriate database defaults:

- **Localhost Detection**: Uses defaults for local development
  - Host: `localhost`
  - User: `root`
  - Database: `modern_school`
  
- **cPanel/Hosted Detection**: Uses cPanel defaults when not on localhost
  - Host: `localhost` (cPanel MySQL)
  - User: `projectl_school`
  - Database: `projectl_school`

You can override these defaults by setting environment variables, or force detection by setting `DEPLOYMENT_ENV`:
- `DEPLOYMENT_ENV=development` - Forces localhost defaults
- `DEPLOYMENT_ENV=production` - Forces cPanel/hosted defaults

### Required Variables
The following environment variables **must** be set in your `.env` file:

- `SECRET_KEY` - Flask secret key (generate with: `python -c "import secrets; print(secrets.token_hex(32))"`)

**Database variables are optional** (defaults are used based on environment detection):
- `DB_HOST` - Database host (defaults: `localhost` for both environments)
- `DB_USER` - Database username (defaults: `root` for localhost, `projectl_school` for hosted)
- `DB_PASSWORD` - Database password (defaults: empty for localhost, cPanel password for hosted)
- `DB_NAME` - Database name (defaults: `modern_school` for localhost, `projectl_school` for hosted)

### Optional Variables
- `FLASK_ENV` - Flask environment (`development` or `production`)
- `FLASK_DEBUG` - Enable/disable debug mode (`True` or `False`)
- `MAIL_SERVER`, `MAIL_PORT`, `MAIL_USERNAME`, `MAIL_PASSWORD` - Email configuration
- `SUPPORT_EMAIL`, `SUPPORT_PHONE`, `SCHOOL_NAME` - Support contact information

### Security Best Practices
1. **Never commit `.env` files** - They are automatically ignored by `.gitignore`
2. **Use strong SECRET_KEY** - Generate a random 64-character hex string
3. **Use different credentials for production** - Never use development credentials in production
4. **Review `env.example`** - It shows all available configuration options

## Troubleshooting

### Database Connection Issues
- Verify MySQL is running
- Check database credentials in `.env` file
- Ensure database exists: `CREATE DATABASE modern_school;`
- Check that all required environment variables are set

### Environment Variable Issues
- Ensure `.env` file exists in the project root
- Verify all required variables are set (app will show warnings if missing)
- In production, ensure `FLASK_ENV=production` and `SECRET_KEY` is set to a secure value

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


