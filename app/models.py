from flask_login import UserMixin
from . import db
from flask_bcrypt import bcrypt 
import secrets
import logging 

log = logging.getLogger(__name__)

class user(db.Model,UserMixin):
    __tablename__='users'   
    id=db.Column(db.Integer, primary_key=True)
    username=db.Column(db.Text, nullable=False)
    password=db.Column(db.Text)
    admin=db.Column(db.Boolean) # can add users and manage others profiles
    active = db.Column(db.Boolean, default = True)
    apiKey = db.Column(db.Text)

    def __repr__(self):
        return f'Username: {self.username}'

    def newUser(userName,pw, role=0):
        try:
            salt=bcrypt.gensalt()
            _passwd = bcrypt.hashpw(pw.encode('utf-8'),salt)
            api = secrets.token_urlsafe(32)
            newUser = user(username = userName, password = _passwd, active = True, admin = role,apiKey = api)
            db.session.add(newUser)
            db.session.commit()
            log.info(f'{userName} has been added')
            return (f'{userName} has been added!')
        except Exception as e:
            log.info(f"newUser Error : {e}")
            return f'An Error has occured: {e}'