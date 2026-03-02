#!/bin/bash
# Post-deploy setup script for cPanel
# Run after: git pull origin main
# Usage: bash setup_cpanel.sh

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=========================================="
echo "Project Lucas - cPanel Setup"
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
    echo "  cp .env.example .env"
    echo "  Then edit .env with your DB credentials and SECRET_KEY"
    echo ""
else
    echo ".env found."
fi

# 4. .htaccess check
if [ ! -f ".htaccess" ]; then
    echo ""
    echo "WARNING: .htaccess not found!"
    echo "  cp .htaccess.example .htaccess"
    echo "  Then edit .htaccess and set PassengerAppRoot to your full server path"
    echo "  (e.g. /home/username/public_html or /home1/account/project_lucas)"
    echo ""
else
    echo ".htaccess found. Ensure PassengerAppRoot matches your app directory path."
fi

echo ""
echo "=========================================="
echo "Setup complete. See DEPLOYMENT.md for full guide."
echo "=========================================="
