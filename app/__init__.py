from flask import Flask, request
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from os import path
import fcntl
import logging
import os
from dotenv import load_dotenv

# Load environment variables from .env file (if present)
load_dotenv()

log = logging.getLogger(__name__)

MIGRATIONS_DIR = path.join(path.dirname(path.dirname(path.abspath(__file__))), "migrations")

# Initialise extensions without binding to an app yet (Application Factory pattern)
db = SQLAlchemy()
migrate = Migrate()

# Rate limiter: keyed by remote IP, default limits apply to all routes
# Counters live in RATELIMIT_STORAGE_URI (e.g. redis://host:6379). The default
# in-memory store is per process, so it is only exact with a single Gunicorn worker.
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "20 per hour"],
    default_limits_exempt_when=lambda: request.endpoint == "static",
    storage_uri=os.environ.get("RATELIMIT_STORAGE_URI", "memory://"),
)


def create_app(test_config=None):
    """Application factory — creates and configures the Flask app instance.

    test_config, if given, overrides the config and skips first-run DB creation.
    """
    app = Flask(__name__)

    # --- Config ---
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
    if not app.config['SECRET_KEY']:
        raise ValueError("No SECRET_KEY set in environment variables")

    # SQLite database stored in the instance/ folder (excluded from version control)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///KeyShift.db'

    if test_config:
        app.config.update(test_config)

    # Behind a reverse proxy/ingress, trust that many X-Forwarded-* hops so the
    # rate limiter and logs see the real client IP. 0 (default) trusts none,
    # because the header is spoofable when the app is reachable directly.
    proxies = int(app.config.get("TRUSTED_PROXY_COUNT", os.environ.get("TRUSTED_PROXY_COUNT", 0)))
    if proxies:
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=proxies, x_proto=proxies, x_host=proxies)

    # --- Extensions ---
    db.init_app(app)
    limiter.init_app(app)
    # Alembic migrations; batch mode lets SQLite alter tables
    migrate.init_app(app, db, directory=MIGRATIONS_DIR, render_as_batch=True)

    # CSRF protection for all forms (Flask-WTF)
    from flask_wtf.csrf import CSRFProtect
    csrf = CSRFProtect()
    csrf.init_app(app)

    # --- Logging ---
    from logging.config import dictConfig
    from app.logging_config import LOGGING_CONFIG, addFileHandler
    dictConfig(LOGGING_CONFIG)
    if not app.config.get("TESTING"):
        addFileHandler(app)  # feeds the log viewer on the admin Advanced tab

    # --- Blueprints ---
    from .pages import bp
    app.register_blueprint(bp, url_prefix='/')

    from app.routes import register_blueprints
    register_blueprints(app)  # Registers auth, admin, ssid, setup blueprints

    # --- Health check (liveness/readiness probes) ---
    @app.route('/healthz')
    @limiter.exempt
    def healthz():
        """Lightweight, unauthenticated and rate-limit-exempt endpoint for k3s probes."""
        return {"status": "ok"}, 200

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

    # Create or upgrade the database schema on startup
    if not test_config:
        _maybe_init_db(app)

    return app


def _maybe_init_db(app):
    """
    Brings the database schema up to date on startup.

    Fresh installs get the schema from the migrations. Databases created before
    migrations existed (tables but no alembic_version) are stamped at the baseline
    revision first, so their data is left untouched.

    An flock on instance/.migrate.lock serialises Gunicorn workers and cron jobs
    that start at the same time. The OS drops the lock if the holder dies, so a
    crash can never leave a stale lock behind.
    """
    if not path.isdir(MIGRATIONS_DIR):
        log.warning("No migrations directory found; creating tables directly.")
        with app.app_context():
            db.create_all()
        return

    os.makedirs(app.instance_path, exist_ok=True)
    with open(path.join(app.instance_path, ".migrate.lock"), "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        with app.app_context():
            upgrade_schema(app)
            from app.config.config import encryptConfigSecrets
            encryptConfigSecrets()


def upgrade_schema(app):
    """Stamp a pre-migrations database at the baseline, then upgrade to head."""
    from alembic.script import ScriptDirectory
    from flask_migrate import stamp, upgrade
    from sqlalchemy import inspect

    tables = inspect(db.engine).get_table_names()
    if tables and "alembic_version" not in tables:
        baseline = ScriptDirectory(MIGRATIONS_DIR).get_bases()[0]
        log.info(f"Existing database without migration history; stamping {baseline}")
        stamp(revision=baseline)
    upgrade()
