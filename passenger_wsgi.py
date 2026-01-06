# Passenger WSGI entry point for cPanel
# Application startup file: app.py
# Entry point: app

from app import app

# Export app as the entry point (configured in cPanel Passenger settings)
# Also export as 'application' for compatibility
application = app
