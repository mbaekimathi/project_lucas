# Modern School Website

A professional, responsive school website built with Flask, TailwindCSS, and PyMySQL. Features dark/light mode, role-based dashboards, and a modern Neo-Classical design.

## Features

- 🎨 Modern Neo-Classical/Professional design
- 🌓 Dark/Light mode toggle
- 📱 Fully responsive (Desktop, Tablet, Mobile)
- 👥 Role-based dashboards (Student, Parent, Teacher, Admin)
- ✨ Smooth animations and transitions
- 🗄️ MySQL database integration
- 🔐 User authentication and authorization

## Installation

1. **Clone or download the project**

2. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up MySQL database:**
   
   The application is configured to work with both **local** and **hosted** environments.
   
   **Default Database Configuration (Hosted):**
   - Host: `localhost`
   - User: `groundle_school`
   - Password: `Itskimathi007`
   - Database: `groundle_school`
   
   **For Local Development:**
   
   Create a `.env` file in the project root to override defaults:
   ```
   DB_HOST=localhost
   DB_USER=root
   DB_PASSWORD=your_local_password
   DB_NAME=school_db
   ```
   
   **For Hosted Environment:**
   
   The application will automatically use the hosted credentials (groundle_school) if no `.env` file is present. You can also explicitly set them in `.env`:
   ```
   DB_HOST=localhost
   DB_USER=groundle_school
   DB_PASSWORD=Itskimathi007
   DB_NAME=groundle_school
   ```
   
   **Note:** The `.env` file is gitignored for security. Create it locally as needed.

4. **Run the application:**
   ```bash
   python app.py
   ```

5. **Access the website:**
   - Open your browser and navigate to `http://localhost:5000`
   - Default admin credentials:
     - Username: `admin`
     - Password: `admin123`

## Project Structure

```
.
├── app.py                 # Flask application
├── requirements.txt       # Python dependencies
├── templates/            # HTML templates
│   ├── base.html         # Base template
│   ├── index.html        # Home page
│   ├── about.html        # About page
│   ├── programs.html     # Programs page
│   ├── admissions.html   # Admissions page
│   ├── news.html         # News/Blog page
│   ├── events.html       # Events page
│   ├── gallery.html      # Gallery page
│   ├── contact.html      # Contact page
│   ├── ngo.html          # NGO page
│   ├── donate.html       # Donate page
│   ├── staff.html        # Staff page
│   ├── login.html        # Login page
│   ├── register.html     # Registration page
│   └── dashboards/       # Role-based dashboards
│       ├── student.html
│       ├── parent.html
│       ├── teacher.html
│       └── admin.html
└── static/               # Static files
    ├── css/              # Custom CSS
    ├── js/               # JavaScript files
    └── images/           # Images and assets
```

## Pages

### Public Pages
- **Home**: Hero banner, testimonials, quick navigation
- **About Us**: School history, mission, vision, values
- **Programs**: Academic programs by grade level
- **Admissions**: Application process and requirements
- **News & Events**: Latest news and upcoming events
- **Gallery**: Photo and video gallery
- **Contact**: Contact form and school information
- **NGO**: NGO sponsor information
- **Donate**: Donation options and payment
- **Staff**: Faculty and staff directory

### Dashboard Pages (Logged-in Users)
- **Student Dashboard**: Timetable, assignments, results, fees
- **Parent Dashboard**: Child's attendance, grades, fee status
- **Teacher Dashboard**: Class list, grading, assignments
- **Admin Dashboard**: Full administrative controls

## Customization

### Colors
Edit the TailwindCSS classes in templates to customize colors. The default theme uses:
- Primary: Blue (#1C6DD0)
- Success: Green (#10B981)
- Dark mode: Dark greys and navy

### Database
The application automatically creates tables on first run. You can manually add data or use the admin dashboard (when implemented).

## Security Notes

⚠️ **Important**: This is a development version. For production:
- Use proper password hashing (bcrypt, argon2)
- Implement CSRF protection
- Use environment variables for sensitive data
- Enable HTTPS
- Add rate limiting
- Implement proper session management

## License

This project is open source and available for educational purposes.

## Support

For issues or questions, please contact the development team.

