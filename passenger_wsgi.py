# Passenger WSGI entry point for cPanel
# This file is used by Passenger to run the Flask application

from app import app

# Passenger requires the 'application' variable
application = app
