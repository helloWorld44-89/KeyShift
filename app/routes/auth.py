import hmac
import os
import secrets
from functools import wraps
from flask import Blueprint, current_app, render_template, request, url_for, redirect, flash, session, abort
from flask_bcrypt import bcrypt
from flask_login import login_user, login_required, logout_user, current_user
from app.models import user
from app import limiter
import logging

bp = Blueprint("auth", __name__)
log = logging.getLogger(__name__)


def admin_required(f):
    """Allow only logged-in users with the admin role; others get 403."""
    @wraps(f)
    @login_required
    def wrapper(*args, **kwargs):
        if not current_user.admin:
            log.warning(f"{current_user.username} was denied admin-only route {request.path}")
            abort(403)
        return f(*args, **kwargs)
    return wrapper


def setup_in_progress() -> bool:
    """
    True only for the browser session that created the very first user and has
    not yet finished first-run setup.

    The flag is bound to the first user's id, so another visitor who also opened
    /initApp before setup finished cannot reuse it.
    """
    first = user.query.order_by(user.id).first()
    return (first is not None
            and session.get("init_mode") is True
            and session.get("init_user") == first.id)


def _setup_token_path() -> str:
    return os.path.join(current_app.instance_path, "setup_token")


def setup_token() -> str:
    """
    The one-time token a visitor must present to create the first admin.

    Taken from the SETUP_TOKEN setting/env var if set. Otherwise a random token
    is generated, stored in instance/setup_token (shared by all Gunicorn
    workers) and logged so the operator can read it from the container logs.
    """
    token = current_app.config.get("SETUP_TOKEN") or os.environ.get("SETUP_TOKEN")
    if token:
        return token
    path = _setup_token_path()
    os.makedirs(current_app.instance_path, exist_ok=True)
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        with open(path) as f:
            return f.read().strip()
    token = secrets.token_urlsafe(16)
    with os.fdopen(fd, "w") as f:
        f.write(token)
    return token


def clear_setup_token():
    """Remove the generated token once the first user exists."""
    try:
        os.remove(_setup_token_path())
    except OSError:
        pass


def setup_token_valid(candidate) -> bool:
    return bool(candidate) and hmac.compare_digest(str(candidate), setup_token())


@bp.route("/login", methods=["GET", "POST"])
@limiter.limit("5 per minute")
def login():
    if len(user.query.all()) < 1:
        log.info("No users found, redirecting to initApp")
        return redirect(url_for("setup.initApp"))
    if request.method == 'POST':
        _username = request.form["username"]
        password = request.form["password"]
        _user = user.query.filter_by(username=_username).first()
        if _user:
            if(bcrypt.checkpw(password.encode('utf-8'),_user.password)):
                flash('Login success!','success')
                login_user(_user)
                log.info(f"{_username} logged in")
                return redirect(url_for("admin.admin"))
            else:
                log.warning(f"{_username} failed log in")
                flash('Incorrect Username or Password', 'danger')
        else:
            log.warning(f"{_username} failed log in")
            flash('Incorrect Username or Password', 'danger')
    return render_template("pages/login.html")

@bp.route("/logout", methods=["POST"])
@login_required
def logout():
    log.info(f"{current_user.username} logged out")
    logout_user()
    return redirect(url_for("auth.login"))