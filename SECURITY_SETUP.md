# Security Setup Guide

## Critical: SECRET_KEY Configuration

Your application is currently using a default or empty SECRET_KEY, which is a **critical security vulnerability**. This must be fixed immediately.

### Generated Secure SECRET_KEY

Use this secure key (generated on 2025-01-27):

```
36efd7370f7b3c6d69f06b557256978ff877f0c3076ce781cb107408f43adec1
```

**⚠️ IMPORTANT:** Keep this key secret and never commit it to version control!

### How to Set SECRET_KEY in cPanel/Hosted Environment

#### Option 1: Using cPanel Environment Variables (Recommended)

1. Log into your cPanel account
2. Navigate to **"Environment Variables"** or **"Setup Python App"** (depending on your cPanel version)
3. Add a new environment variable:
   - **Variable Name:** `SECRET_KEY`
   - **Variable Value:** `36efd7370f7b3c6d69f06b557256978ff877f0c3076ce781cb107408f43adec1`
4. Save and restart your application

#### Option 2: Using .env File

1. Connect to your server via SSH or File Manager
2. Navigate to your application root directory: `/home1/projectl/project_lucas/`
3. Create or edit the `.env` file
4. Add this line:
   ```
   SECRET_KEY=36efd7370f7b3c6d69f06b557256978ff877f0c3076ce781cb107408f43adec1
   ```
5. Make sure `.env` is in `.gitignore` (it should already be)
6. Restart your application

#### Option 3: Using Passenger/WSGI Configuration

If you're using Passenger (which appears to be the case), you can also set environment variables in your `.htaccess` file or Passenger configuration:

```apache
SetEnv SECRET_KEY 36efd7370f7b3c6d69f06b557256978ff877f0c3076ce781cb107408f43adec1
```

### Verify the Fix

After setting the SECRET_KEY, restart your application and check the logs. You should **NOT** see the security warning anymore.

### Generate a New Key (Optional)

If you want to generate a new unique key, run this command:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### Additional Security Recommendations

1. **Never commit .env files** - Already in `.gitignore` ✓
2. **Use HTTPS** - Ensure your site uses SSL/TLS
3. **Keep dependencies updated** - Regularly update packages in `requirements.txt`
4. **Review access logs** - Monitor for suspicious activity
5. **Use strong database passwords** - Already configured ✓

### Troubleshooting

If you still see the warning after setting SECRET_KEY:

1. **Check file permissions** - Ensure `.env` file is readable by the web server
2. **Restart the application** - Environment variables require a restart
3. **Check variable name** - Ensure it's exactly `SECRET_KEY` (case-sensitive)
4. **Check for typos** - Verify the key value is correct
5. **Clear any caches** - Some systems cache environment variables

### Need Help?

If you continue to see the security warning after following these steps, check:
- Application error logs in cPanel
- Passenger/WSGI logs
- Server error logs

---

**Last Updated:** 2025-01-27
**Status:** ⚠️ Action Required - Set SECRET_KEY immediately

