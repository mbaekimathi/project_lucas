import sys
import os

# Add the project directory to the Python path
project_dir = os.path.dirname(os.path.abspath(__file__))
if project_dir not in sys.path:
    sys.path.insert(0, project_dir)

# Import the Flask app from app.py
from app import app

# Passenger requires the 'application' variable (not 'app')
application = app

