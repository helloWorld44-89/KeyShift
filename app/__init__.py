from flask import Flask
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from os import path

db=SQLAlchemy()
migrate=Migrate()


def create_app():
    app = Flask(__name__)

    app.config['SECRET_KEY'] = 'SECRETKEY'
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///KeyShift.db'
    app.secret_key = 'TEST KEY'

    db.init_app(app)

    

    from .pages import bp
    app.register_blueprint(bp, url_prefix = '/')


    login_manager=LoginManager()
    login_manager.login_message_category = "info"
    login_manager.login_view='pages.login'
    login_manager.init_app(app)

    from .models import user
    from .config.config import getConfig


    @login_manager.user_loader
    def load_user(id):
        return user.query.get(int(id))
    
    if not path.exists("instance/KeyShift.db"):
        print("Creating DB...")
        with app.app_context():
            db.create_all()
            print("Database Created!")
            print(user.newUser('root', 'admin', True ))
    else :
        print("Database exisits....")
        migrate.init_app(app,db)



    return app