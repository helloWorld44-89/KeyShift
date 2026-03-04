from flask import Flask
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from os import path
import os
from dotenv import load_dotenv

# Load environment variables from .env file (if present)
load_dotenv()

# Initialise extensions without binding to an app yet (Application Factory pattern)
db = SQLAlchemy()
migrate = Migrate()

# Rate limiter: keyed by remote IP, default limits apply to all routes
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "20 per hour"]
)


def create_app():
    """Application factory — creates and configures the Flask app instance."""
    app = Flask(__name__)

    # --- Config ---
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
    if not app.config['SECRET_KEY']:
        raise ValueError("No SECRET_KEY set in environment variables")

    # SQLite database stored in the instance/ folder (excluded from version control)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///KeyShift.db'

    # --- Extensions ---
    db.init_app(app)
    limiter.init_app(app)
    migrate.init_app(app, db)  # Alembic migrations registered here

    # CSRF protection for all forms (Flask-WTF)
    from flask_wtf.csrf import CSRFProtect
    csrf = CSRFProtect()
    csrf.init_app(app)

    # --- Logging ---
    from logging.config import dictConfig
    from app.logging_config import LOGGING_CONFIG
    dictConfig(LOGGING_CONFIG)

    # --- Blueprints ---
    from .pages import bp
    app.register_blueprint(bp, url_prefix='/')

    from app.routes import register_blueprints
    register_blueprints(app)  # Registers auth, admin, ssid, setup blueprints

    # --- Login Manager ---
    login_manager = LoginManager()
    login_manager.login_message_category = "info"
    login_manager.login_view = 'auth.login'  # Redirect unauthenticated requests here
    login_manager.init_app(app)

    from .models import user
    from .config.config import getConfig

    @login_manager.user_loader
    def load_user(id):
        """Callback used by Flask-Login to reload the user from the session."""
        return user.query.get(int(id))

    # Initialise the database on first run (skips if DB already exists)
    _maybe_init_db(app)

    return app


def _maybe_init_db(app):
    """
    Creates the SQLite database tables on first launch.

    Uses a file-based lock to prevent race conditions when multiple Gunicorn
    workers start simultaneously — only the first worker to create the lock
    file will perform the initialisation.
    """
    db_path = path.join("instance", "KeyShift.db")

    if path.exists(db_path):
        print("Database exists, skipping creation.")
        return

    lock_path = db_path + ".init.lock"

    # Atomic lock: only the process that creates the lock file wins
    try:
        fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.close(fd)
    except FileExistsError:
        # Another worker is already initialising — nothing to do
        print(f"[PID {os.getpid()}] DB init already in progress, skipping.")
        return

    try:
        print(f"[PID {os.getpid()}] Creating database...")
        with app.app_context():
            db.create_all()
        print("Database created!")
    finally:
        # Always remove the lock so it doesn't block future container restarts
        try:
            os.remove(lock_path)
        except OSError:
            pass
