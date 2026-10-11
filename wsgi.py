"""
WSGI entry point for SalesPulse production servers.
Exposes the application callable for Gunicorn, uWSGI, and cloud platforms.
"""

from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run()
