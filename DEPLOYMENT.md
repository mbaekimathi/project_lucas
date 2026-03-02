# cPanel Deployment Guide - Project Lucas

This guide covers deploying the Flask app to cPanel with Passenger after pulling from GitHub.

## Prerequisites

- cPanel hosting with **Passenger** (Python WSGI) support
- MySQL database created in cPanel
- Git deployed or available (e.g., Git Version Control in cPanel)

---

## Step 1: Pull from GitHub

```bash
cd /home/your_username/public_html   # or your app directory
git pull origin main
```

---

## Step 2: Create Virtual Environment & Install Dependencies

```bash
# Create virtualenv (if not exists)
virtualenv -p python3 venv
source venv/bin/activate   # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Or if cPanel uses "Setup Python App", install via that interface
```

---

## Step 3: Environment Configuration

```bash
# Copy the example env file
cp .env.example .env

# Edit .env with your cPanel credentials
nano .env   # or use cPanel File Manager
```

**Required values in `.env`:**
- `IS_HOSTED=true`
- `SECRET_KEY` – generate a random string (e.g. `openssl rand -hex 32`)
- `DB_HOST`, `DB_USER`, `DB_PASSWORD`, `DB_NAME` – from cPanel MySQL

---

## Step 4: Update .htaccess

Update `PassengerAppRoot` in `.htaccess` to match your server path:

```
PassengerAppRoot /home/YOUR_CPANEL_USER/your_app_directory
```

To find your path: cPanel → File Manager → navigate to your app → check the path shown at the top.

If you don't have `.htaccess`, copy from the example:

```bash
cp .htaccess.example .htaccess
# Then edit .htaccess and set PassengerAppRoot
```

---

## Step 5: Database Setup (First Time Only)

```bash
python create_db.py   # Creates database and tables
# Or run migrations if tables exist:
python -c "from migrations.migration_manager import run_all_migrations; run_all_migrations()"
```

---

## Step 6: cPanel Application Setup

### Option A: Setup Python App (if available)

1. cPanel → **Setup Python App**
2. Create Application
3. Set **Application root** to your project directory
4. Set **Application startup file** to `passenger_wsgi.py`
5. Set **Application URL** (e.g. your domain or subdomain)
6. Use the Python path shown there for `PassengerPython` in `.htaccess` if needed

### Option B: Manual Passenger

Ensure these files exist in your app root:

- `passenger_wsgi.py` – WSGI entry point
- `.htaccess` – Passenger config (with correct `PassengerAppRoot`)
- `app.py` – Flask application

---

## Step 7: Restart the Application

- **Setup Python App**: Use "Restart" in the Python App interface
- **Manual**: Touch `passenger_wsgi.py` to trigger reload:
  ```bash
  touch passenger_wsgi.py
  ```

---

## File Checklist

| File | Purpose |
|------|---------|
| `passenger_wsgi.py` | WSGI entry point for Passenger |
| `.htaccess` | Apache/Passenger config (update path) |
| `.env` | Environment variables (create from .env.example) |
| `requirements.txt` | Python dependencies |
| `app.py` | Flask application |

---

## Troubleshooting

### 500 Internal Server Error
- Check **Passenger error logs** in cPanel (Metrics → Errors, or the application logs)
- Ensure `PassengerAppRoot` in `.htaccess` is correct
- Ensure all dependencies are installed: `pip install -r requirements.txt`

### Database Connection Failed
- Confirm `.env` has correct `DB_*` values
- Ensure MySQL user has access to the database
- Verify `IS_HOSTED=true` for production DB config

### Static Files Not Loading
- Ensure `static/` folder exists and is readable
- Check file permissions: `chmod -R 755 static/`

### "Application Error" Page
- View Passenger logs for the full traceback
- Run locally first: `python app.py` to catch import/syntax errors
