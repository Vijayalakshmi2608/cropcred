"""Production WSGI entrypoint for CropCred.

Gunicorn imports this module before accepting requests.  Initialization is
deliberately here—not only under ``app.py``'s __main__ block—so a fresh
persistent deployment cannot start successfully with an empty database.
"""

from database import init_db, seed_db

init_db()
seed_db()

from app import app  # noqa: E402  (startup must happen before serving)

__all__ = ['app']
