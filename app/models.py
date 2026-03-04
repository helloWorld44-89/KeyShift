from flask_login import UserMixin
from . import db
from sqlalchemy import delete
from flask_bcrypt import bcrypt
import secrets
import logging

log = logging.getLogger(__name__)


class user(db.Model, UserMixin):
    """
    Application user model.

    Supports two roles:
        admin=True  — can add/manage other users and change configuration
        admin=False — standard user (can change passwords and view SSIDs)
    """
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.Text, nullable=False)
    password = db.Column(db.Text)               # bcrypt hash
    admin = db.Column(db.Boolean)               # True = admin role
    active = db.Column(db.Boolean, default=True)
    apiKey = db.Column(db.Text)                 # URL-safe 32-byte token for API access

    def __repr__(self):
        return f'Username: {self.username}'

    @staticmethod 
    def newUser(userName, pw, role=0):
        """
        Create and persist a new user.

        Hashes the password with bcrypt and generates a random API key.

        Args:
            userName: Login username
            pw: Plaintext password (will be hashed)
            role: 0 = standard user, 1 = admin
        """
        try:
            salt = bcrypt.gensalt()
            _passwd = bcrypt.hashpw(pw.encode('utf-8'), salt)
            api = secrets.token_urlsafe(32)  # Cryptographically secure API key
            newUser = user(username=userName, password=_passwd, active=True, admin=role, apiKey=api)
            db.session.add(newUser)
            db.session.commit()
            log.info(f'{userName} has been added')
            return (f'{userName} has been added!')
        except Exception as e:
            log.info(f"newUser Error : {e}")
            return f'An Error has occured: {e}'


class SSID(db.Model):
    """
    Wi-Fi SSID model — mirrors a wireless network on the controller.

    One SSID may be designated as 'isGuest=True', which controls which QR code
    is shown on the public guest page (/network/qr/<id>).
    """
    __tablename__ = 'ssids'
    id = db.Column(db.Integer, primary_key=True)
    ssidName = db.Column(db.Text, nullable=False)
    ssidPW = db.Column(db.Text)                         # Current plaintext Wi-Fi password
    lastChanged = db.Column(db.DateTime, default=None)  # Timestamp of last password change
    siteID = db.Column(db.Text)                         # Controller site ID
    wlanGroupID = db.Column(db.Text, default=None)      # WLAN group (Omada only)
    ssidID = db.Column(db.Text)                         # Unique SSID ID on the controller
    status = db.Column(db.Boolean, default=True)        # SSID enabled/disabled
    hidden = db.Column(db.Boolean, default=False)       # Hidden SSID
    pwRotate = db.Column(db.Boolean, default=False)     # Rotation enabled
    rotateFrequency = db.Column(db.Text, default=None)  # Cron expression for rotation
    qrCode = db.Column(db.Boolean, default=False)       # QR code generation enabled
    isGuest = db.Column(db.Boolean, default=False)      # Guest network flag

    def __repr__(self):
        return f'SSID: {self.ssidName} SiteID: {self.siteID} WLANGroupID: {self.wlanGroupID} SSIDID: {self.ssidID}'

    def __init__(self, ssidName, ssidPW, siteID, wlanGroupID, ssidID,
                 status=True, pwRotate=False, qrCode=False, isGuest=False):
        self.ssidName = ssidName
        self.ssidPW = ssidPW
        self.siteID = siteID
        self.wlanGroupID = wlanGroupID
        self.ssidID = ssidID
        self.status = status
        self.pwRotate = pwRotate
        self.qrCode = qrCode
        self.isGuest = isGuest
    @staticmethod 
    def newSSID(ssidName, ssidPW, siteID, wlanGroupID, ssidID,
                status=True, pwRotate=False, qrCode=False, isGuest=False):
        """Create and persist a new SSID record."""
        try:
            newSSID = SSID(ssidName=ssidName, ssidPW=ssidPW, siteID=siteID,
                           wlanGroupID=wlanGroupID, ssidID=ssidID, status=status,
                           pwRotate=pwRotate, qrCode=qrCode, isGuest=isGuest)
            db.session.add(newSSID)
            db.session.commit()
            log.info(f'SSID {ssidName} has been added to the database.')
            return (f'SSID {ssidName} has been added!')
        except Exception as e:
            log.info(f"newSSID Error : {e}")
            return f'An Error has occured: {e}'

    def makeGuest(self):
        """
        Mark this SSID as the active guest network.

        Enforces a single-guest constraint: if another SSID is already the
        guest, it is demoted before this one is promoted.
        """
        try:
            guestSSID = SSID.query.filter_by(isGuest=True).first()
            if guestSSID is None:
                # No current guest — set this one
                self.isGuest = True
                db.session.commit()
                log.info(f"{self.ssidName} is now the guest SSID.")
                return f"{self.ssidName} is now the guest SSID."
            if guestSSID.id == self.id:
                log.info(f"{self.ssidName} is already the guest SSID.")
                return f"{self.ssidName} is already the guest SSID."
            else:
                # Demote existing guest, promote this one
                guestSSID.isGuest = False
                self.isGuest = True
                db.session.commit()
                log.info(f"{self.ssidName} is now the guest SSID.")
                return f"{self.ssidName} is now the guest SSID."
        except Exception as e:
            log.error(f"makeGuest Error : {e}")
            return f'An Error has occured: {e}'

    def addRotation(self, rotateFrequency):
        """
        Enable or disable scheduled password rotation for this SSID.

        Args:
            rotateFrequency: Cron expression string (e.g. '0 3 * * 1'),
                             or None to disable rotation.
        """
        try:
            print(rotateFrequency)
            if rotateFrequency is not None:
                self.pwRotate = True
                self.rotateFrequency = rotateFrequency
                db.session.commit()
                log.info(f"Password rotation added to {self.ssidName} with frequency {rotateFrequency}.")
                return f"Password rotation added to {self.ssidName} with frequency {rotateFrequency}."
            else:
                # Remove rotation schedule
                self.pwRotate = False
                self.rotateFrequency = None
                db.session.commit()
                log.info(f"Password rotation removed from {self.ssidName}.")
                return f"Password rotation removed from {self.ssidName}."
        except Exception as e:
            log.error(f"addRotation Error : {e}")
            return f'An Error has occured: {e}'
    @staticmethod 
    def removeAllSSIDS() -> bool:
        """
        Delete all SSID records from the database.

        Used before a controller rescan to ensure the local DB stays in
        sync with what the controller reports.
        """
        try:
            if len(SSID.query.all()) > 0:
                db.session.execute(delete(SSID).where(SSID.id > 0))
                db.session.commit()
                log.info('SSIDs deleted from database.')
            return True
        except Exception as e:
            log.error(e)
            return False
