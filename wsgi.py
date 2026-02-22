"""
WSGI entrypoint for production servers.

Examples:
  - Waitress (Windows friendly):
      waitress-serve --host=0.0.0.0 --port=5000 wsgi:app

  - Gunicorn (Linux/macOS):
      gunicorn -w 2 -b 0.0.0.0:5000 wsgi:app
"""

from app import app

