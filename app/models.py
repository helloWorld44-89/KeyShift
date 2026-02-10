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
        
class SSID(db.Model):
    __tablename__='ssids'   
    id=db.Column(db.Integer, primary_key=True)
    ssidName=db.Column(db.Text, nullable=False)
    ssidPW=db.Column(db.Text)
    #lastChanged=db.Column(db.DateTime, default=None)
    siteID=db.Column(db.Text)
    wlanGroupID=db.Column(db.Text,default=None)
    ssidID=db.Column(db.Text)
    status=db.Column(db.Boolean, default=True)
    #hidden=db.Column(db.Boolean, default=False)
    pwRotate=db.Column(db.Boolean, default=False)
    rotateFrequency=db.Column(db.Text, default=None)
    qrCode=db.Column(db.Boolean, default=False)
    isGuest=db.Column(db.Boolean, default=False)

    def __repr__(self):
        return f'SSID: {self.ssidName} SiteID: {self.siteID} WLANGroupID: {self.wlanGroupID} SSIDID: {self.ssidID}'
    
    def __init__(self, ssidName, ssidPW, siteID, wlanGroupID, ssidID,  status=True, pwRotate=False, qrCode=False, isGuest=False):
        self.ssidName= ssidName
        self.ssidPW= ssidPW
        self.siteID= siteID
        self.wlanGroupID= wlanGroupID
        self.ssidID= ssidID
        self.status= status
        self.pwRotate= pwRotate
        self.qrCode= qrCode
        self.isGuest= isGuest
    
    def newSSID(ssidName, ssidPW, siteID, wlanGroupID, ssidID, status=True, pwRotate=False, qrCode=False, isGuest=False):
        try:
            newSSID = SSID(ssidName = ssidName, ssidPW = ssidPW, siteID = siteID, wlanGroupID = wlanGroupID, ssidID = ssidID, status=status, pwRotate=pwRotate, qrCode=qrCode, isGuest=isGuest)
            db.session.add(newSSID)
            db.session.commit()
            log.info(f'SSID {ssidName} has been added to the database.')
            return (f'SSID {ssidName} has been added!')
        except Exception as e:
            log.info(f"newSSID Error : {e}")
            return f'An Error has occured: {e}'
    
    def makeGuest(self):
        try:
            guestSSID = SSID.query.filter_by(isGuest=True).first()
            if guestSSID.id == self.id:
                log.info(f"{self.ssidName} is already the guest SSID.")
                return f"{self.ssidName} is already the guest SSID."
            else:
                guestSSID.isGuest = False
                self.isGuest = True
                db.session.commit()
                log.info(f"{self.ssidName} is now the guest SSID.")
                return f"{self.ssidName} is now the guest SSID."
        except Exception as e:
            log.error(f"makeGuest Error : {e}")
            return f'An Error has occured: {e}'
    
    def addRotation(self, rotateFrequency):
        try:
            print(rotateFrequency)
            if rotateFrequency != None:
                self.pwRotate = True
                self.rotateFrequency = rotateFrequency
                db.session.commit()
                log.info(f"Password rotation added to {self.ssidName} with frequency {rotateFrequency}.")
                return f"Password rotation added to {self.ssidName} with frequency {rotateFrequency}."
            else:
                self.pwRotate = False
                self.rotateFrequency = None
                db.session.commit()
                log.info(f"Password rotation removed from {self.ssidName}.")
                return f"Password rotation removed from {self.ssidName}."
        except Exception as e:
            log.error(f"addRotation Error : {e}")
            return f'An Error has occured: {e}'
           
