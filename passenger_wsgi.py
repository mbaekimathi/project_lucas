# Passenger WSGI entry point for cPanel
# Application startup file: passenger_wsgi.py
# Entry point: application

import os
import sys

project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_dir)
os.chdir(project_dir)

try:
    from app import app

    application = app
except Exception as load_error:
    load_error_message = str(load_error)

    from flask import Flask

    error_app = Flask(__name__)

    @error_app.route('/')
    def error():
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Application Error</title>
            <style>
                body {{ font-family: Arial, sans-serif; padding: 50px; background: #f5f5f5; }}
                .container {{ background: white; padding: 30px; border-radius: 10px; max-width: 800px; margin: 0 auto; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                h1 {{ color: #ef4444; }}
                .error {{ background: #fee; padding: 15px; border-left: 4px solid #ef4444; margin: 20px 0; word-break: break-word; }}
                code {{ background: #f5f5f5; padding: 2px 6px; border-radius: 3px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Application Error</h1>
                <p>Failed to load Flask application.</p>
                <div class="error">
                    <strong>Error:</strong> <code>{load_error_message}</code>
                </div>
                <p><strong>What to do:</strong></p>
                <ol>
                    <li>Check Passenger error logs in cPanel</li>
                    <li>Run: <code>pip install -r requirements.txt</code></li>
                    <li>Confirm <code>.env</code> exists with DB_HOST, DB_USER, DB_PASSWORD, DB_NAME, SECRET_KEY</li>
                    <li>SSH test: <code>python -c "from app import app; print('OK')"</code></li>
                </ol>
            </div>
        </body>
        </html>
        """, 500

    application = error_app
