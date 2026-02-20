from app.routes.auth import bp as auth_bp
from app.routes.admin import bp as admin_bp
from app.routes.ssid import bp as ssid_bp

from app.routes.setup import bp as setup_bp

def register_blueprints(app):
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(ssid_bp)
    app.register_blueprint(setup_bp)