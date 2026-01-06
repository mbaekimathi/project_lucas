# Passenger WSGI entry point for cPanel
# Application startup file: app.py
# Entry point: app

import sys
import os

# Add the project directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    # Import the Flask app
    from app import app
    
    # Verify the app is loaded and has routes
    if app is None:
        raise ImportError("Failed to import app from app.py")
    
    # Export both 'app' and 'application' for compatibility
    # Passenger typically looks for 'application'
    application = app
    
    # Print confirmation (visible in Passenger logs)
    print("=" * 60)
    print("Passenger WSGI: App loaded successfully")
    print(f"App instance: {app}")
    print(f"Registered routes: {len(app.url_map._rules)}")
    print("=" * 60)
    
except Exception as e:
    # If import fails, create a minimal error app
    print(f"ERROR loading app: {e}")
    import traceback
    traceback.print_exc()
    
    from flask import Flask
    error_app = Flask(__name__)
    
    @error_app.route('/')
    def error():
        return f"""
        <!DOCTYPE html>
        <html>
        <head><title>Application Error</title></head>
        <body>
            <h1>Application Error</h1>
            <p>Failed to load Flask application.</p>
            <p>Error: {str(e)}</p>
            <p>Check Passenger error logs for details.</p>
        </body>
        </html>
        """, 500
    
    application = error_app
    app = error_app
