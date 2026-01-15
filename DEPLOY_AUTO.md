# Automatic Deployment Setup for cPanel

## Option A: GitHub Webhook + cPanel Script (Recommended)

### Step 1: Create Deployment Script in cPanel

1. Log into cPanel via SSH or Terminal
2. Create a deployment script:

```bash
cd /home1/projectl
nano deploy.sh
```

3. Add this content:

```bash
#!/bin/bash
cd /home1/projectl/project_lucas
git pull origin main
# Install/update dependencies if needed
source venv/bin/activate 2>/dev/null || true
pip install -r requirements.txt --quiet
# Restart Passenger (touch passenger_wsgi.py to trigger reload)
touch passenger_wsgi.py
echo "Deployment completed at $(date)"
```

4. Make it executable:
```bash
chmod +x deploy.sh
```

### Step 2: Set Up GitHub Webhook

1. Go to your GitHub repository: `https://github.com/mbaekimathi/project_lucas`
2. Go to Settings → Webhooks → Add webhook
3. Payload URL: `https://yourdomain.com/webhook/deploy` (you'll need to create this endpoint)
4. Content type: `application/json`
5. Events: Select "Just the push event"
6. Active: ✓

### Step 3: Create Webhook Endpoint in Flask App

Add this route to `app.py`:

```python
@app.route('/webhook/deploy', methods=['POST'])
def webhook_deploy():
    """GitHub webhook for automatic deployment"""
    import subprocess
    import hmac
    import hashlib
    
    # Verify webhook secret (optional but recommended)
    secret = os.environ.get('WEBHOOK_SECRET', '')
    if secret:
        signature = request.headers.get('X-Hub-Signature-256', '')
        if not signature:
            return jsonify({'error': 'Missing signature'}), 401
        
        expected = hmac.new(
            secret.encode(),
            request.data,
            hashlib.sha256
        ).hexdigest()
        
        if not hmac.compare_digest(f'sha256={expected}', signature):
            return jsonify({'error': 'Invalid signature'}), 401
    
    # Run deployment script
    try:
        result = subprocess.run(
            ['/home1/projectl/deploy.sh'],
            capture_output=True,
            text=True,
            timeout=60
        )
        return jsonify({
            'status': 'success',
            'output': result.stdout,
            'error': result.stderr
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
```

## Option B: cPanel Git Auto-Deploy (Simpler)

### Step 1: Enable Auto-Deploy in cPanel

1. Go to cPanel → Git Version Control
2. Click on your repository
3. Enable "Auto-Deploy" or "Deploy on Pull"
4. Set branch to `main`

### Step 2: Create Post-Receive Hook

In cPanel Git Version Control, add a post-receive hook:

```bash
#!/bin/bash
cd /home1/projectl/project_lucas
git pull origin main
touch passenger_wsgi.py  # Restart Passenger
```

## Option C: Manual Deployment (Current Method)

After pushing to GitHub:

1. **SSH into cPanel** or use Terminal:
   ```bash
   cd /home1/projectl/project_lucas
   git pull origin main
   ```

2. **Restart Python App** in cPanel:
   - Go to Setup Python App
   - Click "Restart" on your app

3. **Update Dependencies** (if needed):
   ```bash
   source venv/bin/activate
   pip install -r requirements.txt
   ```

## Database Updates

**Important**: Database schema changes are NOT automatic!

### For Database Changes:

1. **Create Migration Scripts**: Save SQL changes to a file
2. **Run Manually**: Execute SQL in cPanel phpMyAdmin or via SSH
3. **Or Add to Deployment**: Include in deployment script:

```bash
# In deploy.sh, add:
mysql -u username -p database_name < migrations/latest.sql
```

### Recommended: Database Migration System

Create a `migrations/` folder and track schema changes:

```python
# migrations/001_add_backup_tables.sql
CREATE TABLE IF NOT EXISTS backup_settings (...);
CREATE TABLE IF NOT EXISTS backup_history (...);
```

Then run migrations during deployment.

## Security Notes

1. **Protect Webhook Endpoint**: Use a secret token
2. **Limit Access**: Restrict webhook endpoint to GitHub IPs
3. **Backup First**: Always backup database before migrations
4. **Test Locally**: Test changes before deploying

## Quick Deploy Command

Create an alias for quick deployment:

```bash
# Add to ~/.bashrc
alias deploy='cd /home1/projectl/project_lucas && git pull origin main && touch passenger_wsgi.py'
```

Then just run: `deploy`






