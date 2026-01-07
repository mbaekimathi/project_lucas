#!/bin/bash
# Deployment script for cPanel
# Usage: Run this script after pushing to GitHub

echo "=========================================="
echo "Starting Deployment..."
echo "=========================================="

# Navigate to project directory
cd /home1/projectl/project_lucas || exit 1

# Pull latest code from GitHub
echo "Pulling latest code from GitHub..."
git pull origin main

# Check if pull was successful
if [ $? -ne 0 ]; then
    echo "ERROR: Git pull failed!"
    exit 1
fi

# Update Python dependencies (if requirements.txt exists)
if [ -f "requirements.txt" ]; then
    echo "Updating Python dependencies..."
    # Activate virtual environment if it exists
    if [ -d "venv" ]; then
        source venv/bin/activate
    fi
    pip install -r requirements.txt --quiet --upgrade
fi

# Run database migrations
echo "Running database migrations..."
if [ -f "migrations/migration_manager.py" ]; then
    python3 -c "from migrations.migration_manager import run_all_migrations; run_all_migrations()" || echo "Warning: Migrations may have failed, check logs"
else
    echo "No migration system found, skipping migrations"
fi

# Restart Passenger by touching passenger_wsgi.py
echo "Restarting Passenger application..."
touch passenger_wsgi.py

echo "=========================================="
echo "Deployment completed successfully!"
echo "Date: $(date)"
echo "=========================================="

