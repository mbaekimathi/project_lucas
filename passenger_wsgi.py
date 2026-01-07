# Passenger WSGI entry point for cPanel
# Application startup file: app.py
# Entry point: app

import sys
import os

# Add the project directory to Python path
project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_dir)

print("=" * 60)
print("Passenger WSGI: Starting application load...")
print(f"Project directory: {project_dir}")
print(f"Python path: {sys.path[:3]}")
print("=" * 60)

try:
    # Import the Flask app
    print("Attempting to import app from app.py...")
    from app import app
    
    # Run database migrations automatically on startup
    try:
        print("Running database migrations...")
        from migrations.migration_manager import run_all_migrations
        run_all_migrations()
        print("Migrations completed.")
    except Exception as e:
        print(f"Warning: Error running migrations: {e}")
        import traceback
        traceback.print_exc()
    
    # Verify the app is loaded and has routes
    if app is None:
        raise ImportError("Failed to import app from app.py - app is None")
    
    # Export both 'app' and 'application' for compatibility
    # Passenger typically looks for 'application'
    application = app
    
    # Print confirmation (visible in Passenger logs)
    print("=" * 60)
    print("Passenger WSGI: App loaded successfully")
    print(f"App instance: {app}")
    print(f"App name: {app.name}")
    print(f"Registered routes: {len(app.url_map._rules)}")
    
    # List some key routes for debugging
    routes = []
    for rule in app.url_map.iter_rules():
        routes.append(f"{rule.rule} -> {rule.endpoint}")
    
    print("\nSample routes:")
    for route in routes[:10]:  # Show first 10 routes
        print(f"  {route}")
    if len(routes) > 10:
        print(f"  ... and {len(routes) - 10} more routes")
    
    print("=" * 60)
    
except Exception as e:
    # If import fails, create a minimal error app
    print("=" * 60)
    print(f"ERROR loading app: {e}")
    print("=" * 60)
    import traceback
    traceback.print_exc()
    print("=" * 60)
    
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
                .error {{ background: #fee; padding: 15px; border-left: 4px solid #ef4444; margin: 20px 0; }}
                code {{ background: #f5f5f5; padding: 2px 6px; border-radius: 3px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>⚠️ Application Error</h1>
                <p>Failed to load Flask application.</p>
                <div class="error">
                    <strong>Error:</strong> <code>{str(e)}</code>
                </div>
                <p><strong>What to do:</strong></p>
                <ol>
                    <li>Check Passenger error logs in cPanel</li>
                    <li>Verify all dependencies are installed: <code>pip install -r requirements.txt</code></li>
                    <li>Check that <code>app.py</code> is in the correct directory</li>
                    <li>Verify database connection settings</li>
                    <li>Check that SECRET_KEY is set in environment variables</li>
                </ol>
                <p><small>Check the Passenger error logs for full traceback details.</small></p>
            </div>
        </body>
        </html>
        """, 500
    
    @error_app.route('/test')
    def test():
        return "<h1>Test Route Working</h1><p>If you see this, Flask is running but the main app failed to load.</p>", 200
    
    application = error_app
    app = error_app
    print("Created fallback error app with / route")
