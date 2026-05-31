#!/bin/bash
# Post-deploy setup script for cPanel
# Run after: git pull origin main
# Usage: bash setup_cpanel.sh

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=========================================="
echo "Elimu Centric - cPanel Setup"
echo "=========================================="

# 1. Create venv if missing
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    virtualenv -p python3 venv
fi
echo "Activating virtualenv..."
source venv/bin/activate

# 2. Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# 3. .env check
if [ ! -f ".env" ]; then
    echo ""
    echo "WARNING: .env not found!"
    echo "  Create .env on the server with DB credentials, SECRET_KEY, and other settings"
    echo ""
else
    echo ".env found."
fi

# 4. .htaccess check
if [ ! -f ".htaccess" ]; then
    echo ""
    echo "WARNING: .htaccess not found!"
    echo "  Add .htaccess for Passenger and set PassengerAppRoot to your full server path"
    echo "  (e.g. /home/username/public_html or /home1/account/elimu_centric)"
    echo ""
else
    echo ".htaccess found. Ensure PassengerAppRoot matches your app directory path."
fi

# 5. Run migrations (creates/updates tables and columns)
echo "Running database migrations..."
python -c "from migrations.migration_manager import run_all_migrations; run_all_migrations()" || true

# 6. Restart Passenger (so it picks up new code and migrations)
if [ -f "passenger_wsgi.py" ]; then
    echo "Touching passenger_wsgi.py to trigger restart..."
    touch passenger_wsgi.py
fi

echo ""
echo "=========================================="
echo "Setup complete."
echo "=========================================="
