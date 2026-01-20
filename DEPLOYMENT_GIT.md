# Git Deployment Troubleshooting Guide

## Problem: 404 Error When Using Git vs Zip Upload Works

If your app works when you upload a zip file but gets a 404 when using git, follow these steps:

## Step 1: Verify Git Clone Path

When cloning the repository in cPanel Git Version Control:

1. **Repository Path** should be:
   ```
   /home1/projectl/project_lucas
   ```
   **NOT** `/home1/projectl/project_lucas/project_lucas` (this creates a nested directory)

2. **Clone URL**:
   ```
   https://github.com/mbaekimathi/project_lucas.git
   ```

## Step 2: Verify Python App Configuration

In cPanel → Setup Python App, ensure:

1. **Application root**: 
   ```
   /home1/projectl/project_lucas
   ```
   (Must match the git repository path exactly)

2. **Application startup file**: 
   ```
   passenger_wsgi.py
   ```

3. **Application Entry point**: 
   ```
   application
   ```

## Step 3: Verify Critical Files Exist

After cloning, verify these files exist in `/home1/projectl/project_lucas/`:

```bash
cd /home1/projectl/project_lucas
ls -la passenger_wsgi.py
ls -la .htaccess
ls -la app.py
```

All three files should exist. If `.htaccess` is missing, it might be hidden. Use:
```bash
ls -la | grep htaccess
```

## Step 4: Check File Permissions

Set correct permissions:
```bash
cd /home1/projectl/project_lucas
chmod 644 passenger_wsgi.py
chmod 644 .htaccess
chmod 644 app.py
chmod 755 templates
chmod 755 static
```

## Step 5: Pull Latest Code

After initial clone, always pull the latest:
```bash
cd /home1/projectl/project_lucas
git pull origin main
```

## Step 6: Verify .htaccess is Not Ignored

Check if `.htaccess` is in `.gitignore` (it shouldn't be):
```bash
grep htaccess .gitignore
```

If it shows up, remove it from `.gitignore` and commit:
```bash
git rm --cached .gitignore
# Edit .gitignore to remove .htaccess
git add .gitignore
git commit -m "Remove .htaccess from .gitignore"
git push origin main
```

## Step 7: Restart Application

After any changes:
1. Go to cPanel → Setup Python App
2. Click "Restart" or "Reload"
3. Wait 30 seconds
4. Test your domain

## Common Issues

### Issue 1: Nested Directory Structure
**Symptom**: Files are in `/home1/projectl/project_lucas/project_lucas/` instead of `/home1/projectl/project_lucas/`

**Solution**: 
- Delete the repository in cPanel Git Version Control
- Recreate with correct path: `/home1/projectl/project_lucas` (not a subdirectory)

### Issue 2: .htaccess Missing After Clone
**Symptom**: `.htaccess` file doesn't exist after git clone

**Solution**:
```bash
cd /home1/projectl/project_lucas
git pull origin main
# If still missing, manually create it or copy from working zip
```

### Issue 3: Wrong Application Root
**Symptom**: cPanel Python app points to wrong directory

**Solution**:
- Go to cPanel → Setup Python App
- Edit your app
- Set Application root to: `/home1/projectl/project_lucas`
- Save and restart

### Issue 4: Passenger Can't Find passenger_wsgi.py
**Symptom**: Error "cannot determine application type"

**Solution**:
1. Verify `passenger_wsgi.py` exists in application root
2. Check Application startup file is set to `passenger_wsgi.py`
3. Verify `.htaccess` exists with correct Passenger configuration

## Quick Fix Checklist

- [ ] Git repository path: `/home1/projectl/project_lucas`
- [ ] Python app root: `/home1/projectl/project_lucas` (matches git path)
- [ ] `passenger_wsgi.py` exists in root directory
- [ ] `.htaccess` exists in root directory
- [ ] `app.py` exists in root directory
- [ ] Application startup file: `passenger_wsgi.py`
- [ ] Application Entry point: `application`
- [ ] Pulled latest code: `git pull origin main`
- [ ] Restarted application in cPanel
- [ ] Checked error logs for specific errors

## Still Not Working?

1. **Check Passenger Error Logs** in cPanel → Errors
2. **Compare working zip structure** with git clone structure
3. **Verify all files are present**:
   ```bash
   cd /home1/projectl/project_lucas
   ls -la
   ```
4. **Check if files are in subdirectory**:
   ```bash
   find . -name "passenger_wsgi.py"
   find . -name ".htaccess"
   ```

## Need Help?

If still getting 404 after following all steps:
1. Check Passenger error logs
2. Verify the exact error message
3. Compare file structure between working zip and git clone
4. Ensure no files are missing or in wrong location







