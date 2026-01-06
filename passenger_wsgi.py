#!/usr/bin/env python3
"""
Passenger WSGI entry point for cPanel deployment
This file is used by Passenger to run the Flask application
"""
import sys
import os

# Add the project directory to the Python path
sys.path.insert(0, os.path.dirname(__file__))

# Import the Flask app
from app import app

# Passenger expects the 'application' variable
application = app

# Optional: Initialize database on Passenger startup (only once)
# This is handled automatically by app.py's initialization

